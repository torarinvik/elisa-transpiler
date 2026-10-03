#!/usr/bin/env python3
"""Run one owned POSIX process group with a deadline and aggregate memory cap.

The launcher starts the command in a new session and signals only that group on
a limit breach. It samples aggregate RSS everywhere and macOS physical footprint
as well, because compressed/swapped pages can make `ps` RSS substantially
under-report a process's memory pressure. It intentionally does not wrap a
shell command string: pass the executable and its arguments separately.
"""

from __future__ import annotations

import argparse
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from collections.abc import Sequence

RSS_HEADROOM_MAX_KB = 65536
RSS_HEADROOM_FRACTION_DIVISOR = 8
FOOTPRINT_SAMPLE_SECONDS = 0.1
FOOTPRINT_HEADROOM_FRACTION_DIVISOR = 4


class MonitorError(RuntimeError):
    pass


def process_group_stats(group_id: int) -> tuple[int, bool, list[int]]:
    """Return (sum RSS in KiB, has live member, live PIDs) for a process group."""
    result = subprocess.run(
        ["ps", "-axo", "pid=,pgid=,rss=,stat="],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or f"ps exited {result.returncode}"
        raise MonitorError(detail)

    rss_total = 0
    live = False
    pids: list[int] = []
    for row in result.stdout.splitlines():
        fields = row.split()
        if len(fields) < 4:
            continue
        try:
            row_group = int(fields[1])
            row_rss = int(fields[2])
        except ValueError:
            continue
        if row_group != group_id or fields[3].startswith("Z"):
            continue
        try:
            pids.append(int(fields[0]))
        except ValueError:
            continue
        rss_total += row_rss
        live = True
    return rss_total, live, pids


def process_group_footprint_bytes(pids: Sequence[int]) -> int:
    """Return macOS physical footprint for the listed live processes."""
    if not pids:
        return 0
    command = ["footprint", "--noCategories", "--format", "bytes"]
    for pid in pids:
        command.extend(["--pid", str(pid)])
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired as error:
        raise MonitorError("footprint sampling exceeded 10 seconds") from error
    if result.returncode != 0:
        detail = result.stderr.strip() or f"footprint exited {result.returncode}"
        raise MonitorError(detail)

    summary = re.search(r"Summary Footprint:\s*(\d+)\s*B", result.stdout)
    if summary:
        return int(summary.group(1))
    values = re.findall(r"^\s*phys_footprint:\s*(\d+)\s*B\s*$", result.stdout, re.MULTILINE)
    if not values:
        raise MonitorError("footprint output did not include a physical-footprint value")
    return sum(int(value) for value in values)


def process_group_breakdown(group_id: int) -> str:
    """Describe each live owned process to attribute aggregate RSS failures."""
    result = subprocess.run(
        ["ps", "-axo", "pid=,pgid=,rss=,stat=,comm="],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or f"ps exited {result.returncode}"
        return f"unavailable ({detail})"

    members: list[str] = []
    for row in result.stdout.splitlines():
        fields = row.strip().split(None, 4)
        if len(fields) < 5:
            continue
        try:
            pid, row_group, rss_kb = int(fields[0]), int(fields[1]), int(fields[2])
        except ValueError:
            continue
        if row_group != group_id or fields[3].startswith("Z"):
            continue
        members.append(f"{fields[4]} pid={pid} rss={rss_kb}KiB state={fields[3]}")
    return "; ".join(members) if members else "no live members found"


def terminate_group(group_id: int, process: subprocess.Popen[bytes], grace_seconds: float = 1.0) -> None:
    """Terminate and reap the owned group, escalating only that group if needed."""
    try:
        _, group_live, _ = process_group_stats(group_id)
    except MonitorError:
        # If the monitor is unavailable, preserve the fail-closed behavior.
        group_live = True
    if not group_live:
        process.wait()
        return
    try:
        os.killpg(group_id, signal.SIGTERM)
    except ProcessLookupError:
        pass

    deadline = time.monotonic() + grace_seconds
    while time.monotonic() < deadline:
        try:
            _, live, _ = process_group_stats(group_id)
        except MonitorError:
            # If the monitor itself is unavailable, do not infer that a stopped
            # leader means the group is empty; a descendant may still be alive.
            live = True
        if not live:
            break
        time.sleep(0.05)

    try:
        _, live, _ = process_group_stats(group_id)
    except MonitorError:
        live = True
    if live:
        try:
            os.killpg(group_id, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=2.0)
    except subprocess.TimeoutExpired:
        # The process may have exited while a child in the same group remained.
        try:
            os.killpg(group_id, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def positive_float(text: str) -> float:
    value = float(text)
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError("must be a finite positive number")
    return value


def positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a positive integer") from error
    if value <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return value


def rss_termination_threshold(max_rss_kb: int) -> int:
    """Reserve headroom for RSS growth between process-tree samples."""
    reserve_kb = min(RSS_HEADROOM_MAX_KB, max_rss_kb // RSS_HEADROOM_FRACTION_DIVISOR)
    return max_rss_kb - reserve_kb


def run(command: Sequence[str], max_rss_kb: int, timeout_seconds: float, poll_seconds: float) -> int:
    if os.name != "posix":
        print("run_bounded_process: POSIX process groups are required", file=sys.stderr)
        return 2
    if not command or not command[0]:
        print("run_bounded_process: missing command", file=sys.stderr)
        return 2

    try:
        process = subprocess.Popen(command, start_new_session=True)
    except OSError as error:
        print(f"run_bounded_process: cannot start {command[0]!r}: {error}", file=sys.stderr)
        return 127 if isinstance(error, FileNotFoundError) else 126

    group_id = process.pid
    deadline = time.monotonic() + timeout_seconds
    rss_threshold_kb = rss_termination_threshold(max_rss_kb)
    memory_threshold_bytes = rss_threshold_kb * 1024
    footprint_threshold_bytes = memory_threshold_bytes - memory_threshold_bytes // FOOTPRINT_HEADROOM_FRACTION_DIVISOR
    footprint_threshold_kb = (footprint_threshold_bytes + 1023) // 1024
    peak_rss_kb = 0
    peak_footprint_kb = 0
    footprint_available = sys.platform == "darwin" and shutil.which("footprint") is not None
    last_footprint_sample = 0.0
    limit_reason = ""
    try:
        while True:
            rss_kb, group_live, pids = process_group_stats(group_id)
            peak_rss_kb = max(peak_rss_kb, rss_kb)
            if rss_kb >= rss_threshold_kb:
                limit_reason = (
                    f"aggregate RSS {rss_kb} KiB reached safety threshold "
                    f"{rss_threshold_kb} KiB (configured cap {max_rss_kb} KiB)"
                )
                break
            now = time.monotonic()
            if footprint_available and group_live and now - last_footprint_sample >= FOOTPRINT_SAMPLE_SECONDS:
                footprint_bytes = process_group_footprint_bytes(pids)
                footprint_kb = (footprint_bytes + 1023) // 1024
                peak_footprint_kb = max(peak_footprint_kb, footprint_kb)
                last_footprint_sample = time.monotonic()
                if footprint_bytes >= footprint_threshold_bytes:
                    limit_reason = (
                        f"aggregate physical footprint {footprint_kb} KiB reached safety threshold "
                        f"{footprint_threshold_kb} KiB (configured cap {max_rss_kb} KiB)"
                    )
                    break
            if time.monotonic() >= deadline and group_live:
                limit_reason = f"deadline exceeded ({timeout_seconds:g}s)"
                break

            return_code = process.poll()
            if return_code is not None and not group_live:
                footprint_report = f"; peak physical footprint {peak_footprint_kb} KiB" if footprint_available else ""
                print(f"run_bounded_process: peak process-group RSS {peak_rss_kb} KiB{footprint_report}", file=sys.stderr)
                return return_code if return_code >= 0 else 128 - return_code
            time.sleep(poll_seconds)
    except MonitorError as error:
        # A child can exit between `ps` and `footprint`. Recheck before turning
        # a transient stale-PID report into a termination request; this also
        # avoids signaling a process group whose leader has already been reaped.
        try:
            rss_kb, group_live, _ = process_group_stats(group_id)
            peak_rss_kb = max(peak_rss_kb, rss_kb)
        except MonitorError:
            group_live = True
        if not group_live and process.poll() is not None:
            footprint_report = f"; peak physical footprint {peak_footprint_kb} KiB" if footprint_available else ""
            print(f"run_bounded_process: peak process-group RSS {peak_rss_kb} KiB{footprint_report}", file=sys.stderr)
            return_code = process.wait()
            return return_code if return_code >= 0 else 128 - return_code
        limit_reason = f"could not monitor owned process group: {error}"
    except KeyboardInterrupt:
        terminate_group(group_id, process)
        return 130

    process_details = process_group_breakdown(group_id)
    terminate_group(group_id, process)
    footprint_report = f"; peak physical footprint {peak_footprint_kb} KiB" if footprint_available else ""
    print(
        f"run_bounded_process: {limit_reason}; terminated owned process group "
        f"{group_id} (peak RSS {peak_rss_kb} KiB{footprint_report})\n"
        f"run_bounded_process: process-group members at limit: {process_details}",
        file=sys.stderr,
    )
    return 124 if limit_reason.startswith("deadline") else 125


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-rss-kb", type=positive_int, required=True)
    parser.add_argument("--timeout-seconds", type=positive_float, required=True)
    parser.add_argument("--poll-seconds", type=positive_float, default=0.1)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    arguments = parser.parse_args(argv)
    command = arguments.command
    if command and command[0] == "--":
        command = command[1:]
    return run(command, arguments.max_rss_kb, arguments.timeout_seconds, arguments.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
