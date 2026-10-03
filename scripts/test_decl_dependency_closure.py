#!/usr/bin/env python3
"""Keep directly referenced declaration nodes during AST projection."""

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


def walk(node: object):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk(value)


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
        print("clang is required for the declaration-closure regression", file=sys.stderr)
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
    declarations = [
        node
        for node in ast.get("inner", [])
        if isinstance(node, dict)
        and node.get("kind") == "FunctionDecl"
        and node.get("name") == "add"
    ]
    if len(declarations) != 1:
        print(f"expected one add declaration, found {len(declarations)}", file=sys.stderr)
        return 1
    declaration = declarations[0]
    declaration_id = declaration.get("id")
    location = declaration.get("loc")
    children = declaration.get("inner")
    if not isinstance(declaration_id, str) or not isinstance(location, dict) or not isinstance(children, list):
        print("Clang add declaration lacks an id or location", file=sys.stderr)
        return 1
    declaration.pop("isUsed", None)
    location["file"] = "/synthetic/non-project/header.h"
    declaration_position = ast.get("inner", []).index(declaration)
    # Clang omits repeated top-level `loc.file` values. Moving `add` to a
    # synthetic header therefore requires making the following main-file
    # declarations explicit, or the synthetic provenance would correctly
    # carry forward to them as well.
    for sibling in ast["inner"][declaration_position + 1 :]:
        if isinstance(sibling, dict) and isinstance(sibling.get("loc"), dict):
            sibling["loc"].setdefault("file", SOURCE)
    bodies = [child for child in children if isinstance(child, dict) and child.get("kind") == "CompoundStmt"]
    if len(bodies) != 1:
        print(f"expected one add function body, found {len(bodies)}", file=sys.stderr)
        return 1
    children.remove(bodies[0])
    declaration["storageClass"] = "extern"

    references = [
        node
        for node in walk(ast)
        if node.get("kind") == "DeclRefExpr"
        and isinstance(node.get("referencedDecl"), dict)
        and node["referencedDecl"].get("id") == declaration_id
    ]
    if len(references) != 1:
        print(f"expected one add reference, found {len(references)}", file=sys.stderr)
        return 1
    reference = references[0]
    if reference.pop("type", None) is None:
        print("Clang reference no longer has the type metadata this test removes", file=sys.stderr)
        return 1
    reference["referencedDecl"].pop("type", None)

    with tempfile.TemporaryDirectory(prefix="elisa-decl-closure-") as temporary_directory:
        ast_path = Path(temporary_directory) / "referenced-declaration.json"
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

    expected_external = '@link_name("add")'
    if result.returncode != 0 or not result.stdout or expected_external not in result.stdout:
        print("referenced declaration was dropped during AST projection", file=sys.stderr)
        print(result.stderr, end="", file=sys.stderr)
        if result.stdout:
            print("unexpected translated output:", file=sys.stderr)
            print(result.stdout[:1200], file=sys.stderr)
        return 1

    print("declaration dependency closure check OK (id-based; not location/isUsed dependent)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
