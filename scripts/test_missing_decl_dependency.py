#!/usr/bin/env python3
"""Reject a source-local call whose declaration dependency was lost."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CASES = (
    ("testdata/fixtures/simple.c", "add", "main -> add", "add"),
    (
        "testdata/fixtures/missing_dependency_chain.c",
        "leaf",
        "main -> middle -> leaf",
        "leaf",
    ),
)


def remove_dependency(node: object, missing_name: str) -> int:
    if isinstance(node, dict):
        removed = 0
        if node.get("kind") == "DeclRefExpr":
            reference = node.get("referencedDecl")
            if isinstance(reference, dict) and reference.get("name") == missing_name:
                reference.pop("type", None)
                node.pop("type", None)
                removed += 1
        for value in node.values():
            removed += remove_dependency(value, missing_name)
        return removed
    if isinstance(node, list):
        return sum(remove_dependency(value, missing_name) for value in node)
    return 0


def check_case(
    transpiler: Path,
    clang: str,
    source_name: str,
    missing_name: str,
    trail: str,
    expected_range: str,
) -> bool:
    source = str(ROOT / source_name)
    raw_ast = subprocess.run(
        [clang, "-std=c11", "-Xclang", "-ast-dump=json", "-fsyntax-only", source],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if raw_ast.returncode != 0:
        print(f"Clang failed to create the AST for {source_name}", file=sys.stderr)
        print(raw_ast.stderr, end="", file=sys.stderr)
        return False

    ast = json.loads(raw_ast.stdout)
    inner = ast.get("inner")
    if not isinstance(inner, list):
        print(f"Clang AST for {source_name} has no translation-unit declarations", file=sys.stderr)
        return False
    original_count = len(inner)
    inner[:] = [
        declaration
        for declaration in inner
        if not (
            isinstance(declaration, dict)
            and declaration.get("kind") == "FunctionDecl"
            and declaration.get("name") == missing_name
        )
    ]
    if len(inner) == original_count:
        print(f"Clang AST for {source_name} has no {missing_name} declaration", file=sys.stderr)
        return False
    reference_count = remove_dependency(ast, missing_name)
    if reference_count != 1:
        print(f"expected one {missing_name} reference, found {reference_count}", file=sys.stderr)
        return False

    with tempfile.TemporaryDirectory(prefix="elisa-missing-decl-") as temporary_directory:
        ast_path = Path(temporary_directory) / "missing-declaration.json"
        ast_path.write_text(json.dumps(ast, separators=(",", ":")), encoding="utf-8")
        environment = os.environ.copy()
        environment["PATH"] = str(ROOT / "testdata/fake_tools") + os.pathsep + environment.get("PATH", "")
        environment["ELISA_FAKE_CLANG_JSON"] = str(ast_path)
        result = subprocess.run(
            [str(transpiler), "--diagnostics-json", source],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

    expected = f"missing-declaration-dependency:{trail}"
    if result.returncode == 0 or result.stdout:
        print(f"lost {missing_name} declaration did not report its dependency trail", file=sys.stderr)
        print(result.stderr, end="", file=sys.stderr)
        if result.stdout:
            print("unexpected partial Elisa output:", file=sys.stderr)
            print(result.stdout[:1200], file=sys.stderr)
        return False
    try:
        diagnostics = json.loads(result.stderr)
    except json.JSONDecodeError:
        print("missing-declaration output was not valid diagnostic JSON", file=sys.stderr)
        print(result.stderr, end="", file=sys.stderr)
        return False
    issues = [item for item in diagnostics if item.get("kind") == expected]
    if len(issues) != 1:
        print(f"expected one source-qualified diagnostic for {expected}", file=sys.stderr)
        print(result.stderr, end="", file=sys.stderr)
        return False
    issue = issues[0]
    source_bytes = Path(source).read_bytes()
    start, end = issue["range_start_offset"], issue["range_end_offset"]
    if (
        issue["canonical_source"] != str(Path(source).resolve())
        or issue["translation_unit"] != str(Path(source).resolve())
        or start < 0
        or end < start
        or source_bytes[start:end] != expected_range.encode()
    ):
        print(f"missing-declaration diagnostic lost its precise source origin: {issue}", file=sys.stderr)
        return False
    print(f"missing declaration trail check OK: {trail}")
    return True


def main() -> int:
    configured_transpiler = (
        sys.argv[1]
        if len(sys.argv) > 1
        else os.environ.get("ELISA_TRANSLATOR_BIN", str(ROOT / "build/elisa-c-transpiler"))
    )
    transpiler = Path(configured_transpiler).expanduser()
    if not transpiler.is_absolute():
        transpiler = ROOT / transpiler
    transpiler = transpiler.resolve()
    if not transpiler.is_file() or not os.access(transpiler, os.X_OK):
        print(f"missing translator executable: {transpiler}", file=sys.stderr)
        return 2

    clang = shutil.which("clang")
    if clang is None:
        print("clang is required for the missing-declaration regression", file=sys.stderr)
        return 2
    for source_name, missing_name, trail, expected_range in CASES:
        if not check_case(transpiler, clang, source_name, missing_name, trail, expected_range):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
