#!/usr/bin/env python3
"""Verify source-qualified diagnostics and exact half-open source ranges."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path


def fnv1a64_hex(data: bytes) -> str:
    value = 0xCBF29CE484222325
    for byte in data:
        value = ((value ^ byte) * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return f"{value:016x}"


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    translator = Path(
        os.environ.get("ELISA_TRANSLATOR_BIN", root / "build" / "elisa-c-transpiler")
    ).resolve()
    if not translator.is_file():
        raise SystemExit(f"translator executable not found: {translator}")

    source_path = (root / "testdata" / "fixtures" / "conditional_comma_unsupported.c").resolve()
    source = source_path.read_bytes()
    command = [str(translator), "--diagnostics-json", str(source_path)]
    result = subprocess.run(command, cwd=root, capture_output=True, check=False)
    assert result.returncode == 1, (result.returncode, result.stderr.decode(errors="replace"))
    assert not result.stdout, "failed translation must not emit partial Elisa"

    diagnostics = json.loads(result.stderr)
    assert isinstance(diagnostics, list) and diagnostics
    required = {
        "schema_version",
        "category",
        "kind",
        "subject_type",
        "required_capability",
        "translation_unit",
        "translation_unit_content_hash",
        "range_start_offset",
        "range_end_offset",
        "source",
        "canonical_source",
        "source_content_hash",
        "spelling_source_content_hash",
        "spelling_included_from_content_hash",
        "expansion_source_content_hash",
        "expansion_included_from_content_hash",
        "line",
        "column",
    }
    assert all(isinstance(item, dict) and required <= item.keys() for item in diagnostics)
    assert {item["schema_version"] for item in diagnostics} == {5}
    hash_fields = (
        "translation_unit_content_hash",
        "source_content_hash",
        "spelling_source_content_hash",
        "spelling_included_from_content_hash",
        "expansion_source_content_hash",
        "expansion_included_from_content_hash",
    )
    assert all(
        item[field] is None or re.fullmatch(r"[0-9a-f]{16}", item[field])
        for item in diagnostics
        for field in hash_fields
    )
    assert all(item["line"] >= 0 and item["column"] >= 0 for item in diagnostics)
    assert all(item["line"] == 0 or item["column"] >= 1 for item in diagnostics)
    assert all(item["range_start_offset"] >= -1 for item in diagnostics)
    assert all(item["range_end_offset"] >= -1 for item in diagnostics)
    assert all(
        item["range_start_offset"] < 0
        or item["range_start_offset"] <= item["range_end_offset"] <= len(source)
        for item in diagnostics
    )

    conditional = next(
        item
        for item in diagnostics
        if item["category"] == "expression"
        and item["required_capability"] == "comma effects in record-valued conditional"
    )
    assert conditional["subject_type"] == "struct Payload"
    assert conditional["source"] == str(source_path)
    assert conditional["canonical_source"] == str(source_path)
    assert conditional["translation_unit"] == str(source_path)
    expected_source_hash = fnv1a64_hex(source)
    assert conditional["source_content_hash"] == expected_source_hash
    assert conditional["translation_unit_content_hash"] == expected_source_hash
    start, end = conditional["range_start_offset"], conditional["range_end_offset"]
    assert 0 <= start < end <= len(source)
    assert source[start:end] == b"gate ? (touch(), left) : right"
    line_start = source.rfind(b"\n", 0, start) + 1
    assert conditional["line"] == source[:start].count(b"\n") + 1
    assert conditional["column"] == start - line_start + 1

    schema_fixture = root / "testdata" / "fixtures" / "ast_schema_wrong_kind_utf8.json"
    fake_clang_env = os.environ.copy()
    fake_clang_env["ELISA_FAKE_CLANG_JSON"] = str(schema_fixture)
    fake_clang_env["PATH"] = f"{root / 'testdata' / 'fake_tools'}:{fake_clang_env['PATH']}"
    schema_result = subprocess.run(
        [str(translator), "--diagnostics-json", str(source_path)],
        cwd=root,
        env=fake_clang_env,
        capture_output=True,
        check=False,
    )
    assert schema_result.returncode == 1
    assert not schema_result.stdout
    schema_diagnostics = json.loads(schema_result.stderr)
    schema_diagnostic = next(
        item for item in schema_diagnostics if item["category"] == "AST schema"
    )
    assert schema_diagnostic["source_content_hash"] == expected_source_hash
    assert schema_diagnostic["translation_unit_content_hash"] == expected_source_hash
    assert schema_diagnostic["spelling_source_content_hash"] is None
    assert schema_diagnostic["expansion_source_content_hash"] is None

    fake_clang_env["ELISA_FAKE_CLANG_JSON"] = str(
        root / "testdata" / "fixtures" / "malformed_dropped_clang_ast_field.json"
    )
    invalid_json_result = subprocess.run(
        [str(translator), "--diagnostics-json", str(source_path)],
        cwd=root,
        env=fake_clang_env,
        capture_output=True,
        check=False,
    )
    assert invalid_json_result.returncode == 1
    assert not invalid_json_result.stdout
    invalid_json_diagnostic = json.loads(invalid_json_result.stderr)[0]
    assert invalid_json_diagnostic["kind"] == "invalid-json"
    assert invalid_json_diagnostic["source_content_hash"] == expected_source_hash
    assert invalid_json_diagnostic["translation_unit_content_hash"] == expected_source_hash

    macro_source = root / "testdata" / "fixtures" / "macro_origin_header.c"
    macro_header = root / "testdata" / "fixtures" / "macro_origin.h"
    macro_result = subprocess.run(
        [str(translator), "--diagnostics-json", str(macro_source)],
        cwd=root,
        capture_output=True,
        check=False,
    )
    assert macro_result.returncode == 1
    assert not macro_result.stdout
    macro_diagnostics = json.loads(macro_result.stderr)
    macro_origin_diagnostics = [
        item for item in macro_diagnostics if item["kind"] == "AddrLabelExpr"
    ]
    assert len(macro_origin_diagnostics) >= 2, macro_origin_diagnostics
    assert all(
        item["spelling_source_content_hash"] == fnv1a64_hex(macro_header.read_bytes())
        and item["expansion_source_content_hash"] == fnv1a64_hex(macro_source.read_bytes())
        and item["translation_unit_content_hash"] == fnv1a64_hex(macro_source.read_bytes())
        for item in macro_origin_diagnostics
    )

    macro_dump_result = subprocess.run(
        [str(translator), "--dump-typed-ir", str(macro_source)],
        cwd=root,
        capture_output=True,
        check=False,
    )
    assert macro_dump_result.returncode == 1
    assert not macro_dump_result.stdout
    typed_ir_dump = macro_dump_result.stderr.decode(errors="replace")
    assert typed_ir_dump.startswith("typed-ir-v16\n")
    diagnostic_lines = [
        line for line in typed_ir_dump.splitlines() if line.startswith("diagnostic ")
    ]
    assert diagnostic_lines
    expected_tu_hash = fnv1a64_hex(macro_source.read_bytes())
    expected_header_hash = fnv1a64_hex(macro_header.read_bytes())
    assert any(
        f"translation_unit_content_hash={expected_tu_hash}" in line
        and f"source_content_hash={expected_tu_hash}" in line
        and f"spelling_source_content_hash={expected_header_hash}" in line
        for line in diagnostic_lines
    )

    # Clang accepts both LF and CRLF translation units. The byte-offset
    # fallback must count CRLF as one physical line break, including when the
    # retained offset is measured in the original CRLF byte stream.
    with tempfile.TemporaryDirectory(prefix="elisa-diagnostics-crlf-") as temp_dir:
        crlf_path = Path(temp_dir) / source_path.name
        crlf_source = source.replace(b"\n", b"\r\n")
        crlf_path.write_bytes(crlf_source)
        crlf_result = subprocess.run(
            [str(translator), "--diagnostics-json", str(crlf_path)],
            cwd=root,
            capture_output=True,
            check=False,
        )
        assert crlf_result.returncode == 1
        assert not crlf_result.stdout
        crlf_diagnostics = json.loads(crlf_result.stderr)
        crlf_conditional = next(
            item
            for item in crlf_diagnostics
            if item["category"] == "expression"
            and item["required_capability"] == "comma effects in record-valued conditional"
        )
        crlf_start = crlf_conditional["range_start_offset"]
        crlf_end = crlf_conditional["range_end_offset"]
        crlf_line_start = crlf_source.rfind(b"\n", 0, crlf_start) + 1
        assert crlf_source[crlf_start:crlf_end] == b"gate ? (touch(), left) : right"
        assert crlf_conditional["line"] == crlf_source[:crlf_start].count(b"\n") + 1
        assert crlf_conditional["column"] == crlf_start - crlf_line_start + 1

    human = subprocess.run(
        [str(translator), str(source_path)], cwd=root, capture_output=True, check=False
    )
    assert human.returncode == 1
    assert not human.stdout
    assert b"[type: struct Payload]" in human.stderr
    assert b"[missing translator capability: comma effects in record-valued conditional]" in human.stderr

    # A header-origin diagnostic is emitted once for each owning translation
    # unit. Project aggregation must not collapse the two rows just because
    # their source range and semantic issue are otherwise identical.
    with tempfile.TemporaryDirectory(prefix="elisa-diagnostics-project-") as temp_dir:
        project_root = Path(temp_dir)
        shared_header = project_root / "shared_unsupported.h"
        first_source = project_root / "first.c"
        second_source = project_root / "second.c"
        output_dir = project_root / "translated"
        shared_header.write_text(
            "static int touch(void) { return 0; }\n"
            "struct Payload { int value; };\n"
            "static struct Payload unsupported_payload(int gate) {\n"
            "    struct Payload left = {1};\n"
            "    struct Payload right = {2};\n"
            "    struct Payload selected = gate ? (touch(), left) : right;\n"
            "    return selected;\n"
            "}\n"
        )
        first_source.write_text(
            '#include "shared_unsupported.h"\n'
            "int first(void) { return unsupported_payload(1).value; }\n"
        )
        second_source.write_text(
            '#include "shared_unsupported.h"\n'
            "int second(void) { return unsupported_payload(0).value; }\n"
        )
        project_result = subprocess.run(
            [
                str(translator),
                "--diagnostics-json",
                "--output-dir",
                str(output_dir),
                str(first_source),
                str(second_source),
            ],
            cwd=root,
            capture_output=True,
            check=False,
        )
        assert project_result.returncode == 1, (
            project_result.returncode,
            project_result.stderr.decode(errors="replace"),
        )
        assert not project_result.stdout
        project_diagnostics = json.loads(project_result.stderr)
        repeated_header_issues = [
            item
            for item in project_diagnostics
            if item["required_capability"]
            == "comma effects in record-valued conditional"
            and item["canonical_source"] == str(shared_header.resolve())
        ]
        assert len(repeated_header_issues) == 2, repeated_header_issues
        assert {
            item["translation_unit"] for item in repeated_header_issues
        } == {str(first_source.resolve()), str(second_source.resolve())}
        assert {
            item["source_content_hash"] for item in repeated_header_issues
        } == {fnv1a64_hex(shared_header.read_bytes())}
        expected_translation_hashes = {
            str(first_source.resolve()): fnv1a64_hex(first_source.read_bytes()),
            str(second_source.resolve()): fnv1a64_hex(second_source.read_bytes()),
        }
        assert {
            item["translation_unit"]: item["translation_unit_content_hash"]
            for item in repeated_header_issues
        } == expected_translation_hashes
        assert {item["line"] for item in repeated_header_issues} == {6}
        assert all(
            shared_header.read_bytes()[item["range_start_offset"]:item["range_end_offset"]]
            == b"gate ? (touch(), left) : right"
            for item in repeated_header_issues
        )
        assert not (output_dir / "elisa_project.elisa").exists(), (
            "failed project diagnostics must not publish the project manifest"
        )

    print("diagnostics JSON checks passed")


if __name__ == "__main__":
    main()
