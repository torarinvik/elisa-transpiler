#!/usr/bin/env python3
"""Bounded self-tests for the manifest fixture runner."""

import contextlib
import json
import importlib.util
import io
import os
import signal
import sys
import tempfile
import time
import unittest
from unittest import mock
from pathlib import Path
from types import SimpleNamespace


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
RUNNER_PATH = Path(__file__).with_name("run_fixture_manifest.py")
SPEC = importlib.util.spec_from_file_location("fixture_manifest_under_test", RUNNER_PATH)
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


def python_argv(code):
    return [sys.executable, "-c", code]


def base_case(stdout_code="same", expected_exit=42):
    output_code = "import sys;sys.stdout.write(%r);sys.exit(%d)" % (stdout_code, expected_exit)
    return {
        "name": "runner_self_test",
        "source": "testdata/fixtures/simple.c",
        "timeout_seconds": 2,
        "translate_argv": python_argv("import sys;sys.stdout.write('def main(): pass')"),
        "generated_checks": {"contains_regex": ["def main"]},
        "native_build_argv": python_argv("pass"),
        "elisa_compile_argv": python_argv("pass"),
        "elisa_link_argv": python_argv("pass"),
        "native_run_argv": python_argv(output_code),
        "elisa_run_argv": python_argv(output_code),
        "expected_exit_code": expected_exit,
        "compare": ["stdout", "stderr", "exit_code"],
        "capture_files": [],
    }


def run_arguments(output_dir, timeout=None, max_rss_kb=None):
    return SimpleNamespace(
        output_dir=output_dir,
        timeout_seconds=timeout,
        default_timeout_seconds=2,
        translator=sys.executable,
        elisa_compiler=sys.executable,
        max_rss_kb=max_rss_kb,
        max_output_bytes=RUNNER.DEFAULT_STAGE_OUTPUT_BYTES,
    )


