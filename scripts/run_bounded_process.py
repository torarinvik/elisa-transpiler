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
PROCESS_SAMPLE_TIMEOUT_SECONDS = 1.0
FOOTPRINT_SAMPLE_SECONDS = 0.1
FOOTPRINT_SAMPLE_TIMEOUT_SECONDS = 10.0
FOOTPRINT_HEADROOM_FRACTION_DIVISOR = 4
SYSTEM_MEMORY_SAMPLE_SECONDS = 1.0
SYSTEM_MEMORY_SAMPLE_TIMEOUT_SECONDS = 5.0


class MonitorError(RuntimeError):
    pass


def process_group_stats(
    group_id: int, timeout_seconds: float = PROCESS_SAMPLE_TIMEOUT_SECONDS,
) -> tuple[int, bool, list[int]]:
    """Return (sum RSS in KiB, has live member, live PIDs) for a process group."""
    try:
        result = subprocess.run(
            ["ps", "-axo", "pid=,pgid=,rss=,stat="],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as error:
        raise MonitorError(f"process-list sampling exceeded {timeout_seconds:g} seconds") from error
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


def process_group_footprint_bytes(
    pids: Sequence[int], timeout_seconds: float = FOOTPRINT_SAMPLE_TIMEOUT_SECONDS,
) -> int:
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
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as error:
        raise MonitorError(f"footprint sampling exceeded {timeout_seconds:g} seconds") from error
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


def process_group_breakdown(
    group_id: int, timeout_seconds: float = PROCESS_SAMPLE_TIMEOUT_SECONDS,
) -> str:
    """Describe each live owned process to attribute aggregate RSS failures."""
    try:
        result = subprocess.run(
            ["ps", "-axo", "pid=,pgid=,rss=,stat=,comm="],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return f"unavailable (process breakdown sampling exceeded {timeout_seconds:g} seconds)"
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


def parse_system_memory_free_percent(output: str) -> int:
    match = re.search(r"^System-wide memory free percentage:\s*(\d+)\s*%\s*$", output, re.MULTILINE)
    if not match:
        raise MonitorError("memory_pressure output did not include system-wide free percentage")
    percentage = int(match.group(1))
    if percentage > 100:
        raise MonitorError(f"memory_pressure reported invalid free percentage {percentage}%")
    return percentage


def system_memory_free_percent(timeout_seconds: float = SYSTEM_MEMORY_SAMPLE_TIMEOUT_SECONDS) -> int:
    """Return the host-wide free-memory estimate reported by macOS."""
    if sys.platform != "darwin":
        raise MonitorError("host-wide memory-floor monitoring is supported only on macOS")
    try:
        result = subprocess.run(
            ["memory_pressure"],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as error:
        raise MonitorError(f"memory_pressure sampling exceeded {timeout_seconds:g} seconds") from error
    if result.returncode != 0:
        detail = result.stderr.strip() or f"memory_pressure exited {result.returncode}"
        raise MonitorError(detail)
    return parse_system_memory_free_percent(result.stdout)


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


def percentage(text: str) -> int:
    try:
        value = int(text)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be an integer from 1 through 99") from error
    if value < 1 or value > 99:
        raise argparse.ArgumentTypeError("must be an integer from 1 through 99")
    return value


def rss_termination_threshold(max_rss_kb: int) -> int:
    """Reserve headroom for RSS growth between process-tree samples."""
    reserve_kb = min(RSS_HEADROOM_MAX_KB, max_rss_kb // RSS_HEADROOM_FRACTION_DIVISOR)
    return max_rss_kb - reserve_kb


def run(
    command: Sequence[str],
    max_rss_kb: int,
    timeout_seconds: float,
    poll_seconds: float,
    min_system_free_percent: int | None = None,
    system_memory_poll_seconds: float = SYSTEM_MEMORY_SAMPLE_SECONDS,
    quiet_success_report: bool = False,
    require_initial_system_free_percent: int | None = None,
) -> int:
    if os.name != "posix":
        print("run_bounded_process: POSIX process groups are required", file=sys.stderr)
        return 2
    if not command or not command[0]:
        print("run_bounded_process: missing command", file=sys.stderr)
        return 2

    minimum_system_free_percent = 100
    last_system_memory_sample = 0.0
    if min_system_free_percent is not None or require_initial_system_free_percent is not None:
        try:
            minimum_system_free_percent = system_memory_free_percent()
        except MonitorError as error:
            print(f"run_bounded_process: cannot verify host memory before launch: {error}", file=sys.stderr)
            return 2
        if (
            require_initial_system_free_percent is not None
            and minimum_system_free_percent <= require_initial_system_free_percent
        ):
            print(
                "run_bounded_process: refusing to start command: host system memory free "
                f"percentage is {minimum_system_free_percent}%, initial headroom must be above "
                f"{require_initial_system_free_percent}%",
                file=sys.stderr,
            )
            return 125
        if (
            min_system_free_percent is not None
            and minimum_system_free_percent <= min_system_free_percent
        ):
            print(
                "run_bounded_process: refusing to start command: host system memory free "
                f"percentage is {minimum_system_free_percent}%, must stay above "
                f"{min_system_free_percent}%",
                file=sys.stderr,
            )
            return 125
        if min_system_free_percent is not None:
            last_system_memory_sample = time.monotonic()

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
            remaining_seconds = max(0.001, deadline - time.monotonic())
            rss_kb, group_live, pids = process_group_stats(
                group_id, min(PROCESS_SAMPLE_TIMEOUT_SECONDS, remaining_seconds),
            )
            peak_rss_kb = max(peak_rss_kb, rss_kb)
            if group_live and time.monotonic() >= deadline:
                limit_reason = f"deadline exceeded ({timeout_seconds:g}s)"
                break
            if rss_kb >= rss_threshold_kb:
                limit_reason = (
                    f"aggregate RSS {rss_kb} KiB reached safety threshold "
                    f"{rss_threshold_kb} KiB (configured cap {max_rss_kb} KiB)"
                )
                break
            now = time.monotonic()
            if footprint_available and group_live and now - last_footprint_sample >= FOOTPRINT_SAMPLE_SECONDS:
                sample_timeout = max(0.001, deadline - time.monotonic())
                footprint_bytes = process_group_footprint_bytes(
                    pids, min(FOOTPRINT_SAMPLE_TIMEOUT_SECONDS, sample_timeout),
                )
                footprint_kb = (footprint_bytes + 1023) // 1024
                peak_footprint_kb = max(peak_footprint_kb, footprint_kb)
                last_footprint_sample = time.monotonic()
                if footprint_bytes >= footprint_threshold_bytes:
                    limit_reason = (
                        f"aggregate physical footprint {footprint_kb} KiB reached safety threshold "
                        f"{footprint_threshold_kb} KiB (configured cap {max_rss_kb} KiB)"
                    )
                    break
            if (
                min_system_free_percent is not None
                and group_live
                and now - last_system_memory_sample >= system_memory_poll_seconds
            ):
                sample_timeout = max(0.001, deadline - time.monotonic())
                free_percent = system_memory_free_percent(
                    min(SYSTEM_MEMORY_SAMPLE_TIMEOUT_SECONDS, sample_timeout),
                )
                minimum_system_free_percent = min(minimum_system_free_percent, free_percent)
                last_system_memory_sample = time.monotonic()
                if free_percent <= min_system_free_percent:
                    limit_reason = (
                        f"host system memory free percentage {free_percent}% reached safety floor "
                        f"{min_system_free_percent}%"
                    )
                    break
            if time.monotonic() >= deadline and group_live:
                limit_reason = f"deadline exceeded ({timeout_seconds:g}s)"
                break

            return_code = process.poll()
            if return_code is not None and not group_live:
                if not quiet_success_report or return_code != 0:
                    footprint_report = f"; peak physical footprint {peak_footprint_kb} KiB" if footprint_available else ""
                    system_memory_report = (
                        f"; minimum host free memory {minimum_system_free_percent}%"
                        if min_system_free_percent is not None else ""
                    )
                    print(
                        f"run_bounded_process: peak process-group RSS {peak_rss_kb} KiB"
                        f"{footprint_report}{system_memory_report}",
                        file=sys.stderr,
                    )
                return return_code if return_code >= 0 else 128 - return_code
            remaining_seconds = deadline - time.monotonic()
            if remaining_seconds > 0:
                time.sleep(min(poll_seconds, remaining_seconds))
    except MonitorError as error:
        if time.monotonic() >= deadline:
            limit_reason = f"deadline exceeded ({timeout_seconds:g}s)"
        else:
            # A child can exit between `ps` and `footprint`. Recheck before
            # treating a transient stale-PID report as a reason to terminate.
            try:
                remaining_seconds = max(0.001, deadline - time.monotonic())
                rss_kb, group_live, _ = process_group_stats(
                    group_id, min(PROCESS_SAMPLE_TIMEOUT_SECONDS, remaining_seconds),
                )
                peak_rss_kb = max(peak_rss_kb, rss_kb)
            except MonitorError:
                group_live = True
            if not group_live and process.poll() is not None:
                return_code = process.wait()
                if not quiet_success_report or return_code != 0:
                    footprint_report = f"; peak physical footprint {peak_footprint_kb} KiB" if footprint_available else ""
                    system_memory_report = (
                        f"; minimum host free memory {minimum_system_free_percent}%"
                        if min_system_free_percent is not None else ""
                    )
                    print(
                        f"run_bounded_process: peak process-group RSS {peak_rss_kb} KiB"
                        f"{footprint_report}{system_memory_report}",
                        file=sys.stderr,
                    )
                return return_code if return_code >= 0 else 128 - return_code
            limit_reason = (
                f"deadline exceeded ({timeout_seconds:g}s)"
                if time.monotonic() >= deadline
                else f"could not monitor owned process group: {error}"
            )
    except KeyboardInterrupt:
        terminate_group(group_id, process)
        return 130

    process_details = process_group_breakdown(group_id)
    terminate_group(group_id, process)
    footprint_report = f"; peak physical footprint {peak_footprint_kb} KiB" if footprint_available else ""
    system_memory_report = (
        f"; minimum host free memory {minimum_system_free_percent}%"
        if min_system_free_percent is not None else ""
    )
    print(
        f"run_bounded_process: {limit_reason}; terminated owned process group "
        f"{group_id} (peak RSS {peak_rss_kb} KiB{footprint_report}{system_memory_report})\n"
        f"run_bounded_process: process-group members at limit: {process_details}",
        file=sys.stderr,
    )
    return 124 if limit_reason.startswith("deadline") else 125


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-rss-kb", type=positive_int, required=True)
    parser.add_argument("--timeout-seconds", type=positive_float, required=True)
    parser.add_argument("--poll-seconds", type=positive_float, default=0.1)
    parser.add_argument(
        "--min-system-free-percent",
        type=percentage,
        default=os.environ.get("ELISA_SETUP_MIN_SYSTEM_FREE_PERCENT"),
    )
    parser.add_argument(
        "--require-initial-system-free-percent",
        type=percentage,
        help="refuse launch unless host free memory initially exceeds this percentage; live monitoring uses --min-system-free-percent",
    )
    parser.add_argument("--system-memory-poll-seconds", type=positive_float, default=SYSTEM_MEMORY_SAMPLE_SECONDS)
    parser.add_argument(
        "--quiet-success-report",
        action="store_true",
        help="do not append resource telemetry to stderr when the child succeeds",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER)
    arguments = parser.parse_args(argv)
    command = arguments.command
    if command and command[0] == "--":
        command = command[1:]
    return run(
        command,
        arguments.max_rss_kb,
        arguments.timeout_seconds,
        arguments.poll_seconds,
        arguments.min_system_free_percent,
        arguments.system_memory_poll_seconds,
        arguments.quiet_success_report,
        arguments.require_initial_system_free_percent,
    )


if __name__ == "__main__":
    raise SystemExit(main())
