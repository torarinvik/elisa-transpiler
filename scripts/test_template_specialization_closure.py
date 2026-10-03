#!/usr/bin/env python3
"""Retain and lower a used external class-template specialization via Clang IDs."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
HEADER = """\
template<typename T>
struct ExternalCell {
    T value;
};

using IntegerCell = ExternalCell<int>;
"""
PROGRAM = """\
#include \"model.hpp\"

int main()
{
    IntegerCell cell;
    cell.value = 41;
    return cell.value == 41 ? 0 : 1;
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


def externalize_subtree(node: object, origin: str) -> None:
    if isinstance(node, dict):
        location = node.get("loc")
        if isinstance(location, dict):
            location["file"] = origin
        node.pop("isUsed", None)
        node.pop("isReferenced", None)
        for value in node.values():
            externalize_subtree(value, origin)
    elif isinstance(node, list):
        for value in node:
            externalize_subtree(value, origin)


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: test_template_specialization_closure.py TRANSLATOR ELISA_COMPILER [ELISA_RUNTIME]", file=sys.stderr)
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
    clang = shutil.which("clang++")
    if clang is None:
        print("clang++ is required for the template-specialization regression", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory(prefix="elisa-template-specialization-") as temporary_directory:
        temporary_root = Path(temporary_directory)
        headers = temporary_root / "external-headers"
        headers.mkdir()
        header = headers / "model.hpp"
        source = temporary_root / "template_specialization.cpp"
        header.write_text(HEADER, encoding="utf-8")
        source.write_text(PROGRAM, encoding="utf-8")

        native = temporary_root / "native"
        native_build = subprocess.run(
            [clang, "-std=c++17", "-I", str(headers), str(source), "-o", str(native)],
            cwd=temporary_root,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if native_build.returncode != 0:
            return fail("native Clang rejected the template-specialization fixture", native_build.stderr)

        ast_result = subprocess.run(
            [clang, "-std=c++17", "-I", str(headers), "-Xclang", "-ast-dump=json", "-fsyntax-only", str(source)],
            cwd=temporary_root,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if ast_result.returncode != 0:
            return fail("Clang failed to create the template-specialization AST", ast_result.stderr)
        ast = json.loads(ast_result.stdout)
        template = next(
            (
                node
                for node in ast.get("inner", [])
                if isinstance(node, dict)
                and node.get("kind") == "ClassTemplateDecl"
                and node.get("name") == "ExternalCell"
            ),
            None,
        )
        alias = next(
            (
                node
                for node in ast.get("inner", [])
                if isinstance(node, dict)
                and node.get("kind") == "TypeAliasDecl"
                and node.get("name") == "IntegerCell"
            ),
            None,
        )
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
        if not isinstance(template, dict) or not isinstance(alias, dict) or not isinstance(main_decl, dict):
            return fail("Clang AST lacks the expected template, alias or main declaration")

        specializations = [
            node
            for node in walk(template)
            if node.get("kind") == "ClassTemplateSpecializationDecl"
            and node.get("name") == "ExternalCell"
            and node.get("completeDefinition") is True
        ]
        if len(specializations) != 1 or not isinstance(specializations[0].get("id"), str):
            return fail(f"expected one complete ExternalCell specialization, found {len(specializations)}")
        specialization_id = specializations[0]["id"]
        alias_reaches_specialization = any(
            node.get("kind") == "RecordType"
            and isinstance(node.get("decl"), dict)
            and node["decl"].get("id") == specialization_id
            for node in walk(alias)
        )
        if not alias_reaches_specialization:
            return fail("Clang alias type no longer carries a RecordType.decl edge to its specialization")

        externalize_subtree(template, "/synthetic/non-project/model.hpp")
        externalize_subtree(alias, "/synthetic/non-project/model.hpp")
        main_decl.setdefault("loc", {})["file"] = str(source)
        # Keep the alias identity edge but remove the convenient desugared type
        # spelling from source expressions. Otherwise a name-based fallback for
        # ExternalCell could mask a broken specialization-ID closure.
        for node in walk(main_decl):
            type_info = node.get("type")
            if isinstance(type_info, dict):
                type_info.pop("desugaredQualType", None)
        if "ExternalCell" in json.dumps(main_decl, separators=(",", ":")):
            return fail("source subtree still exposes the template name and can pass by spelling fallback")

        ast_path = temporary_root / "external-template-specialization.json"
        ast_path.write_text(json.dumps(ast, separators=(",", ":")), encoding="utf-8")
        environment = os.environ.copy()
        fake_tools = temporary_root / "fake-tools"
        fake_tools.mkdir()
        (fake_tools / "clang++").symlink_to(ROOT / "testdata/fake_tools/clang")
        environment["PATH"] = str(fake_tools) + os.pathsep + str(ROOT / "testdata/fake_tools") + os.pathsep + environment.get("PATH", "")
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
            return fail("external template specialization was lost or rejected during translation", translated.stderr)
        if "struct IntegerCell:" not in translated.stdout or ("value: i32" not in translated.stdout and "value: mutable i32" not in translated.stdout):
            return fail("generated Elisa lacks the concrete specialized record layout", translated.stderr, translated.stdout)
        if "cell: mutable IntegerCell = zeroed" not in translated.stdout:
            return fail("record-valued C++ alias was not preserved in the generated Elisa type", translated.stdout)

        generated = temporary_root / "template_specialization.elisa"
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
            return fail("Elisa compiler rejected the specialized-record translation", generated_build.stderr, translated.stdout)
        generated_executable = temporary_root / "generated"
        link_argv = [clang, "-Wl,-dead_strip", "-o", str(generated_executable), str(object_file)]
        if runtime is not None:
            link_argv.append(str(runtime))
        linked = subprocess.run(link_argv, cwd=temporary_root, capture_output=True, text=True, timeout=30, check=False)
        if linked.returncode != 0:
            return fail("generated template-specialization object did not link", linked.stderr)
        native_run = subprocess.run([str(native)], cwd=temporary_root, capture_output=True, timeout=30, check=False)
        generated_run = subprocess.run([str(generated_executable)], cwd=temporary_root, capture_output=True, timeout=30, check=False)
        if (native_run.returncode, native_run.stdout, native_run.stderr) != (generated_run.returncode, generated_run.stdout, generated_run.stderr):
            return fail(f"native/generated template-specialization behavior differs ({native_run.returncode}/{generated_run.returncode})")
        if native_run.returncode != 0:
            return fail(f"template-specialization fixture returned {native_run.returncode} instead of 0")

    print("template specialization dependency closure check OK (type-alias ID reaches concrete layout; compile/link/runtime parity)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
