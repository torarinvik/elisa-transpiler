#!/usr/bin/env python3
"""Resolve unqualified C++ by-value field layouts conservatively."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def fail(message: str, *outputs: str) -> int:
    print(message, file=sys.stderr)
    for output in outputs:
        if output:
            print(output[:2000], file=sys.stderr)
    return 1


def ast_nodes(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from ast_nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from ast_nodes(child)


def relocate(node: dict, path: str) -> None:
    location = node.setdefault("loc", {})
    if isinstance(location, dict):
        location["file"] = path
        location.pop("includedFrom", None)


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: test_unqualified_cpp_layout.py TRANSLATOR [ELISA_COMPILER]", file=sys.stderr)
        return 2
    translator = Path(sys.argv[1]).expanduser()
    if not translator.is_absolute():
        translator = ROOT / translator
    translator = translator.resolve()
    if not translator.is_file() or not os.access(translator, os.X_OK):
        print(f"missing translator executable: {translator}", file=sys.stderr)
        return 2

    compiler_value = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("ELISA_COMPILER_BIN", "")
    compiler = Path(compiler_value).expanduser() if compiler_value else None
    if compiler is not None and not compiler.is_absolute():
        compiler = ROOT / compiler
    if compiler is not None and (not compiler.is_file() or not os.access(compiler, os.X_OK)):
        print(f"missing Elisa compiler executable: {compiler}", file=sys.stderr)
        return 2

    clang = shutil.which("clang")
    if clang is None:
        print("clang is required for the unqualified C++ layout regression", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory(prefix="elisa-unqualified-cpp-layout-") as temporary_directory:
        temporary_root = Path(temporary_directory)
        header_directory = temporary_root / "headers"
        header_directory.mkdir()
        header = header_directory / "model.hpp"
        header.write_text("struct Layout { int value; };\nstruct Owner { Layout payload; };\n", encoding="utf-8")
        source = temporary_root / "unqualified_layout.cpp"
        source.write_text(
            '#include "model.hpp"\n'
            "int main() { struct Owner owner; if (sizeof(owner) != sizeof(int)) return 1; return 0; }\n",
            encoding="utf-8",
        )
        raw_ast = subprocess.run(
            [clang, "-x", "c++", "-std=c++17", "-I", str(header_directory), "-Xclang", "-fdump-record-layouts-simple", "-Xclang", "-ast-dump=json", "-fsyntax-only", str(source)],
            cwd=temporary_root,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if raw_ast.returncode != 0:
            return fail("Clang failed to create the unqualified C++ record-layout AST", raw_ast.stderr)
        json_start = raw_ast.stdout.find("{")
        if json_start < 0:
            return fail("Clang emitted no JSON AST after its record-layout dump", raw_ast.stdout)
        layout_dump = raw_ast.stdout[:json_start]
        ast = json.loads(raw_ast.stdout[json_start:])
        owner = next(
            (
                node
                for node in ast_nodes(ast)
                if node.get("kind") == "CXXRecordDecl"
                and node.get("name") == "Owner"
                and node.get("completeDefinition") is True
                and not node.get("isImplicit")
            ),
            None,
        )
        field = next(
            (
                node
                for node in owner.get("inner", [])
                if isinstance(node, dict) and node.get("kind") == "FieldDecl" and node.get("name") == "payload"
            ),
            None,
        ) if isinstance(owner, dict) else None
        field_type = field.get("type") if isinstance(field, dict) else None
        if not isinstance(field_type, dict) or field_type.get("qualType") != "Layout":
            return fail("Clang C++ AST fixture changed: expected Owner.payload to spell Layout")
        if any(key in field_type for key in ("decl", "typeAliasDeclId", "ownedTagDecl")):
            return fail("Clang C++ AST fixture now exposes an explicit declaration edge for the class field")
        if not any(
            node.get("kind") == "CXXRecordDecl" and node.get("name") == "Layout" and node.get("isImplicit") is True
            for node in ast_nodes(ast)
        ):
            return fail("Clang C++ AST fixture no longer covers an implicit injected-class-name declaration")

        for node in ast_nodes(ast):
            if node.get("kind") == "CXXRecordDecl" and node.get("name") in {"Layout", "Owner"} and not node.get("isImplicit"):
                relocate(node, f"/synthetic/cpp-header/{node['name']}.hpp")

        ast_path = temporary_root / "unqualified-cpp-layout.json"
        ast_path.write_text(layout_dump + json.dumps(ast, separators=(",", ":")), encoding="utf-8")
        environment = os.environ.copy()
        fake_tool_directory = temporary_root / "fake_tools"
        fake_tool_directory.mkdir()
        os.symlink(ROOT / "testdata/fake_tools/clang", fake_tool_directory / "clang++")
        environment["PATH"] = os.pathsep.join(
            (str(fake_tool_directory), str(ROOT / "testdata/fake_tools"), environment.get("PATH", ""))
        )
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
            return fail("translator rejected a C++ AST with an unqualified by-value record type", translated.stderr)
        layout_emitted = "struct Layout:\n    value: i32" in translated.stdout or "struct Layout:\n    value: mutable i32" in translated.stdout
        if "struct Owner:\n    payload: Layout" not in translated.stdout or not layout_emitted:
            return fail("unqualified C++ by-value field failed to retain its complete layout", translated.stderr, translated.stdout)

        ambiguous_ast = json.loads(json.dumps(ast))
        declarations = ambiguous_ast.get("inner")
        if not isinstance(declarations, list):
            return fail("Clang C++ AST fixture lost its top-level declarations for ambiguity coverage")
        declarations.append(
            {
                "id": "0xC2200000",
                "kind": "CXXRecordDecl",
                "name": "Layout",
                "tagUsed": "struct",
                "completeDefinition": True,
                "loc": {"file": "/synthetic/other-cpp-scope/Layout.hpp"},
                "inner": [
                    {
                        "id": "0xC2200001",
                        "kind": "FieldDecl",
                        "name": "unrelated_value",
                        "type": {"qualType": "long"},
                    }
                ],
            }
        )
        ambiguous_path = temporary_root / "ambiguous-unqualified-cpp-layout.json"
        ambiguous_path.write_text(layout_dump + json.dumps(ambiguous_ast, separators=(",", ":")), encoding="utf-8")
        ambiguous_environment = environment.copy()
        ambiguous_environment["ELISA_FAKE_CLANG_JSON"] = str(ambiguous_path)
        ambiguous = subprocess.run(
            [str(translator), str(source)],
            cwd=ROOT,
            env=ambiguous_environment,
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
        if ambiguous.returncode != 0 or not ambiguous.stdout:
            return fail("translator rejected an ambiguous unqualified C++ record type", ambiguous.stderr)
        ambiguous_layout_emitted = "struct Layout:\n    value: i32" in ambiguous.stdout or "struct Layout:\n    value: mutable i32" in ambiguous.stdout
        if ambiguous_layout_emitted or "unrelated_value" in ambiguous.stdout:
            return fail("ambiguous C++ class spelling selected a layout by name alone", ambiguous.stderr, ambiguous.stdout)

        native = subprocess.run(
            [clang, "-x", "c++", "-std=c++17", "-I", str(header_directory), str(source), "-o", str(temporary_root / "native")],
            cwd=temporary_root,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if native.returncode != 0:
            return fail("native C++ control did not compile", native.stderr)

        if compiler is not None:
            generated = temporary_root / "unqualified_cpp_layout.elisa"
            object_file = temporary_root / "unqualified_cpp_layout.o"
            generated.write_text(translated.stdout, encoding="utf-8")
            compiled = subprocess.run(
                [str(compiler), "-emit", "obj", "-O0", "-o", str(object_file), str(generated)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=90,
                check=False,
            )
            if compiled.returncode != 0:
                return fail("Elisa compiler rejected the unqualified C++ layout translation", compiled.stderr, generated.read_text(encoding="utf-8"))
            linked = subprocess.run(
                ["clang", "-Wl,-dead_strip", "-o", str(temporary_root / "generated"), str(object_file)],
                cwd=temporary_root,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if linked.returncode != 0:
                return fail("generated unqualified C++ layout object did not link", linked.stderr)
            native_run = subprocess.run([str(temporary_root / "native")], timeout=30, check=False)
            generated_run = subprocess.run([str(temporary_root / "generated")], timeout=30, check=False)
            if native_run.returncode != generated_run.returncode or native_run.returncode != 0:
                return fail(f"native/generated C++ layout behavior differs ({native_run.returncode}/{generated_run.returncode})")

    verification = "compile/runtime parity" if compiler is not None else "translation and native-control checks"
    print(f"unqualified C++ record-layout check OK (implicit-name filtering, ambiguity rejection, {verification})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
