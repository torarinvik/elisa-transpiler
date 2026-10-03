#!/usr/bin/env python3
"""Exercise the raw-Clang-JSON nesting boundary without a large fixture."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile


JSON_MAX_DEPTH = 256
SOURCE = "testdata/fixtures/simple.c"


def generated_ast(nested_arrays: int) -> str:
    # Include the TranslationUnitDecl object in the total nesting depth.
    filler = "[" * nested_arrays + "0" + "]" * nested_arrays
    return (
        '{"kind":"TranslationUnitDecl","inner":[],"depthProbe":'
        + filler
        + "}"
    )


def run_case(transpiler: Path, fake_clang: Path, ast_path: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PATH"] = str(fake_clang) + os.pathsep + environment.get("PATH", "")
    environment["ELISA_FAKE_CLANG_JSON"] = str(ast_path)
    return subprocess.run(
        [str(transpiler), SOURCE],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


ROOT = Path(__file__).resolve().parents[1]


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

    fake_clang = ROOT / "testdata/fake_tools"
    with tempfile.TemporaryDirectory(prefix="elisa-ast-depth-") as temporary_directory:
        temporary_root = Path(temporary_directory)
        at_limit_path = temporary_root / "at-limit.json"
        over_limit_path = temporary_root / "over-limit.json"
        at_limit_path.write_text(generated_ast(JSON_MAX_DEPTH - 1), encoding="utf-8")
        over_limit_path.write_text(generated_ast(JSON_MAX_DEPTH), encoding="utf-8")

        at_limit = run_case(transpiler, fake_clang, at_limit_path)
        if at_limit.returncode != 0:
            print("AST at JSON_MAX_DEPTH was rejected", file=sys.stderr)
            print(at_limit.stderr, end="", file=sys.stderr)
            return 1

        over_limit = run_case(transpiler, fake_clang, over_limit_path)
        expected_diagnostic = (
            "Clang emitted invalid or over-depth AST JSON while processing " + SOURCE
        )
        if (
            over_limit.returncode == 0
            or over_limit.stdout
            or expected_diagnostic not in over_limit.stderr
        ):
            print("over-depth AST was not rejected without partial output", file=sys.stderr)
            print(over_limit.stderr, end="", file=sys.stderr)
            return 1

    print(f"AST depth checks OK (depth {JSON_MAX_DEPTH} accepted; {JSON_MAX_DEPTH + 1} rejected)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
