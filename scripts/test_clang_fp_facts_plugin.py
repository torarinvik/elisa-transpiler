#!/usr/bin/env python3
"""Build and exercise the optional scoped-FP Clang facts plugin.

This is intentionally opt-in until the plugin's exact Clang compatibility and
incremental memory cost have been measured. On macOS it refuses to start any
compiler process unless system-wide free memory is above 80%, then keeps the
host above 60% while each process runs.

Use --profile-source and repeat --clang-arg=-I... / --clang-arg=-D... to
measure a representative translation unit with its relevant frontend flags.
"""

from __future__ import annotations

import argparse
from contextlib import redirect_stderr
import io
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "testdata" / "fixtures" / "fp_scoped_controls.c"
HEADER = ROOT / "testdata" / "fixtures" / "fp_scoped_controls_header.h"
PLUGIN_SOURCE = ROOT / "tools" / "clang_fp_facts_plugin.cpp"
MAX_RECORDS = 250_000
MAX_PAYLOAD_BYTES = 32 * 1024 * 1024
MAX_FACT_FILE_BYTES = MAX_PAYLOAD_BYTES + 16_384
MAX_RSS_KB = 2_500_000
MIN_FREE_PERCENT = 60
INITIAL_FREE_PERCENT = 80


def small_command(command: list[str]) -> str:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"{command[0]} exited {result.returncode}: "
            f"{result.stderr.strip()[:2000]}"
        )
    return result.stdout.strip()


def source_line(lines: list[str], marker: str, start: int = 0) -> int:
    for index in range(start, len(lines)):
        if marker in lines[index]:
            return index + 1
    raise AssertionError(f"fixture marker is missing: {marker}")


def location_line(record: dict[str, object], field: str = "begin") -> int:
    range_value = record.get("range")
    if not isinstance(range_value, dict):
        return 0
    location = range_value.get(field)
    if not isinstance(location, dict):
        return 0
    line = location.get("line")
    return line if isinstance(line, int) else 0


def run_compiler(
    bounded_run,
    command: list[str],
    label: str,
    *,
    quiet_success_report: bool = False,
) -> tuple[int, int | None]:
    print(f"FP facts integration: {label}", file=sys.stderr)
    telemetry = io.StringIO()
    with redirect_stderr(telemetry):
        result = bounded_run(
            command,
            max_rss_kb=MAX_RSS_KB,
            timeout_seconds=180,
            poll_seconds=0.25,
            min_system_free_percent=MIN_FREE_PERCENT,
            quiet_success_report=quiet_success_report,
            require_initial_system_free_percent=INITIAL_FREE_PERCENT,
        )
    report = telemetry.getvalue()
    if report:
        print(report, end="", file=sys.stderr)
    match = re.search(r"peak process-group RSS (\d+) KiB", report)
    return result, int(match.group(1)) if match else None


def frontend_command(
    clang: Path,
    source: Path,
    plugin_args: list[str],
    clang_args: list[str],
    stderr_path: Path | None = None,
) -> list[str]:
    arguments = [str(clang), "-std=c11", *clang_args, "-Wno-everything", *plugin_args]
    arguments.extend(
        [
            "-Xclang",
            "-fparse-all-comments",
            "-Xclang",
            "-ast-dump=json",
            "-Xclang",
            "-fdump-record-layouts-simple",
            "-fsyntax-only",
            str(source),
        ]
    )
    # Keep the exact Clang argv while discarding its large AST JSON stdout.
    wrapper = (
        "import subprocess,sys; output=open(sys.argv[1],'wb'); "
        "result=subprocess.run(sys.argv[2:], stdout=subprocess.DEVNULL, "
        "stderr=output, check=False); output.close(); raise SystemExit(result.returncode)"
        if stderr_path is not None
        else "import subprocess,sys; raise SystemExit(subprocess.run(sys.argv[1:], stdout=subprocess.DEVNULL, check=False).returncode)"
    )
    prefix = [sys.executable, "-c", wrapper]
    if stderr_path is not None:
        prefix.append(str(stderr_path))
    return [*prefix, *arguments]


def fp_plugin_arguments(plugin: Path, facts_path: Path, *limits: str) -> list[str]:
    result = [
        "-Xclang",
        "-load",
        "-Xclang",
        str(plugin),
        "-Xclang",
        "-add-plugin",
        "-Xclang",
        "elisa-fp-facts",
        "-Xclang",
        "-plugin-arg-elisa-fp-facts",
        "-Xclang",
        "--output",
        "-Xclang",
        "-plugin-arg-elisa-fp-facts",
        "-Xclang",
        str(facts_path),
    ]
    for option, value in zip(limits[::2], limits[1::2], strict=True):
        result.extend(
            [
                "-Xclang",
                "-plugin-arg-elisa-fp-facts",
                "-Xclang",
                option,
                "-Xclang",
                "-plugin-arg-elisa-fp-facts",
                "-Xclang",
                value,
            ]
        )
    return result


