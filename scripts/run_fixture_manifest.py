#!/usr/bin/env python3
"""Run manifest-described native-vs-Elisa executable fixtures without a shell."""

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import run_bounded_process as bounded_process


ROOT = Path(__file__).resolve().parent.parent
OUTCOMES = ("passed", "failed", "timed_out", "crashed", "resource_limited", "monitor_error", "unsupported", "skipped", "missing_tool")
PROCESS_POLL_SECONDS = 0.02
DEFAULT_STAGE_OUTPUT_BYTES = 64 * 1024 * 1024


class ManifestError(Exception):
    pass


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp." + str(os.getpid()))
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(str(temporary), str(path))


def substitute_template(template, values, field_name):
    try:
        return template.format_map(values)
    except KeyError as error:
        raise ManifestError("unknown placeholder %s in %s" % (error.args[0], field_name))


def substitute_argv(template, values, field_name):
    if not isinstance(template, list) or not template:
        raise ManifestError("%s must be a non-empty argv array" % field_name)
    result = []
    for part in template:
        if not isinstance(part, str):
            raise ManifestError("%s entries must be strings" % field_name)
        result.append(substitute_template(part, values, field_name))
    return result


def run_command(case_dir, stage, argv, timeout_seconds, max_rss_kb=None, max_output_bytes=DEFAULT_STAGE_OUTPUT_BYTES):
    started = time.monotonic()
    stdout_path = case_dir / (stage + ".stdout.bin")
    stderr_path = case_dir / (stage + ".stderr.bin")
    result = {
        "stage": stage,
        "argv": argv,
        "timeout_seconds": timeout_seconds,
        "status": "completed",
        "return_code": None,
        "duration_seconds": None,
        "stdout_file": str(stdout_path),
        "stderr_file": str(stderr_path),
    }
    if max_rss_kb is not None:
        result["max_rss_kb"] = max_rss_kb
    result["max_output_bytes"] = max_output_bytes
    stdout_stream = stdout_path.open("wb")
    stderr_stream = stderr_path.open("wb")
    try:
        process = subprocess.Popen(
            argv,
            cwd=str(ROOT),
            stdin=subprocess.DEVNULL,
            stdout=stdout_stream,
            stderr=stderr_stream,
            start_new_session=(os.name == "posix"),
        )
    except FileNotFoundError as error:
        stdout_stream.close()
        stderr_stream.close()
        stderr_path.write_text(str(error) + "\n", encoding="utf-8")
        result["status"] = "missing_tool"
        result["error"] = str(error)
        result["duration_seconds"] = round(time.monotonic() - started, 6)
        return result, b"", str(error).encode("utf-8", "replace")
    except OSError as error:
        stdout_stream.close()
        stderr_stream.close()
        stderr_path.write_text(str(error) + "\n", encoding="utf-8")
        result["status"] = "launch_error"
        result["error"] = str(error)
        result["duration_seconds"] = round(time.monotonic() - started, 6)
        return result, b"", str(error).encode("utf-8", "replace")

    group_id = process.pid
    deadline = started + timeout_seconds
    rss_threshold_kb = bounded_process.rss_termination_threshold(max_rss_kb) if max_rss_kb is not None else None
    footprint_threshold_bytes = None
    if rss_threshold_kb is not None:
        memory_threshold_bytes = rss_threshold_kb * 1024
        footprint_threshold_bytes = memory_threshold_bytes - memory_threshold_bytes // bounded_process.FOOTPRINT_HEADROOM_FRACTION_DIVISOR
    footprint_available = max_rss_kb is not None and sys.platform == "darwin" and shutil.which("footprint") is not None
    last_footprint_sample = 0.0
    peak_rss_kb = 0
    peak_footprint_kb = 0
    limit_reason = ""
    process_details = ""

    while True:
        group_live = process.poll() is None
        pids = [group_id] if group_live else []
        rss_kb = 0
        if os.name == "posix":
            try:
                rss_kb, group_live, pids = bounded_process.process_group_stats(group_id)
            except bounded_process.MonitorError as error:
                # As with the shared bounded launcher, a process may exit
                # between `ps` and a follow-up sample. Do not turn that normal
                # race into a test failure; only fail closed if the owned group
                # still has a live member or its state remains unknowable.
                try:
                    rss_kb, group_live, pids = bounded_process.process_group_stats(group_id)
                except bounded_process.MonitorError:
                    group_live = True
                    rss_kb = peak_rss_kb
                    pids = []
                if group_live or process.poll() is None:
                    limit_reason = "could not monitor owned process group: " + str(error)
                    result["status"] = "monitor_error"
                    process_details = bounded_process.process_group_breakdown(group_id)
                    bounded_process.terminate_group(group_id, process)
                    break

        peak_rss_kb = max(peak_rss_kb, rss_kb)
        stdout_size = stdout_path.stat().st_size
        stderr_size = stderr_path.stat().st_size
        combined_output_size = stdout_size + stderr_size
        now = time.monotonic()
        if combined_output_size > max_output_bytes:
            limit_reason = "combined stdout/stderr output %d bytes exceeded cap %d bytes" % (combined_output_size, max_output_bytes)
        elif rss_threshold_kb is not None and rss_kb >= rss_threshold_kb:
            limit_reason = (
                "aggregate RSS %d KiB reached safety threshold %d KiB (configured cap %d KiB)"
                % (rss_kb, rss_threshold_kb, max_rss_kb)
            )
        elif not limit_reason and footprint_available and group_live and now - last_footprint_sample >= bounded_process.FOOTPRINT_SAMPLE_SECONDS:
            try:
                footprint_bytes = bounded_process.process_group_footprint_bytes(pids)
            except bounded_process.MonitorError as error:
                # A PID can disappear after the ps snapshot. Recheck the
                # owned group before classifying a missing footprint record
                # as an inability to enforce the configured cap.
                try:
                    rss_kb, group_live, pids = bounded_process.process_group_stats(group_id)
                    peak_rss_kb = max(peak_rss_kb, rss_kb)
                except bounded_process.MonitorError:
                    group_live = True
                if group_live or process.poll() is None:
                    limit_reason = "could not monitor owned process footprint: " + str(error)
                    result["status"] = "monitor_error"
            else:
                footprint_kb = (footprint_bytes + 1023) // 1024
                peak_footprint_kb = max(peak_footprint_kb, footprint_kb)
                last_footprint_sample = time.monotonic()
                if footprint_bytes >= footprint_threshold_bytes:
                    limit_reason = (
                        "aggregate physical footprint %d KiB reached safety threshold %d KiB (configured RSS cap %d KiB)"
                        % (footprint_kb, (footprint_threshold_bytes + 1023) // 1024, max_rss_kb)
                    )
        if limit_reason:
            if result["status"] not in ("monitor_error", "timed_out"):
                result["status"] = "resource_limited"
            process_details = bounded_process.process_group_breakdown(group_id) if os.name == "posix" else "process groups unavailable"
            if os.name == "posix":
                bounded_process.terminate_group(group_id, process)
            else:
                process.kill()
                process.wait()
            break

        return_code = process.poll()
        if return_code is not None and not group_live:
            result["return_code"] = return_code
            if return_code < 0:
                result["status"] = "crashed"
            break

        if now >= deadline and group_live:
            limit_reason = "deadline exceeded (%.3fs)" % timeout_seconds
            result["status"] = "timed_out"
            process_details = bounded_process.process_group_breakdown(group_id) if os.name == "posix" else "process groups unavailable"
            if os.name == "posix":
                bounded_process.terminate_group(group_id, process)
            else:
                process.kill()
                process.wait()
            break

        time.sleep(PROCESS_POLL_SECONDS)

    stdout_stream.close()
    stderr_stream.close()
    result["peak_rss_kb"] = peak_rss_kb
    if footprint_available:
        result["peak_physical_footprint_kb"] = peak_footprint_kb
    if limit_reason:
        result["limit_reason"] = limit_reason
        result["process_group_members_at_limit"] = process_details
        diagnostic = ("\nfixture runner: " + limit_reason + "; owned process group members: " + process_details + "\n").encode("utf-8", "replace")
        with stderr_path.open("ab") as stream:
            stream.write(diagnostic)

    stdout = stdout_path.read_bytes()
    stderr = stderr_path.read_bytes()
    result["return_code"] = process.returncode
    result["duration_seconds"] = round(time.monotonic() - started, 6)
    result["stdout_bytes"] = len(stdout)
    result["stderr_bytes"] = len(stderr)
    return result, stdout, stderr


def stage_failure_outcome(stage_result, stage_name, stderr):
    if stage_result["status"] == "timed_out":
        return "timed_out"
    if stage_result["status"] == "resource_limited":
        return "resource_limited"
    if stage_result["status"] == "crashed":
        return "crashed"
    if stage_result["status"] == "missing_tool":
        return "missing_tool"
    if stage_name == "translate" and stage_result["return_code"] not in (0, None):
        if b"unsupported" in stderr.lower():
            return "unsupported"
    return "failed"


def run_case(case, arguments):
    name = case["name"]
    if case.get("skip_reason"):
        if not case.get("optional", False):
            raise ManifestError("case %s has skip_reason but is not marked optional" % name)
        result = {"name": name, "status": "skipped", "skip_reason": case["skip_reason"], "stages": []}
        atomic_json(arguments.output_dir / name / "result.json", result)
        print("SKIP %s: %s" % (name, result["skip_reason"]))
        return result

    source = (ROOT / case["source"]).resolve()
    if not source.is_file():
        raise ManifestError("case %s source does not exist: %s" % (name, source))
    case_dir = arguments.output_dir / name
    case_dir.mkdir(parents=True, exist_ok=True)
    timeout = arguments.timeout_seconds or case.get("timeout_seconds", arguments.default_timeout_seconds)
    generated = case_dir / "generated.elisa"
    native = case_dir / "native"
    obj = case_dir / "generated.o"
    executable = case_dir / "generated"
    elisa_runtime = getattr(arguments, "elisa_runtime", "")
    values = {
        "source": str(source),
        "case_dir": str(case_dir.resolve()),
        "generated": str(generated.resolve()),
        "native": str(native.resolve()),
        "object": str(obj.resolve()),
        "elisa_executable": str(executable.resolve()),
        "translator": str(arguments.translator),
        "elisa_bin": str(arguments.elisa_compiler),
        "elisa_runtime": str(elisa_runtime or ""),
    }
    stages = []
    checks = []
    result = {"name": name, "source": str(source), "status": "failed", "stages": stages, "checks": checks}

    def execute(stage_name, command_array):
        argv = substitute_argv(command_array, values, name + "." + stage_name)
        stage_result, stdout, stderr = run_command(
            case_dir,
            stage_name,
            argv,
            timeout,
            getattr(arguments, "max_rss_kb", None),
            getattr(arguments, "max_output_bytes", DEFAULT_STAGE_OUTPUT_BYTES),
        )
        stages.append(stage_result)
        return stage_result, stdout, stderr

    def require_success(stage_name, stage_result, stderr, expected=0):
        if stage_result["status"] != "completed" or stage_result["return_code"] != expected:
            result["status"] = stage_failure_outcome(stage_result, stage_name, stderr)
            result["failure"] = {
                "stage": stage_name,
                "expected_return_code": expected,
                "observed_return_code": stage_result["return_code"],
                "stage_status": stage_result["status"],
            }
            return False
        return True

    stage, output, error = execute("translate", case["translate_argv"])
    generated.write_bytes(output)
    if not require_success("translate", stage, error):
        atomic_json(case_dir / "result.json", result)
        return result

    text = output.decode("utf-8", "surrogateescape")
    generated_checks = case.get("generated_checks", {})
    for pattern in generated_checks.get("contains_regex", []):
        matched = re.search(pattern, text, re.MULTILINE) is not None
        checks.append({"kind": "contains_regex", "pattern": pattern, "passed": matched})
    for pattern in generated_checks.get("not_contains_regex", []):
        matched = re.search(pattern, text, re.MULTILINE) is None
        checks.append({"kind": "not_contains_regex", "pattern": pattern, "passed": matched})
    if generated_checks.get("no_trailing_whitespace", False):
        line_number = next(
            (number for number, line in enumerate(text.splitlines(), 1) if line.endswith((" ", "\t"))),
            None,
        )
        checks.append({"kind": "no_trailing_whitespace", "passed": line_number is None, "line": line_number})
    max_empty_lines = generated_checks.get("max_consecutive_empty_lines")
    if max_empty_lines is not None:
        current = maximum = 0
        for line in text.splitlines():
            current = current + 1 if not line.strip() else 0
            maximum = max(maximum, current)
        checks.append({
            "kind": "max_consecutive_empty_lines",
            "maximum_allowed": max_empty_lines,
            "observed": maximum,
            "passed": maximum <= max_empty_lines,
        })
    if any(not check["passed"] for check in checks):
        result["failure"] = {"stage": "generated_source_checks", "checks": [check for check in checks if not check["passed"]]}
        atomic_json(case_dir / "result.json", result)
        return result

    stage, _, error = execute("native_build", case["native_build_argv"])
    if not require_success("native_build", stage, error):
        atomic_json(case_dir / "result.json", result)
        return result
    stage, _, error = execute("elisa_compile", case["elisa_compile_argv"])
    if not require_success("elisa_compile", stage, error):
        atomic_json(case_dir / "result.json", result)
        return result
    elisa_link_argv = list(case["elisa_link_argv"])
    if elisa_runtime and "{elisa_runtime}" not in elisa_link_argv:
        # A self-hosted compiler may lower generated containers through the
        # Elisa arena ABI. Link the explicitly selected matching runtime into
        # generated fixtures; default stage0 runs remain unchanged when no
        # runtime is supplied.
        elisa_link_argv.append("{elisa_runtime}")
    stage, _, error = execute("elisa_link", elisa_link_argv)
    if not require_success("elisa_link", stage, error):
        atomic_json(case_dir / "result.json", result)
        return result

    run_records = {}
    for run_name, command_key in (("native_run", "native_run_argv"), ("elisa_run", "elisa_run_argv")):
        stage, stdout, stderr = execute(run_name, case[command_key])
        run_records[run_name] = (stage, stdout, stderr)
        if not require_success(run_name, stage, stderr, case["expected_exit_code"]):
            atomic_json(case_dir / "result.json", result)
            return result

    compare_fields = case.get("compare", ["stdout", "stderr", "exit_code"])
    native_run = run_records["native_run"]
    elisa_run = run_records["elisa_run"]
    for field in compare_fields:
        if field == "stdout":
            same = native_run[1] == elisa_run[1]
        elif field == "stderr":
            same = native_run[2] == elisa_run[2]
        elif field == "exit_code":
            same = native_run[0]["return_code"] == elisa_run[0]["return_code"]
        else:
            raise ManifestError("case %s has unsupported compare field %s" % (name, field))
        checks.append({"kind": "native_vs_elisa", "field": field, "passed": same})
    if any(not check["passed"] for check in checks):
        result["failure"] = {"stage": "differential_comparison", "checks": [check for check in checks if not check["passed"]]}
        atomic_json(case_dir / "result.json", result)
        return result

    artifacts = []
    for template in case.get("capture_files", []):
        artifact_path = Path(substitute_template(template, values, name + ".capture_files"))
        if not artifact_path.is_absolute():
            artifact_path = (ROOT / artifact_path).resolve()
        if not artifact_path.is_file():
            artifacts.append({"path": str(artifact_path), "exists": False})
            result["failure"] = {"stage": "artifact_capture", "missing": str(artifact_path)}
            atomic_json(case_dir / "result.json", result)
            return result
        artifacts.append({
            "path": str(artifact_path),
            "exists": True,
            "size_bytes": artifact_path.stat().st_size,
            "sha256": sha256_file(artifact_path),
        })
    result["artifacts"] = artifacts
    result["status"] = "passed"
    atomic_json(case_dir / "result.json", result)
    print("PASS %s (exit=%s; %s artifacts)" % (name, case["expected_exit_code"], len(artifacts)))
    return result


def validate_case(case, index):
    if not isinstance(case, dict):
        raise ManifestError("case %d must be an object" % index)
    name = case.get("name")
    if not isinstance(name, str) or not name or Path(name).name != name or "/" in name or "\\" in name or name in (".", ".."):
        raise ManifestError("case %d needs a safe, non-empty name" % index)
    if case.get("skip_reason"):
        if case.get("optional") is not True or not isinstance(case["skip_reason"], str):
            raise ManifestError("skipped case %s must be optional and have a string skip_reason" % name)
        return

    required = (
        "source", "translate_argv", "native_build_argv", "elisa_compile_argv",
        "elisa_link_argv", "native_run_argv", "elisa_run_argv", "expected_exit_code",
    )
    missing = [field for field in required if field not in case]
    if missing:
        raise ManifestError("case %s is missing required fields: %s" % (name, ", ".join(missing)))
    if not isinstance(case["source"], str) or not case["source"]:
        raise ManifestError("case %s source must be a non-empty path" % name)
    for field in required[1:7]:
        command = case[field]
        if not isinstance(command, list) or not command or any(not isinstance(part, str) for part in command):
            raise ManifestError("case %s %s must be a non-empty argv array of strings" % (name, field))
    expected_exit_code = case["expected_exit_code"]
    if isinstance(expected_exit_code, bool) or not isinstance(expected_exit_code, int):
        raise ManifestError("case %s expected_exit_code must be an integer" % name)
    timeout = case.get("timeout_seconds")
    if timeout is not None and (isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0):
        raise ManifestError("case %s timeout_seconds must be a finite positive number" % name)
    compare = case.get("compare", ["stdout", "stderr", "exit_code"])
    if not isinstance(compare, list) or any(field not in ("stdout", "stderr", "exit_code") for field in compare):
        raise ManifestError("case %s compare must contain only stdout, stderr, and exit_code" % name)
    capture_files = case.get("capture_files", [])
    if not isinstance(capture_files, list) or any(not isinstance(path, str) for path in capture_files):
        raise ManifestError("case %s capture_files must be an array of path templates" % name)
    generated_checks = case.get("generated_checks", {})
    if not isinstance(generated_checks, dict):
        raise ManifestError("case %s generated_checks must be an object" % name)
    for field in ("contains_regex", "not_contains_regex"):
        patterns = generated_checks.get(field, [])
        if not isinstance(patterns, list) or any(not isinstance(pattern, str) for pattern in patterns):
            raise ManifestError("case %s generated_checks.%s must be an array of strings" % (name, field))
        for pattern in patterns:
            try:
                re.compile(pattern)
            except re.error as error:
                raise ManifestError("case %s has invalid regex in %s: %s" % (name, field, error))
    max_empty = generated_checks.get("max_consecutive_empty_lines")
    if max_empty is not None and (isinstance(max_empty, bool) or not isinstance(max_empty, int) or max_empty < 0):
        raise ManifestError("case %s max_consecutive_empty_lines must be a non-negative integer" % name)
    if "no_trailing_whitespace" in generated_checks and not isinstance(generated_checks["no_trailing_whitespace"], bool):
        raise ManifestError("case %s no_trailing_whitespace must be a boolean" % name)


def load_manifest(path):
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ManifestError("cannot load manifest %s: %s" % (path, error))
    if not isinstance(manifest, dict):
        raise ManifestError("manifest root must be an object")
    if manifest.get("schema_version") != 1:
        raise ManifestError("unsupported fixture manifest schema_version")
    cases = manifest.get("cases")
    if not isinstance(cases, list):
        raise ManifestError("manifest cases must be an array")
    for index, case in enumerate(cases):
        validate_case(case, index)
    names = [case["name"] for case in cases]
    if len(set(names)) != len(names):
        raise ManifestError("every manifest case needs a unique non-empty name")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--translator", required=True)
    parser.add_argument("--elisa-compiler", required=True)
    parser.add_argument(
        "--elisa-runtime",
        default=os.environ.get("ELISA_RUNTIME_OBJ") or os.environ.get("ELISAC_RUNTIME", ""),
        help="matching Elisa runtime object for generated-program links (or ELISA_RUNTIME_OBJ/ELISAC_RUNTIME)",
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--case", action="append", dest="selected_cases")
    parser.add_argument("--timeout-seconds", type=float, help="override each case deadline")
    parser.add_argument("--default-timeout-seconds", type=float, default=120.0)
    parser.add_argument("--max-rss-kb", type=bounded_process.positive_int, help="per-stage aggregate process-group RSS cap, with macOS physical-footprint monitoring")
    parser.add_argument(
        "--max-output-bytes",
        type=bounded_process.positive_int,
        default=os.environ.get("ELISA_FIXTURE_PROCESS_MAX_OUTPUT_BYTES", str(DEFAULT_STAGE_OUTPUT_BYTES)),
        help="combined stdout/stderr cap per stage (default: 64 MiB; may also use ELISA_FIXTURE_PROCESS_MAX_OUTPUT_BYTES)",
    )
    arguments = parser.parse_args()
    arguments.manifest = arguments.manifest if arguments.manifest.is_absolute() else ROOT / arguments.manifest
    arguments.output_dir = arguments.output_dir if arguments.output_dir.is_absolute() else ROOT / arguments.output_dir
    arguments.translator = str((ROOT / arguments.translator).resolve()) if not Path(arguments.translator).is_absolute() else arguments.translator
    arguments.elisa_compiler = str((ROOT / arguments.elisa_compiler).resolve()) if not Path(arguments.elisa_compiler).is_absolute() else arguments.elisa_compiler
    if arguments.elisa_runtime:
        runtime_path = Path(arguments.elisa_runtime).expanduser()
        if not runtime_path.is_absolute():
            runtime_path = ROOT / runtime_path
        runtime_path = runtime_path.resolve()
        if not runtime_path.is_file():
            print("manifest runner error: missing Elisa runtime object: %s" % runtime_path, file=sys.stderr)
            return 2
        arguments.elisa_runtime = str(runtime_path)

    try:
        manifest = load_manifest(arguments.manifest)
        cases_by_name = {case["name"]: case for case in manifest["cases"]}
        selected = arguments.selected_cases or list(cases_by_name)
        unknown = [name for name in selected if name not in cases_by_name]
        if unknown:
            raise ManifestError("unknown fixture case(s): " + ", ".join(unknown))
        if arguments.timeout_seconds is not None and (not math.isfinite(arguments.timeout_seconds) or arguments.timeout_seconds <= 0):
            raise ManifestError("--timeout-seconds must be finite and positive")
        if arguments.default_timeout_seconds <= 0 or not math.isfinite(arguments.default_timeout_seconds):
            raise ManifestError("--default-timeout-seconds must be finite and positive")
        if arguments.max_rss_kb is not None and os.name != "posix":
            raise ManifestError("--max-rss-kb requires POSIX process groups")
        results = [run_case(cases_by_name[name], arguments) for name in selected]
    except ManifestError as error:
        print("fixture manifest error: %s" % error, file=sys.stderr)
        return 2

    counts = {outcome: 0 for outcome in OUTCOMES}
    missing_tools = 0
    for result in results:
        counts[result["status"]] = counts.get(result["status"], 0) + 1
        missing_tools += sum(1 for stage in result.get("stages", []) if stage["status"] == "missing_tool")
        if result["status"] != "passed" and result["status"] != "skipped":
            failure = result.get("failure", {})
            print(
                "%-11s %s%s" % (
                    result["status"].upper(),
                    result["name"],
                    (" at " + failure.get("stage", "unknown stage")) if failure else "",
                ),
                file=sys.stderr,
            )
    summary = {
        "manifest": str(arguments.manifest),
        "selected_cases": selected,
        "counts": counts,
        "missing_tool_stages": missing_tools,
        "results": results,
    }
    atomic_json(arguments.output_dir / "summary.json", summary)
    print("fixture summary: " + " ".join("%s=%s" % (key, counts[key]) for key in OUTCOMES) + " missing_tools=%d" % missing_tools)
    return 0 if all(counts[key] == 0 for key in ("failed", "timed_out", "crashed", "resource_limited", "monitor_error", "unsupported", "missing_tool")) else 1


if __name__ == "__main__":
    sys.exit(main())