class FixtureManifestRunnerTests(unittest.TestCase):
    def run_case_quietly(self, case, output_dir):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return RUNNER.run_case(case, run_arguments(output_dir))

    def test_captures_both_streams_and_accepts_nonzero_exit(self):
        with tempfile.TemporaryDirectory(prefix="elisa-fixture-runner-test-") as temporary:
            case_dir = Path(temporary)
            argv = python_argv("import sys;sys.stdout.write('out');sys.stderr.write('err');sys.exit(42)")
            result, stdout, stderr = RUNNER.run_command(case_dir, "capture", argv, 2)
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["return_code"], 42)
            self.assertEqual(stdout, b"out")
            self.assertEqual(stderr, b"err")
            self.assertEqual(Path(result["stdout_file"]).read_bytes(), b"out")
            self.assertEqual(Path(result["stderr_file"]).read_bytes(), b"err")

    @unittest.skipUnless(os.name == "posix", "process-group output limits are POSIX-specific")
    def test_output_limit_is_enforced_without_buffering_child_streams_in_memory(self):
        with tempfile.TemporaryDirectory(prefix="elisa-fixture-runner-test-") as temporary:
            code = "import sys,time;sys.stdout.buffer.write(b'x'*1024);sys.stdout.flush();time.sleep(2)"
            result, stdout, stderr = RUNNER.run_command(
                Path(temporary), "output-limit", python_argv(code), 5, max_output_bytes=512
            )
            self.assertEqual(result["status"], "resource_limited", stderr.decode("utf-8", "replace"))
            self.assertIn("output", result["limit_reason"])
            self.assertEqual(len(stdout), 1024)
            self.assertEqual(Path(result["stdout_file"]).read_bytes(), stdout)

    def test_host_memory_floor_refuses_launch_at_threshold(self):
        with tempfile.TemporaryDirectory(prefix="elisa-fixture-runner-test-") as temporary:
            marker = Path(temporary) / "child-started"
            command = python_argv("from pathlib import Path;Path(%r).touch()" % str(marker))
            with mock.patch.object(RUNNER.bounded_process, "system_memory_free_percent", return_value=40):
                result, stdout, stderr = RUNNER.run_command(
                    Path(temporary), "host-floor", command, 2, min_system_free_percent=40
                )
            self.assertEqual(result["status"], "resource_limited", stderr.decode("utf-8", "replace"))
            self.assertIn("before launch", result["limit_reason"])
            self.assertEqual(result["minimum_system_free_percent"], 40)
            self.assertEqual(stdout, b"")
            self.assertFalse(marker.exists())

    def test_host_memory_sampler_failure_refuses_launch(self):
        with tempfile.TemporaryDirectory(prefix="elisa-fixture-runner-test-") as temporary:
            marker = Path(temporary) / "child-started"
            command = python_argv("from pathlib import Path;Path(%r).touch()" % str(marker))
            with mock.patch.object(
                RUNNER.bounded_process,
                "system_memory_free_percent",
                side_effect=RUNNER.bounded_process.MonitorError("sampler unavailable"),
            ):
                result, stdout, stderr = RUNNER.run_command(
                    Path(temporary), "host-monitor-error", command, 2,
                    min_system_free_percent=40,
                )
            self.assertEqual(result["status"], "monitor_error", stderr.decode("utf-8", "replace"))
            self.assertIn("sampler unavailable", result["limit_reason"])
            self.assertEqual(stdout, b"")
            self.assertFalse(marker.exists())

    @unittest.skipUnless(os.name == "posix", "host-memory termination uses owned process groups")
    def test_falling_host_memory_floor_terminates_owned_stage(self):
        with tempfile.TemporaryDirectory(prefix="elisa-fixture-runner-test-") as temporary:
            with (
                mock.patch.object(
                    RUNNER.bounded_process,
                    "system_memory_free_percent",
                    side_effect=[80, 39],
                ),
                mock.patch.object(RUNNER, "PROCESS_POLL_SECONDS", 0.01),
            ):
                result, _, stderr = RUNNER.run_command(
                    Path(temporary),
                    "host-floor-drop",
                    python_argv("import time;time.sleep(30)"),
                    5,
                    min_system_free_percent=40,
                    system_memory_poll_seconds=0.01,
                )
            self.assertEqual(result["status"], "resource_limited", stderr.decode("utf-8", "replace"))
            self.assertIn("39% reached safety floor 40%", result["limit_reason"])
            self.assertEqual(result["minimum_system_free_percent"], 39)
            self.assertIn("owned process group members", stderr.decode("utf-8", "replace"))

    def test_case_compares_expected_nonzero_exit(self):
        with tempfile.TemporaryDirectory(prefix="elisa-fixture-runner-test-") as temporary:
            result = self.run_case_quietly(base_case(), Path(temporary))
            self.assertEqual(result["status"], "passed")

    def test_matching_runtime_is_added_to_elisa_link_only(self):
        with tempfile.TemporaryDirectory(prefix="elisa-fixture-runner-test-") as temporary:
            case = base_case()
            runtime = Path(temporary) / "elisacore_runtime.o"
            runtime.write_bytes(b"test runtime placeholder")
            arguments = run_arguments(Path(temporary) / "out")
            arguments.elisa_runtime = str(runtime)
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                result = RUNNER.run_case(case, arguments)
            self.assertEqual(result["status"], "passed")
            stages = {stage["stage"]: stage for stage in result["stages"]}
            self.assertEqual(stages["elisa_link"]["argv"][-1], str(runtime))
            self.assertNotIn(str(runtime), stages["native_build"]["argv"])

    def test_wrong_expected_exit_fails_at_execution_stage(self):
        with tempfile.TemporaryDirectory(prefix="elisa-fixture-runner-test-") as temporary:
            case = base_case()
            case["expected_exit_code"] = 0
            result = self.run_case_quietly(case, Path(temporary))
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["failure"]["stage"], "native_run")

    def test_native_output_mismatch_fails_differential_stage(self):
        with tempfile.TemporaryDirectory(prefix="elisa-fixture-runner-test-") as temporary:
            case = base_case()
            case["elisa_run_argv"] = python_argv("import sys;sys.stdout.write('different');sys.exit(42)")
            result = self.run_case_quietly(case, Path(temporary))
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["failure"]["stage"], "differential_comparison")

    def test_missing_tool_is_distinct(self):
        with tempfile.TemporaryDirectory(prefix="elisa-fixture-runner-test-") as temporary:
            case = base_case()
            case["translate_argv"] = [str(Path(temporary) / "no-such-translator")]
            result = self.run_case_quietly(case, Path(temporary) / "output")
            self.assertEqual(result["status"], "missing_tool")
            self.assertEqual(result["failure"]["stage"], "translate")

    def test_unsupported_translation_is_distinct(self):
        with tempfile.TemporaryDirectory(prefix="elisa-fixture-runner-test-") as temporary:
            case = base_case()
            case["translate_argv"] = python_argv("import sys;sys.stderr.write('unsupported statement');sys.exit(1)")
            result = self.run_case_quietly(case, Path(temporary))
            self.assertEqual(result["status"], "unsupported")

    def test_signal_termination_is_a_crash(self):
        with tempfile.TemporaryDirectory(prefix="elisa-fixture-runner-test-") as temporary:
            case = base_case()
            case["translate_argv"] = python_argv("import os,signal;os.kill(os.getpid(),signal.SIGTERM)")
            result = self.run_case_quietly(case, Path(temporary))
            self.assertEqual(result["status"], "crashed")

    def test_optional_skip_is_reported(self):
        with tempfile.TemporaryDirectory(prefix="elisa-fixture-runner-test-") as temporary:
            case = {"name": "optional", "optional": True, "skip_reason": "compiler capability unavailable"}
            result = self.run_case_quietly(case, Path(temporary))
            self.assertEqual(result["status"], "skipped")
            self.assertEqual(result["skip_reason"], "compiler capability unavailable")

    def test_invalid_manifest_shapes_are_reported_cleanly(self):
        invalid_manifests = (
            {"schema_version": 1, "cases": [None]},
            {"schema_version": 1, "cases": [dict(base_case(), name="../escape")]},
            {"schema_version": 1, "cases": [dict(base_case(), timeout_seconds=0)]},
            {"schema_version": 1, "cases": [dict(base_case(), expected_exit_code=True)]},
        )
        with tempfile.TemporaryDirectory(prefix="elisa-fixture-runner-test-") as temporary:
            manifest_path = Path(temporary) / "invalid.json"
            for manifest in invalid_manifests:
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                with self.assertRaises(RUNNER.ManifestError):
                    RUNNER.load_manifest(manifest_path)

    def test_unknown_capture_placeholder_is_a_manifest_error(self):
        with self.assertRaises(RUNNER.ManifestError):
            RUNNER.substitute_template("{not_a_runner_path}", {}, "self_test.capture_files")

    @unittest.skipUnless(os.name == "posix", "process-group timeout behavior is POSIX-specific")
    def test_timeout_kills_child_process_group(self):
        with tempfile.TemporaryDirectory(prefix="elisa-fixture-runner-test-") as temporary:
            marker = Path(temporary) / "child-survived"
            child_code = "import pathlib,time;time.sleep(0.5);pathlib.Path(%r).touch()" % str(marker)
            parent_code = "import subprocess,sys,time;subprocess.Popen([sys.executable,'-c',%r]);time.sleep(30)" % child_code
            result, _, _ = RUNNER.run_command(Path(temporary), "timeout", python_argv(parent_code), 0.1)
            self.assertEqual(result["status"], "timed_out")
            time.sleep(0.6)
            self.assertFalse(marker.exists(), "timed-out child outlived its process group")

    @unittest.skipUnless(os.name == "posix", "process-group RSS monitoring is POSIX-specific")
    def test_rss_limit_kills_owned_stage_and_is_classified(self):
        with tempfile.TemporaryDirectory(prefix="elisa-fixture-runner-test-") as temporary:
            code = (
                "import time; blocks=[]\n"
                "while True:\n"
                " block=bytearray(4*1024*1024)\n"
                " block[::4096]=b'x'*(len(block)//4096)\n"
                " blocks.append(block)\n"
                " time.sleep(0.02)\n"
            )
            result, _, stderr = RUNNER.run_command(
                Path(temporary), "rss-limit", python_argv(code), 5, max_rss_kb=65536
            )
            self.assertEqual(result["status"], "resource_limited", stderr.decode("utf-8", "replace"))
            self.assertGreater(result["peak_rss_kb"], 0)
            self.assertTrue(
                "aggregate RSS" in result["limit_reason"]
                or "aggregate physical footprint" in result["limit_reason"],
                result["limit_reason"],
            )
            self.assertIn("owned process group members", stderr.decode("utf-8", "replace"))

    @unittest.skipUnless(os.name == "posix", "process-group footprint monitoring is POSIX-specific")
    def test_disappearing_process_during_footprint_sample_is_normal_completion(self):
        with tempfile.TemporaryDirectory(prefix="elisa-fixture-runner-test-") as temporary:
            real_popen = RUNNER.subprocess.Popen
            launched = []

            def launch(*args, **kwargs):
                process = real_popen(*args, **kwargs)
                launched.append(process)
                return process

            samples = 0

            def process_group_stats(group_id):
                nonlocal samples
                samples += 1
                self.assertEqual(group_id, launched[0].pid)
                if samples == 1:
                    return 0, True, [group_id]
                if samples == 2:
                    return 0, False, []
                self.fail("completed process group should not be sampled again")

            def disappearing_footprint(_pids):
                launched[0].wait(timeout=2)
                raise RUNNER.bounded_process.MonitorError("sampled PID exited before footprint lookup")

            with (
                mock.patch.object(RUNNER.subprocess, "Popen", side_effect=launch),
                mock.patch.object(RUNNER.bounded_process, "process_group_stats", side_effect=process_group_stats),
                mock.patch.object(RUNNER.bounded_process, "process_group_footprint_bytes", side_effect=disappearing_footprint),
                mock.patch.object(RUNNER.shutil, "which", return_value="/usr/bin/footprint"),
                mock.patch.object(RUNNER.sys, "platform", "darwin"),
                mock.patch.object(RUNNER.bounded_process, "FOOTPRINT_SAMPLE_SECONDS", 0),
            ):
                result, stdout, stderr = RUNNER.run_command(
                    Path(temporary), "vanishing-footprint-pid", python_argv("print('finished')"), 2, max_rss_kb=65536
                )

            self.assertEqual(result["status"], "completed", stderr.decode("utf-8", "replace"))
            self.assertEqual(result["return_code"], 0)
            self.assertEqual(stdout, b"finished\n")
            self.assertEqual(samples, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
