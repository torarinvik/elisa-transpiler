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
SOURCE = "testdata/fixtures/simple.c"


def remove_add_dependency(node: object) -> int:
    if isinstance(node, dict):
        removed = 0
        if node.get("kind") == "DeclRefExpr":
            reference = node.get("referencedDecl")
            if isinstance(reference, dict) and reference.get("name") == "add":
                reference.pop("type", None)
                node.pop("type", None)
                removed += 1
        for value in node.values():
            removed += remove_add_dependency(value)
        return removed
    if isinstance(node, list):
        return sum(remove_add_dependency(value) for value in node)
    return 0


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
    raw_ast = subprocess.run(
        [clang, "-std=c11", "-Xclang", "-ast-dump=json", "-fsyntax-only", SOURCE],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if raw_ast.returncode != 0:
        print("Clang failed to create the fixture AST", file=sys.stderr)
        print(raw_ast.stderr, end="", file=sys.stderr)
        return 1

    ast = json.loads(raw_ast.stdout)
    inner = ast.get("inner")
    if not isinstance(inner, list):
        print("Clang AST fixture has no translation-unit declarations", file=sys.stderr)
        return 1
    original_count = len(inner)
    inner[:] = [
        declaration
        for declaration in inner
        if not (
            isinstance(declaration, dict)
            and declaration.get("kind") == "FunctionDecl"
            and declaration.get("name") == "add"
        )
    ]
    if len(inner) == original_count:
        print("Clang AST fixture no longer contains the add declaration", file=sys.stderr)
        return 1
    reference_count = remove_add_dependency(ast)
    if reference_count != 1:
        print(f"expected one add reference, found {reference_count}", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="elisa-missing-decl-") as temporary_directory:
        temporary_root = Path(temporary_directory)
        ast_path = temporary_root / "missing-declaration.json"
        ast_path.write_text(json.dumps(ast, separators=(",", ":")), encoding="utf-8")
        environment = os.environ.copy()
        environment["PATH"] = str(ROOT / "testdata/fake_tools") + os.pathsep + environment.get("PATH", "")
        environment["ELISA_FAKE_CLANG_JSON"] = str(ast_path)
        result = subprocess.run(
            [str(transpiler), SOURCE],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

    expected = "missing-declaration-dependency:main -> add"
    if (
        result.returncode == 0
        or result.stdout
        or expected not in result.stderr
        or SOURCE not in result.stderr
    ):
        print("lost source declaration was guessed or its direct dependency trail was omitted", file=sys.stderr)
        print(result.stderr, end="", file=sys.stderr)
        if result.stdout:
            print("unexpected partial Elisa output:", file=sys.stderr)
            print(result.stdout[:1200], file=sys.stderr)
        return 1

    print("missing declaration dependency check OK (source-qualified; direct dependency trail; no guessed signature)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
