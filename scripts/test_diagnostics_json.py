#!/usr/bin/env python3
"""Verify source-qualified diagnostics and exact half-open source ranges."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path


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
        "range_start_offset",
        "range_end_offset",
        "source",
        "canonical_source",
        "line",
        "column",
    }
    assert all(isinstance(item, dict) and required <= item.keys() for item in diagnostics)
    assert {item["schema_version"] for item in diagnostics} == {3}
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
    start, end = conditional["range_start_offset"], conditional["range_end_offset"]
    assert 0 <= start < end <= len(source)
    assert source[start:end] == b"gate ? (touch(), left) : right"
    line_start = source.rfind(b"\n", 0, start) + 1
    assert conditional["line"] == source[:start].count(b"\n") + 1
    assert conditional["column"] == start - line_start + 1

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
    print("diagnostics JSON checks passed")


if __name__ == "__main__":
    main()
