#!/usr/bin/env python3
"""Regression checks for process-group RSS and deadline enforcement."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import run_bounded_process


RUNNER = SCRIPT_DIR / "run_bounded_process.py"


class BoundedProcessTests(unittest.TestCase):
    def invoke(self, *arguments: str, timeout: float = 10) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(RUNNER), *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def test_passes_exit_code_and_child_output(self) -> None:
        result = self.invoke(
            "--max-rss-kb", "262144", "--timeout-seconds", "5", "--",
            sys.executable, "-c", "print('bounded-child'); raise SystemExit(23)",
        )
        self.assertEqual(result.returncode, 23, result.stderr)
        self.assertIn("bounded-child", result.stdout)
        self.assertIn("peak process-group RSS", result.stderr)

    def test_deadline_kills_parent_and_child_group(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            pid_file = Path(temporary) / "child.pid"
            child_code = "import time; time.sleep(30)"
            parent_code = (
                "import subprocess,sys,time; "
                f"child=subprocess.Popen([sys.executable,'-c',{child_code!r}]); "
                f"open({str(pid_file)!r},'w').write(str(child.pid)); "
                "time.sleep(30)"
            )
            result = self.invoke(
                "--max-rss-kb", "262144", "--timeout-seconds", "0.4",
                "--poll-seconds", "0.05", "--", sys.executable, "-c", parent_code,
            )
            self.assertEqual(result.returncode, 124, result.stderr)
            self.assertIn("terminated owned process group", result.stderr)
            self.assertTrue(pid_file.exists(), result.stderr)
            with pid_file.open() as stream:
                child_pid = int(stream.read())
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                try:
                    os.kill(child_pid, 0)
                except ProcessLookupError:
                    break
                time.sleep(0.05)
            else:
                # A zombie is no longer executing and is excluded from live group
                # accounting; verify its process state instead of mistaking it for
                # an orphan that escaped the wrapper.
                state = subprocess.run(
                    ["ps", "-o", "stat=", "-p", str(child_pid)],
                    capture_output=True,
                    text=True,
                    check=False,
                ).stdout.strip()
                self.assertTrue(not state or state.startswith("Z"), f"child still running: {state}")

    def test_poll_interval_cannot_extend_the_deadline(self) -> None:
        started = time.monotonic()
        result = self.invoke(
            "--max-rss-kb", "262144", "--timeout-seconds", "0.25",
            "--poll-seconds", "10", "--", sys.executable, "-c",
            "import time; time.sleep(30)",
            timeout=4,
        )
        elapsed = time.monotonic() - started
        self.assertEqual(result.returncode, 124, result.stderr)
        self.assertIn("deadline exceeded (0.25s)", result.stderr)
        self.assertLess(elapsed, 2.5, f"poll interval delayed deadline for {elapsed:.2f}s")

    @unittest.skipUnless(os.name == "posix" and shutil.which("ps"), "POSIX process sampling")
    def test_slow_process_sampler_is_capped_by_the_remaining_deadline(self) -> None:
        real_ps = shutil.which("ps")
        assert real_ps is not None
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            fake_ps = temporary_path / "ps"
            marker = temporary_path / "first-call"
            fake_ps.write_text(
                f"#!{sys.executable}\n"
                "import os, sys, time\n"
                f"marker = {str(marker)!r}\n"
                f"real_ps = {real_ps!r}\n"
                "if not os.path.exists(marker):\n"
                "    open(marker, 'w').close()\n"
                "    time.sleep(5)\n"
                "os.execv(real_ps, [real_ps, *sys.argv[1:]])\n",
                encoding="utf-8",
            )
            fake_ps.chmod(0o755)
            environment = os.environ.copy()
            environment["PATH"] = f"{temporary}{os.pathsep}{environment.get('PATH', '')}"
            started = time.monotonic()
            result = subprocess.run(
                [
                    sys.executable, str(RUNNER), "--max-rss-kb", "262144",
                    "--timeout-seconds", "0.25", "--poll-seconds", "0.02", "--",
                    sys.executable, "-c", "import time; time.sleep(30)",
                ],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
                timeout=4,
            )
            elapsed = time.monotonic() - started
        self.assertEqual(result.returncode, 124, result.stderr)
        self.assertIn("deadline exceeded (0.25s)", result.stderr)
        self.assertLess(elapsed, 3.0, f"slow monitor delayed deadline for {elapsed:.2f}s")

    def test_rss_limit_kills_owned_group(self) -> None:
        allocation_code = "import time; data=bytearray(24*1024*1024); data[::4096]=b'x'*(len(data)//4096); time.sleep(30)"
        result = self.invoke(
            "--max-rss-kb", "12288", "--timeout-seconds", "5",
            "--poll-seconds", "0.05", "--", sys.executable, "-c", allocation_code,
        )
        self.assertEqual(result.returncode, 125, result.stderr)
        self.assertTrue(
            "aggregate RSS" in result.stderr or "aggregate physical footprint" in result.stderr,
            result.stderr,
        )
        self.assertIn("safety threshold", result.stderr)
        self.assertIn("process-group members at limit:", result.stderr)
        self.assertIn("rss=", result.stderr)
        self.assertIn("terminated owned process group", result.stderr)

    def test_parses_macos_physical_footprint(self) -> None:
        summary = subprocess.CompletedProcess(
            args=["footprint"], returncode=0,
            stdout="Auxiliary data:\n    phys_footprint: 100 B\nSummary Footprint: 321 B\n",
            stderr="",
        )
        with mock.patch.object(run_bounded_process.subprocess, "run", return_value=summary):
            self.assertEqual(run_bounded_process.process_group_footprint_bytes([11, 12]), 321)

        single = subprocess.CompletedProcess(
            args=["footprint"], returncode=0,
            stdout="Auxiliary data:\n    phys_footprint: 456 B\n",
            stderr="",
        )
        with mock.patch.object(run_bounded_process.subprocess, "run", return_value=single):
            self.assertEqual(run_bounded_process.process_group_footprint_bytes([11]), 456)

    def test_parses_host_free_memory_percentage(self) -> None:
        self.assertEqual(
            run_bounded_process.parse_system_memory_free_percent(
                "System-wide memory free percentage: 53%\n"
            ),
            53,
        )
        for output in (
            "System-wide memory free percentage: unavailable\n",
            "System-wide memory free percentage: 101%\n",
        ):
            with self.subTest(output=output), self.assertRaises(run_bounded_process.MonitorError):
                run_bounded_process.parse_system_memory_free_percent(output)

    @unittest.skipUnless(sys.platform == "darwin", "macOS host-memory monitoring")
    def test_host_memory_floor_refuses_launch_below_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fake_memory_pressure = Path(temporary) / "memory_pressure"
            fake_memory_pressure.write_text(
                "#!/bin/sh\nprintf 'System-wide memory free percentage: 20%%\\n'\n"
            )
            fake_memory_pressure.chmod(0o755)
            sentinel = Path(temporary) / "child-started"
            environment = os.environ.copy()
            environment["PATH"] = f"{temporary}{os.pathsep}{environment.get('PATH', '')}"
            result = subprocess.run(
                [
                    sys.executable, str(RUNNER), "--max-rss-kb", "262144",
                    "--timeout-seconds", "5", "--min-system-free-percent", "40", "--",
                    sys.executable, "-c", f"open({str(sentinel)!r}, 'w').close()",
                ],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
                timeout=10,
            )
            self.assertEqual(result.returncode, 125, result.stderr)
            self.assertIn("refusing to start command", result.stderr)
            self.assertFalse(sentinel.exists())

    @unittest.skipUnless(sys.platform == "darwin", "macOS host-memory monitoring")
    def test_initial_headroom_gate_is_separate_from_live_floor(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fake_memory_pressure = Path(temporary) / "memory_pressure"
            sample_count = Path(temporary) / "sample-count"
            fake_memory_pressure.write_text(
                "#!/bin/sh\n"
                f"count_file={str(sample_count)!r}\n"
                "count=0\n"
                "[ ! -f \"$count_file\" ] || count=$(cat \"$count_file\")\n"
                "count=$((count + 1))\n"
                "printf '%s\\n' \"$count\" > \"$count_file\"\n"
                "free=85\n"
                "[ \"$count\" -eq 1 ] || free=70\n"
                "printf 'System-wide memory free percentage: %s%%\\n' \"$free\"\n"
            )
            fake_memory_pressure.chmod(0o755)
            environment = os.environ.copy()
            environment["PATH"] = f"{temporary}{os.pathsep}{environment.get('PATH', '')}"
            # Keep the child alive until the runner has taken at least one
            # post-launch sample. A fixed short sleep can finish before that
            # sample when the host is busy, making this gate test scheduling-
            # dependent rather than testing the initial/live threshold split.
            child_code = (
                "import pathlib,time\n"
                f"sample_count=pathlib.Path({str(sample_count)!r})\n"
                "while True:\n"
                " try:\n"
                "  if int(sample_count.read_text(encoding='utf-8')) >= 2: break\n"
                " except (OSError,ValueError): pass\n"
                " time.sleep(0.01)\n"
            )
            result = subprocess.run(
                [
                    sys.executable, str(RUNNER), "--max-rss-kb", "262144",
                    "--timeout-seconds", "5", "--min-system-free-percent", "60",
                    "--require-initial-system-free-percent", "80",
                    "--system-memory-poll-seconds", "0.01", "--",
                    sys.executable, "-c", child_code,
                ],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertGreaterEqual(int(sample_count.read_text()), 2)

    @unittest.skipUnless(sys.platform == "darwin", "macOS host-memory monitoring")
    def test_initial_headroom_gate_refuses_launch_before_child_starts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fake_memory_pressure = Path(temporary) / "memory_pressure"
            fake_memory_pressure.write_text(
                "#!/bin/sh\nprintf 'System-wide memory free percentage: 80%%\\n'\n"
            )
            fake_memory_pressure.chmod(0o755)
            sentinel = Path(temporary) / "child-started"
            environment = os.environ.copy()
            environment["PATH"] = f"{temporary}{os.pathsep}{environment.get('PATH', '')}"
            result = subprocess.run(
                [
                    sys.executable, str(RUNNER), "--max-rss-kb", "262144",
                    "--timeout-seconds", "5", "--min-system-free-percent", "60",
                    "--require-initial-system-free-percent", "80", "--",
                    sys.executable, "-c", f"open({str(sentinel)!r}, 'w').close()",
                ],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
                timeout=10,
            )
            self.assertEqual(result.returncode, 125, result.stderr)
            self.assertIn("initial headroom must be above 80%", result.stderr)
            self.assertFalse(sentinel.exists())

    @unittest.skipUnless(sys.platform == "darwin", "macOS host-memory monitoring")
    def test_environment_host_memory_floor_is_used_without_cli_override(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fake_memory_pressure = Path(temporary) / "memory_pressure"
            fake_memory_pressure.write_text(
                "#!/bin/sh\nprintf 'System-wide memory free percentage: 40%%\\n'\n"
            )
            fake_memory_pressure.chmod(0o755)
            sentinel = Path(temporary) / "child-started"
            environment = os.environ.copy()
            environment["PATH"] = f"{temporary}{os.pathsep}{environment.get('PATH', '')}"
            environment["ELISA_SETUP_MIN_SYSTEM_FREE_PERCENT"] = "40"
            result = subprocess.run(
                [
                    sys.executable, str(RUNNER), "--max-rss-kb", "262144",
                    "--timeout-seconds", "5", "--",
                    sys.executable, "-c", f"open({str(sentinel)!r}, 'w').close()",
                ],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
                timeout=10,
            )
            self.assertEqual(result.returncode, 125, result.stderr)
            self.assertIn("refusing to start command", result.stderr)
            self.assertIn("must stay above 40%", result.stderr)
            self.assertFalse(sentinel.exists())

    @unittest.skipUnless(sys.platform == "darwin", "macOS host-memory monitoring")
    def test_host_memory_sampler_failure_refuses_launch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fake_memory_pressure = Path(temporary) / "memory_pressure"
            fake_memory_pressure.write_text("#!/bin/sh\necho sampler-failed >&2\nexit 1\n")
            fake_memory_pressure.chmod(0o755)
            sentinel = Path(temporary) / "child-started"
            environment = os.environ.copy()
            environment["PATH"] = f"{temporary}{os.pathsep}{environment.get('PATH', '')}"
            result = subprocess.run(
                [
                    sys.executable, str(RUNNER), "--max-rss-kb", "262144",
                    "--timeout-seconds", "5", "--min-system-free-percent", "40", "--",
                    sys.executable, "-c", f"open({str(sentinel)!r}, 'w').close()",
                ],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
                timeout=10,
            )
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("cannot verify host memory before launch", result.stderr)
            self.assertIn("sampler-failed", result.stderr)
            self.assertFalse(sentinel.exists())

    @unittest.skipUnless(sys.platform == "darwin", "macOS host-memory monitoring")
    def test_host_memory_floor_terminates_owned_group(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            counter = Path(temporary) / "memory-pressure-count"
            fake_memory_pressure = Path(temporary) / "memory_pressure"
            fake_memory_pressure.write_text(
                "#!/bin/sh\n"
                f"count_file={str(counter)!r}\n"
                "count=0\n"
                "if [ -f \"$count_file\" ]; then count=$(cat \"$count_file\"); fi\n"
                "count=$((count + 1))\n"
                "printf '%s' \"$count\" > \"$count_file\"\n"
                "if [ \"$count\" -eq 1 ]; then free=80; else free=39; fi\n"
                "printf 'System-wide memory free percentage: %s%%\\n' \"$free\"\n"
            )
            fake_memory_pressure.chmod(0o755)
            environment = os.environ.copy()
            environment["PATH"] = f"{temporary}{os.pathsep}{environment.get('PATH', '')}"
            result = subprocess.run(
                [
                    sys.executable, str(RUNNER), "--max-rss-kb", "262144",
                    "--timeout-seconds", "5", "--poll-seconds", "0.02",
                    "--min-system-free-percent", "40", "--system-memory-poll-seconds", "0.05", "--",
                    sys.executable, "-c", "import time; time.sleep(30)",
                ],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
                timeout=10,
            )
            self.assertEqual(result.returncode, 125, result.stderr)
            self.assertIn("host system memory free percentage 39%", result.stderr)
            self.assertIn("terminated owned process group", result.stderr)

    @unittest.skipUnless(sys.platform == "darwin", "macOS physical-footprint monitoring")
    def test_physical_footprint_limit_kills_owned_group(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fake_footprint = Path(temporary) / "footprint"
            fake_footprint.write_text("#!/bin/sh\nprintf 'Summary Footprint: 999999999 B\\n'\n")
            fake_footprint.chmod(0o755)
            environment = os.environ.copy()
            environment["PATH"] = f"{temporary}{os.pathsep}{environment.get('PATH', '')}"
            result = subprocess.run(
                [
                    sys.executable, str(RUNNER),
                    "--max-rss-kb", "262144", "--timeout-seconds", "5",
                    "--poll-seconds", "0.05", "--",
                    sys.executable, "-c", "import time; time.sleep(30)",
                ],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
                timeout=10,
            )
            self.assertEqual(result.returncode, 125, result.stderr)
            self.assertIn("aggregate physical footprint", result.stderr)
            self.assertIn("terminated owned process group", result.stderr)

    def test_rejects_invalid_limits_without_starting_command(self) -> None:
        result = self.invoke("--max-rss-kb", "0", "--timeout-seconds", "5", "--", sys.executable, "-c", "raise SystemExit(99)")
        self.assertEqual(result.returncode, 2)
        self.assertIn("positive integer", result.stderr)

    def test_rejects_invalid_host_memory_floor(self) -> None:
        result = self.invoke(
            "--max-rss-kb", "262144", "--timeout-seconds", "5",
            "--min-system-free-percent", "100", "--", sys.executable,
            "-c", "raise SystemExit(99)",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("1 through 99", result.stderr)

    def test_rejects_invalid_initial_host_memory_threshold(self) -> None:
        result = self.invoke(
            "--max-rss-kb", "262144", "--timeout-seconds", "5",
            "--require-initial-system-free-percent", "100", "--", sys.executable,
            "-c", "raise SystemExit(99)",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("1 through 99", result.stderr)


if __name__ == "__main__":
    unittest.main()
