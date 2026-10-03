#!/usr/bin/env python3
"""Retain external inline definitions reachable through canonical redeclarations."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
FORWARD_HEADER = "static inline int imported_increment(int);\n"
DEFINITION_HEADER = "static inline int imported_increment(int value) { return value + 1; }\n"
PROGRAM = """\
#include \"forward.h\"
#include \"definition.h\"

int main(void)
{
    return imported_increment(41) == 42 ? 0 : 1;
}
"""


def fail(message: str, *outputs: str) -> int:
    print(message, file=sys.stderr)
    for output in outputs:
        if output:
            print(output[:2500], file=sys.stderr)
    return 1


def walk(node: object):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk(value)


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: test_inline_dependency_closure.py TRANSLATOR ELISA_COMPILER [ELISA_RUNTIME]", file=sys.stderr)
        return 2
    translator = Path(sys.argv[1]).expanduser().resolve()
    compiler = Path(sys.argv[2]).expanduser().resolve()
    runtime = Path(sys.argv[3]).expanduser().resolve() if len(sys.argv) > 3 and sys.argv[3] else None
    for label, executable in (("translator", translator), ("Elisa compiler", compiler)):
        if not executable.is_file() or not os.access(executable, os.X_OK):
            print(f"missing {label} executable: {executable}", file=sys.stderr)
            return 2
    if runtime is not None and not runtime.is_file():
        print(f"missing matching Elisa runtime: {runtime}", file=sys.stderr)
        return 2

    clang = shutil.which("clang")
    if clang is None:
        print("clang is required for the inline dependency-closure regression", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory(prefix="elisa-inline-dependency-") as temporary_directory:
        temporary_root = Path(temporary_directory)
        headers = temporary_root / "external-headers"
        headers.mkdir()
        source = temporary_root / "inline_dependency.c"
        forward_header = headers / "forward.h"
        definition_header = headers / "definition.h"
        source.write_text(PROGRAM, encoding="utf-8")
        forward_header.write_text(FORWARD_HEADER, encoding="utf-8")
        definition_header.write_text(DEFINITION_HEADER, encoding="utf-8")

        native = temporary_root / "native"
        native_build = subprocess.run(
            [clang, "-std=c11", "-I", str(headers), str(source), "-o", str(native)],
            cwd=temporary_root,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if native_build.returncode != 0:
            return fail("native Clang rejected the inline dependency fixture", native_build.stderr)

        ast_result = subprocess.run(
            [clang, "-std=c11", "-I", str(headers), "-Xclang", "-ast-dump=json", "-fsyntax-only", str(source)],
            cwd=temporary_root,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if ast_result.returncode != 0:
            return fail("Clang failed to create the inline dependency AST", ast_result.stderr)
        ast = json.loads(ast_result.stdout)
        helper_declarations = [
            node
            for node in ast.get("inner", [])
            if isinstance(node, dict)
            and node.get("kind") == "FunctionDecl"
            and node.get("name") == "imported_increment"
        ]
        prototypes = [
            node
            for node in helper_declarations
            if not any(isinstance(child, dict) and child.get("kind") == "CompoundStmt" for child in node.get("inner", []))
        ]
        definitions = [
            node
            for node in helper_declarations
            if any(isinstance(child, dict) and child.get("kind") == "CompoundStmt" for child in node.get("inner", []))
        ]
        if len(prototypes) != 1 or len(definitions) != 1:
            return fail(f"expected one helper prototype and definition; got {len(prototypes)} and {len(definitions)}")
        prototype_id = prototypes[0].get("id")
        definition_id = definitions[0].get("id")
        if not isinstance(prototype_id, str) or not isinstance(definition_id, str):
            return fail("Clang helper redeclarations lack declaration IDs")
        if definitions[0].get("previousDecl") != prototype_id:
            return fail("Clang no longer links the inline definition to its earlier prototype through previousDecl")

        calls = [
            node
            for node in walk(ast)
            if node.get("kind") == "DeclRefExpr"
            and isinstance(node.get("referencedDecl"), dict)
            and node["referencedDecl"].get("name") == "imported_increment"
        ]
        if len(calls) != 1:
            return fail(f"expected one source call to imported_increment, found {len(calls)}")
        # A DeclRef may legally identify either redeclaration. Pin the reference
        # to the declaration-only ID so this test proves the canonical edge is
        # what recovers the body-bearing redeclaration.
        calls[0]["referencedDecl"]["id"] = prototype_id

        for declaration in helper_declarations:
            location = declaration.setdefault("loc", {})
            location["file"] = f"/synthetic/external/{declaration.get('id')}.h"
            declaration.pop("isUsed", None)
        main_decl = next(
            (
                node
                for node in ast.get("inner", [])
                if isinstance(node, dict)
                and node.get("kind") == "FunctionDecl"
                and node.get("name") == "main"
            ),
            None,
        )
        if not isinstance(main_decl, dict):
            return fail("Clang AST fixture has no source main function")
        main_decl.setdefault("loc", {})["file"] = str(source)

        ast_path = temporary_root / "external-inline-dependency.json"
        ast_path.write_text(json.dumps(ast, separators=(",", ":")), encoding="utf-8")
        environment = os.environ.copy()
        environment["PATH"] = str(ROOT / "testdata/fake_tools") + os.pathsep + environment.get("PATH", "")
        environment["ELISA_FAKE_CLANG_JSON"] = str(ast_path)
        translated = subprocess.run(
            [str(translator), str(source)],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
        if translated.returncode != 0 or not translated.stdout:
            return fail("canonical dependency closure rejected the external inline definition", translated.stderr)
        if "def imported_increment(" not in translated.stdout or "def main(" not in translated.stdout:
            return fail("projected Elisa omitted the source-reachable inline definition", translated.stderr, translated.stdout)

        generated = temporary_root / "inline_dependency.elisa"
        generated.write_text(translated.stdout, encoding="utf-8")
        object_file = temporary_root / "generated.o"
        generated_build = subprocess.run(
            [str(compiler), "-emit", "obj", "-O0", "-o", str(object_file), str(generated)],
            cwd=temporary_root,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if generated_build.returncode != 0:
            return fail("Elisa compiler rejected the canonical-inline-closure translation", generated_build.stderr)
        generated_executable = temporary_root / "generated"
        link_argv = [clang, "-Wl,-dead_strip", "-o", str(generated_executable), str(object_file)]
        if runtime is not None:
            link_argv.append(str(runtime))
        linked = subprocess.run(link_argv, cwd=temporary_root, capture_output=True, text=True, timeout=30, check=False)
        if linked.returncode != 0:
            return fail("generated inline-dependency object did not link", linked.stderr)

        native_run = subprocess.run([str(native)], cwd=temporary_root, capture_output=True, timeout=30, check=False)
        generated_run = subprocess.run([str(generated_executable)], cwd=temporary_root, capture_output=True, timeout=30, check=False)
        if (native_run.returncode, native_run.stdout, native_run.stderr) != (generated_run.returncode, generated_run.stdout, generated_run.stderr):
            return fail(f"native/generated inline dependency behavior differs ({native_run.returncode}/{generated_run.returncode})")
        if native_run.returncode != 0:
            return fail(f"inline dependency fixture returned {native_run.returncode} instead of 0")

    print("canonical inline dependency closure check OK (prototype ID reaches external definition; compile/link/runtime parity)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