def validate_facts(facts_path: Path, clang_version: str) -> None:
    if not facts_path.is_file():
        raise AssertionError("Clang plugin did not create its facts file")
    if facts_path.stat().st_size > MAX_FACT_FILE_BYTES:
        raise AssertionError("Clang facts output exceeded its configured byte budget")
    root = json.loads(facts_path.read_text(encoding="utf-8"))
    if not isinstance(root, dict):
        raise AssertionError("facts root is not a JSON object")
    assert root.get("schema") == "elisa-clang-fp-facts-v1"
    fact_version = root.get("clang_version")
    assert isinstance(fact_version, str)
    fact_version_match = re.search(r"(?:Apple )?clang version ([0-9.]+)", fact_version)
    assert fact_version_match and fact_version_match.group(1) == clang_version
    assert root.get("record_policy") == "effective-options-when-nondefault"
    assert root.get("records_complete") is True
    limits = root.get("limits")
    assert isinstance(limits, dict)
    assert limits.get("max_records") == MAX_RECORDS
    assert limits.get("max_serialized_payload_bytes") == MAX_PAYLOAD_BYTES
    defaults = root.get("default_fp")
    assert isinstance(defaults, dict) and defaults.get("reassociate") is False
    records = root.get("records")
    assert isinstance(records, list) and len(records) <= MAX_RECORDS

    source_path = str(SOURCE.resolve())
    header_path = str(HEADER.resolve())
    fixture_lines = SOURCE.read_text(encoding="utf-8").splitlines()
    header_lines = HEADER.read_text(encoding="utf-8").splitlines()
    reassociate_function = source_line(fixture_lines, "float fp_scoped_reassociate(")
    active_on = source_line(
        fixture_lines,
        "#pragma clang fp reassociate(on)",
        reassociate_function - 1,
    )
    nested_off = source_line(
        fixture_lines,
        "#pragma clang fp reassociate(off)",
        active_on,
    )
    nested_block_end = source_line(fixture_lines, "    }", nested_off)
    restored_operation = source_line(
        fixture_lines, "result = FP_SCOPED_SUM", nested_block_end
    )
    restored_return = source_line(fixture_lines, "return result;", restored_operation)
    inactive_start = source_line(fixture_lines, "#if 0")
    inactive_end = source_line(fixture_lines, "#endif", inactive_start)
    macro_definition = source_line(fixture_lines, "#define FP_SCOPED_SUM")
    precise_function = source_line(fixture_lines, "float fp_scoped_precise(")
    header_pragma = source_line(header_lines, "#pragma clang fp reassociate(on)")

    source_records = [
        record
        for record in records
        if isinstance(record, dict)
        and isinstance(record.get("range"), dict)
        and isinstance(record["range"].get("begin"), dict)
        and record["range"]["begin"].get("file") == source_path
    ]
    header_records = [
        record
        for record in records
        if isinstance(record, dict)
        and isinstance(record.get("range"), dict)
        and isinstance(record["range"].get("begin"), dict)
        and record["range"]["begin"].get("file") == header_path
    ]
    assert header_records, "included-header scoped pragma produced no FP facts"
    assert any(location_line(record) > header_pragma for record in header_records)

    float_control_function = source_line(
        fixture_lines, "float fp_scoped_float_control_fast("
    )
    comparison_function = source_line(
        fixture_lines, "int fp_scoped_float_comparison("
    )
    comparison_expression = source_line(fixture_lines, "return left < right;")
    float_control_records = [
        record
        for record in source_records
        if float_control_function < location_line(record) < precise_function
    ]
    assert float_control_records, "file-scope float_control push produced no FP facts"
    assert all(
        isinstance(record.get("fp"), dict)
        and record["fp"].get("reassociate") is True
        for record in float_control_records
    ), "float_control(pop) facts did not retain the pushed relaxed settings"
    comparison_records = [
        record
        for record in source_records
        if location_line(record) == comparison_expression
        and record.get("kind") == "BinaryOperator"
        and record.get("type") == "int"
    ]
    assert comparison_function < comparison_expression
    assert comparison_records, "FP-valued operands on an integer-result comparison were missed"
    assert all(
        isinstance(record.get("fp"), dict)
        and record["fp"].get("reassociate") is True
        for record in comparison_records
    )

    enabled_records = [
        record
        for record in source_records
        if active_on < location_line(record) < nested_off
    ]
    assert enabled_records, "nested reassociate(on) scope produced no FP facts"
    assert all(
        isinstance(record.get("fp"), dict)
        and record["fp"].get("reassociate") is True
        for record in enabled_records
    )

    assert not any(
        nested_off < location_line(record) < nested_block_end
        for record in source_records
    ), "nested reassociate(off) scope incorrectly inherited the outer setting"
    restored_records = [
        record
        for record in source_records
        if nested_block_end < location_line(record) < restored_return
    ]
    assert restored_records, "outer FP settings were not restored after nested scope exit"
    assert all(
        isinstance(record.get("fp"), dict)
        and record["fp"].get("reassociate") is True
        for record in restored_records
    )
    assert not any(
        precise_function < location_line(record) < active_on
        for record in source_records
    ), "file-scope reassociate(off) control produced non-default FP facts"
    assert not any(
        inactive_start <= location_line(record) <= inactive_end
        for record in source_records
    ), "inactive preprocessor branch produced FP facts"

    macro_records = []
    for record in enabled_records:
        record_range = record.get("range")
        if not isinstance(record_range, dict):
            continue
        spelling = record_range.get("spelling_begin")
        expansion = record_range.get("expansion_begin")
        if (
            isinstance(spelling, dict)
            and isinstance(expansion, dict)
            and spelling.get("file") == source_path
            and expansion.get("file") == source_path
            and spelling.get("line") == macro_definition
            and isinstance(expansion.get("line"), int)
            and expansion["line"] > active_on
        ):
            macro_records.append(record)
    assert macro_records, "macro spelling/expansion provenance was not retained"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile-source",
        type=Path,
        default=SOURCE,
        help="representative C translation unit for baseline/plugin peak-RSS comparison",
    )
    parser.add_argument(
        "--clang-arg",
        action="append",
        default=[],
        help="one additional source compile argument; use --clang-arg=-I/path for dash-prefixed values",
    )
    arguments = parser.parse_args()
    profile_source = arguments.profile_source.expanduser().resolve()
    if not profile_source.is_file():
        print(f"profile source is not a file: {profile_source}", file=sys.stderr)
        return 2

    if platform.system() != "Darwin":
        print(
            "SKIP: this opt-in integration check requires macOS host-memory monitoring",
            file=sys.stderr,
        )
        return 77
    if not all(path.is_file() for path in (SOURCE, HEADER, PLUGIN_SOURCE)):
        print("FP facts integration fixtures or plugin source are missing", file=sys.stderr)
        return 2

    scripts_directory = str(ROOT / "scripts")
    sys.path.insert(0, scripts_directory)
    import run_bounded_process

    try:
        initial_free = run_bounded_process.system_memory_free_percent()
    except run_bounded_process.MonitorError as error:
        print(f"SKIP: cannot verify host memory before build: {error}", file=sys.stderr)
        return 77
    if initial_free <= INITIAL_FREE_PERCENT:
        print(
            "SKIP: compiler integration waits for host free memory above "
            f"{INITIAL_FREE_PERCENT}% (currently {initial_free}%)",
            file=sys.stderr,
        )
        return 77

    llvm_config = os.environ.get("LLVM_CONFIG") or shutil.which("llvm-config")
    if not llvm_config:
        print("llvm-config is required to build the matching Clang plugin", file=sys.stderr)
        return 2
    try:
        llvm_version = small_command([llvm_config, "--version"])
        llvm_bindir = Path(small_command([llvm_config, "--bindir"]))
        llvm_cxxflags = shlex.split(small_command([llvm_config, "--cxxflags"]))
        clangxx = llvm_bindir / "clang++"
        clang = llvm_bindir / "clang"
        if not clangxx.is_file() or not clang.is_file():
            raise RuntimeError(f"matching Clang drivers were not found in {llvm_bindir}")
        clang_output = small_command([str(clang), "--version"])
        clang_match = re.search(r"(?:Apple )?clang version ([0-9.]+)", clang_output)
        if not clang_match or clang_match.group(1) != llvm_version:
            raise RuntimeError(
                f"llvm-config version {llvm_version} does not match Clang driver: "
                f"{clang_output.splitlines()[0] if clang_output else 'unknown'}"
            )
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"FP facts integration setup failed: {error}", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory(prefix="elisa-clang-fp-facts-") as temporary:
        temporary_root = Path(temporary)
        plugin_suffix = ".dylib" if platform.system() == "Darwin" else ".so"
        plugin = temporary_root / ("elisa_fp_facts" + plugin_suffix)
        facts_path = temporary_root / "facts.json"
        compile_command = [
            str(clangxx),
            *llvm_cxxflags,
            "-fPIC",
            "-bundle",
            "-undefined",
            "dynamic_lookup",
            str(PLUGIN_SOURCE),
            "-o",
            str(plugin),
        ]
        build_status, _ = run_compiler(
            run_bounded_process.run,
            compile_command,
            "building plugin against LLVM/Clang " + llvm_version,
            quiet_success_report=True,
        )
        if build_status != 0:
            return build_status

        if profile_source == SOURCE.resolve():
            baseline_status, baseline_rss = run_compiler(
                run_bounded_process.run,
                frontend_command(clang, profile_source, [], arguments.clang_arg),
                "measuring baseline JSON-AST frontend RSS with Clang " + llvm_version,
            )
            if baseline_status != 0:
                return baseline_status
            plugin_status, plugin_rss = run_compiler(
                run_bounded_process.run,
                frontend_command(
                    clang,
                    profile_source,
                    fp_plugin_arguments(plugin, facts_path),
                    arguments.clang_arg,
                ),
                "measuring plugin JSON-AST frontend RSS with Clang " + llvm_version,
            )
            if plugin_status != 0:
                return plugin_status
            try:
                validate_facts(facts_path, llvm_version)
            except (AssertionError, OSError, json.JSONDecodeError) as error:
                print(f"FP facts integration assertion failed: {error}", file=sys.stderr)
                return 1
        else:
            fixture_status, _ = run_compiler(
                run_bounded_process.run,
                frontend_command(
                    clang,
                    SOURCE,
                    fp_plugin_arguments(plugin, facts_path),
                    [],
                ),
                "validating generic scoped-controls fixture with Clang " + llvm_version,
            )
            if fixture_status != 0:
                return fixture_status
            try:
                validate_facts(facts_path, llvm_version)
            except (AssertionError, OSError, json.JSONDecodeError) as error:
                print(f"FP facts integration assertion failed: {error}", file=sys.stderr)
                return 1
            baseline_status, baseline_rss = run_compiler(
                run_bounded_process.run,
                frontend_command(clang, profile_source, [], arguments.clang_arg),
                "measuring baseline profile-source RSS with Clang " + llvm_version,
            )
            if baseline_status != 0:
                return baseline_status
            profile_facts = temporary_root / "profile-facts.json"
            plugin_status, plugin_rss = run_compiler(
                run_bounded_process.run,
                frontend_command(
                    clang,
                    profile_source,
                    fp_plugin_arguments(plugin, profile_facts),
                    arguments.clang_arg,
                ),
                "measuring plugin profile-source RSS with Clang " + llvm_version,
            )
            if plugin_status != 0:
                return plugin_status
            if not profile_facts.is_file() or profile_facts.stat().st_size > MAX_FACT_FILE_BYTES:
                print("FP facts profile output is missing or over budget", file=sys.stderr)
                return 1
        if baseline_rss is None or plugin_rss is None:
            print("FP facts integration did not receive both RSS measurements", file=sys.stderr)
            return 1
        print(
            "Clang FP facts incremental peak process-group RSS: "
            f"{plugin_rss - baseline_rss} KiB "
            f"(baseline {baseline_rss} KiB; plugin {plugin_rss} KiB; "
            f"source {profile_source})",
            file=sys.stderr,
        )

        capped_facts = temporary_root / "capped-facts.json"
        capped_diagnostics = temporary_root / "capped-diagnostics.txt"
        capped_status, _ = run_compiler(
            run_bounded_process.run,
            frontend_command(
                clang,
                SOURCE,
                fp_plugin_arguments(
                    plugin,
                    capped_facts,
                    "--max-records",
                    "1",
                ),
                [],
                capped_diagnostics,
            ),
            "verifying fail-closed record-count budget",
            quiet_success_report=True,
        )
        if capped_status != 1 or capped_facts.exists():
            print("FP facts record-count cap did not fail closed", file=sys.stderr)
            return 1
        if not capped_diagnostics.is_file() or (
            "exceeded the configured record-count limit"
            not in capped_diagnostics.read_text(encoding="utf-8", errors="replace")
        ):
            print("FP facts record-count cap emitted the wrong diagnostic", file=sys.stderr)
            return 1

        byte_capped_facts = temporary_root / "byte-capped-facts.json"
        byte_capped_diagnostics = temporary_root / "byte-capped-diagnostics.txt"
        byte_capped_status, _ = run_compiler(
            run_bounded_process.run,
            frontend_command(
                clang,
                SOURCE,
                fp_plugin_arguments(
                    plugin,
                    byte_capped_facts,
                    "--max-output-bytes",
                    "1",
                ),
                [],
                byte_capped_diagnostics,
            ),
            "verifying fail-closed serialized-payload budget",
            quiet_success_report=True,
        )
        if byte_capped_status != 1 or byte_capped_facts.exists():
            print("FP facts serialized-payload cap did not fail closed", file=sys.stderr)
            return 1
        if not byte_capped_diagnostics.is_file() or (
            "exceeded the configured serialized-payload-bytes limit"
            not in byte_capped_diagnostics.read_text(encoding="utf-8", errors="replace")
        ):
            print("FP facts serialized-payload cap emitted the wrong diagnostic", file=sys.stderr)
            return 1

    print("Clang FP facts plugin fixture passed", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
