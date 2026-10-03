#!/usr/bin/env python3
"""Retain nested record-layout dependencies reachable through Clang IDs."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
HEADER_SOURCE = """\
struct Hidden {
    int value;
};

typedef struct Hidden HiddenAlias;
typedef HiddenAlias LeafAlias;

struct LayoutOnly {
    int value;
};

struct LayoutOwner {
    struct LayoutOnly payload;
};

struct Token {
    long tag_value;
};
typedef int Token;

struct AliasOwner {
    Token value;
};

struct UnusedExternal {
    int value;
};
typedef struct UnusedExternal UnusedExternalAlias;

static inline int external_helper(void)
{
    struct UnusedExternal item;
    return item.value;
}
"""
PROGRAM_SOURCE = """\
#include "model.h"

int main(void)
{
    LeafAlias item;
    if (sizeof(item) != sizeof(int))
        return 1;
    struct LayoutOwner layout;
    if (sizeof(layout) != sizeof(int))
        return 2;
    struct AliasOwner alias;
    if (sizeof(alias.value) != sizeof(int))
        return 3;
    return 0;
}
"""


def fail(message: str, *outputs: str) -> int:
    print(message, file=sys.stderr)
    for output in outputs:
        if output:
            print(output[:2000], file=sys.stderr)
    return 1


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: test_transitive_decl_closure.py TRANSLATOR [ELISA_COMPILER]", file=sys.stderr)
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
        print("clang is required for the transitive declaration-closure regression", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory(prefix="elisa-transitive-decls-") as temporary_directory:
        temporary_root = Path(temporary_directory)
        source = temporary_root / "transitive_layout.c"
        header_directory = temporary_root / "headers"
        header_directory.mkdir()
        header = header_directory / "model.h"
        source.write_text(PROGRAM_SOURCE, encoding="utf-8")
        header.write_text(HEADER_SOURCE, encoding="utf-8")
        raw_ast = subprocess.run(
            [
                clang,
                "-std=c11",
                "-I",
                str(header_directory),
                "-Xclang",
                "-fdump-record-layouts-simple",
                "-Xclang",
                "-ast-dump=json",
                "-fsyntax-only",
                str(source),
            ],
            cwd=temporary_root,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if raw_ast.returncode != 0:
            return fail("Clang failed to create the transitive-layout AST", raw_ast.stderr)

        json_start = raw_ast.stdout.find("{")
        if json_start < 0:
            return fail("Clang emitted no JSON AST after its record-layout dump", raw_ast.stdout)
        layout_dump = raw_ast.stdout[:json_start]
        ast_text = raw_ast.stdout[json_start:]
        provenance_ast = json.loads(ast_text)
        ast = json.loads(ast_text)
        inner = ast.get("inner")
        if not isinstance(inner, list):
            return fail("Clang AST has no top-level declaration list")
        records = [
            node
            for node in inner
            if isinstance(node, dict)
            and node.get("kind") == "RecordDecl"
            and node.get("name") == "Hidden"
            and node.get("completeDefinition") is True
        ]
        if len(records) != 1:
            return fail("Clang AST fixture lacks the complete Hidden record declaration")
        layout_owner = next(
            (
                node
                for node in inner
                if isinstance(node, dict)
                and node.get("kind") == "RecordDecl"
                and node.get("name") == "LayoutOwner"
                and node.get("completeDefinition") is True
            ),
            None,
        )
        layout_field = next(
            (
                node
                for node in layout_owner.get("inner", [])
                if isinstance(node, dict) and node.get("kind") == "FieldDecl" and node.get("name") == "payload"
            ),
            None,
        ) if isinstance(layout_owner, dict) else None
        field_type = layout_field.get("type") if isinstance(layout_field, dict) else None
        if not isinstance(field_type, dict) or field_type.get("qualType") != "struct LayoutOnly":
            return fail("Clang AST fixture changed: expected LayoutOwner.payload to spell struct LayoutOnly")
        if any(key in field_type for key in ("decl", "typeAliasDeclId", "ownedTagDecl")):
            return fail("Clang AST fixture now exposes an explicit declaration edge for the ID-less field case")
        alias_owner = next(
            (
                node
                for node in inner
                if isinstance(node, dict)
                and node.get("kind") == "RecordDecl"
                and node.get("name") == "AliasOwner"
                and node.get("completeDefinition") is True
            ),
            None,
        )
        alias_field = next(
            (
                node
                for node in alias_owner.get("inner", [])
                if isinstance(node, dict) and node.get("kind") == "FieldDecl" and node.get("name") == "value"
            ),
            None,
        ) if isinstance(alias_owner, dict) else None
        alias_field_type = alias_field.get("type") if isinstance(alias_field, dict) else None
        if not isinstance(alias_field_type, dict) or alias_field_type.get("qualType") != "Token":
            return fail("Clang AST fixture changed: expected AliasOwner.value to use the Token typedef")

        # The source uses only LeafAlias. Give each header declaration a
        # synthetic external location, but leave its nested AST nodes as Clang
        # emitted them (usually with an offset and no repeated file). This
        # catches source-provenance fallback leaking through external parents.
        # Remove Clang's desugared type spelling from the source variable so
        # retention must follow VarDecl.typeAliasDeclId -> LeafAlias ->
        # HiddenAlias -> Hidden through Clang declaration IDs.
        hidden_names = {"Hidden", "HiddenAlias", "LeafAlias"}
        idless_layout_names = {"LayoutOnly", "LayoutOwner"}
        relocated = set()
        external_names = hidden_names | idless_layout_names | {"Token", "AliasOwner", "UnusedExternal", "UnusedExternalAlias", "external_helper"}

        def relocate(node, path):
            location = node.setdefault("loc", {})
            if isinstance(location, dict):
                location["file"] = path
                location.pop("includedFrom", None)

        def mutate(node):
            if isinstance(node, dict):
                if node.get("kind") in {"RecordDecl", "TypedefDecl", "FunctionDecl"} and node.get("name") in external_names:
                    name = node["name"]
                    relocate(node, f"/synthetic/non-project/{name}.h")
                    if name in hidden_names:
                        relocated.add(name)
                    return
                for value in node.values():
                    mutate(value)
            elif isinstance(node, list):
                for value in node:
                    mutate(value)

        mutate(ast)
        if relocated != hidden_names:
            return fail("Clang AST fixture lacks one or more declarations in the hidden alias chain")

        main = next(
            (
                node
                for node in inner
                if isinstance(node, dict)
                and node.get("kind") == "FunctionDecl"
                and node.get("name") == "main"
            ),
            None,
        )
        def strip_desugared_types(node):
            if isinstance(node, dict):
                node.pop("desugaredQualType", None)
                for value in node.values():
                    strip_desugared_types(value)
            elif isinstance(node, list):
                for value in node:
                    strip_desugared_types(value)

        if isinstance(main, dict):
            strip_desugared_types(main)
        if not isinstance(main, dict) or "Hidden" in json.dumps(main):
            return fail("source AST still exposes Hidden by spelling instead of only its outer alias")
        if "LayoutOnly" in json.dumps(main):
            return fail("source AST spells the ID-less field type, so the layout regression is not isolated")

        ast_path = temporary_root / "transitive-layout.json"
        ast_path.write_text(layout_dump + json.dumps(ast, separators=(",", ":")), encoding="utf-8")
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
            return fail("transitive record dependency was lost during AST projection", translated.stderr)

        if any(name not in translated.stdout for name in hidden_names):
            return fail("generated Elisa is missing a declaration from the transitive alias chain", translated.stderr, translated.stdout)
        if any(name not in translated.stdout for name in idless_layout_names):
            return fail("ID-less by-value record-field dependency was lost during projection", translated.stderr, translated.stdout)
        if "struct LayoutOnly:\n    value: i32" not in translated.stdout:
            return fail("projected LayoutOnly declaration lacks its complete field layout", translated.stderr, translated.stdout)
        if "struct AliasOwner:" not in translated.stdout:
            return fail("source-reachable AliasOwner was lost during dependency projection", translated.stderr, translated.stdout)
        if "struct Token:" in translated.stdout or "tag_value" in translated.stdout:
            return fail("bare typedef spelling incorrectly resolved to a same-named C tag", translated.stderr, translated.stdout)
        if "UnusedExternal" in translated.stdout or "external_helper" in translated.stdout:
            return fail("nested external-header type leaked into source-name retention", translated.stderr, translated.stdout)

        # A simple tag spelling is not a declaration identity. If another
        # unrelated scope contributes a same-named record, the conservative
        # name index must refuse to choose either layout rather than retain
        # the wrong declaration by spelling alone.
        ambiguous_ast = json.loads(json.dumps(ast))
        ambiguous_inner = ambiguous_ast.get("inner")
        if not isinstance(ambiguous_inner, list):
            return fail("Clang AST fixture lost its top-level declarations for ambiguity coverage")
        ambiguous_inner.append(
            {
                "id": "0xA11B0000",
                "kind": "RecordDecl",
                "name": "LayoutOnly",
                "tagUsed": "struct",
                "completeDefinition": True,
                "loc": {"file": "/synthetic/other-scope/LayoutOnly.h"},
                "inner": [
                    {
                        "id": "0xA11B0001",
                        "kind": "FieldDecl",
                        "name": "unrelated_value",
                        "type": {"qualType": "long"},
                    }
                ],
            }
        )
        ambiguous_ast_path = temporary_root / "ambiguous-tag-name.json"
        ambiguous_ast_path.write_text(layout_dump + json.dumps(ambiguous_ast, separators=(",", ":")), encoding="utf-8")
        ambiguous_environment = environment.copy()
        ambiguous_environment["ELISA_FAKE_CLANG_JSON"] = str(ambiguous_ast_path)
        ambiguous_translation = subprocess.run(
            [str(translator), str(source)],
            cwd=ROOT,
            env=ambiguous_environment,
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
        if ambiguous_translation.returncode != 0 or not ambiguous_translation.stdout:
            return fail("translator rejected an AST with an ambiguous unqualified tag spelling", ambiguous_translation.stderr)
        if "struct LayoutOnly:\n    value: i32" in ambiguous_translation.stdout or "unrelated_value" in ambiguous_translation.stdout:
            return fail(
                "ambiguous unqualified tag spelling retained a record layout by name alone",
                ambiguous_translation.stderr,
                ambiguous_translation.stdout,
            )

        provenance_ast_path = temporary_root / "natural-header-provenance.json"
        provenance_ast_path.write_text(
            layout_dump + json.dumps(provenance_ast, separators=(",", ":")),
            encoding="utf-8",
        )
        provenance_environment = environment.copy()
        provenance_environment["ELISA_FAKE_CLANG_JSON"] = str(provenance_ast_path)
        provenance_translation = subprocess.run(
            [str(translator), str(source)],
            cwd=ROOT,
            env=provenance_environment,
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
        if provenance_translation.returncode != 0 or not provenance_translation.stdout:
            return fail(
                f"translator rejected Clang's natural header provenance (exit {provenance_translation.returncode})",
                provenance_translation.stderr,
                provenance_translation.stdout,
            )
        if "UnusedExternal" in provenance_translation.stdout or "external_helper" in provenance_translation.stdout:
            return fail(
                "header siblings with omitted file paths leaked into source projection",
                provenance_translation.stderr,
                provenance_translation.stdout,
            )

        # Model a Clang location schema that retains only `includedFrom` for
        # an included declaration. Put it after a main-file sibling so source
        # provenance has already been established; the include marker must
        # still prevent this unused external record from entering the output.
        inherited_provenance_ast = json.loads(json.dumps(provenance_ast))
        inherited_inner = inherited_provenance_ast.get("inner")
        inherited_record = next(
            (
                node
                for node in inherited_inner or []
                if isinstance(node, dict)
                and node.get("kind") == "RecordDecl"
                and node.get("name") == "UnusedExternal"
            ),
            None,
        )
        if not isinstance(inherited_inner, list) or not isinstance(inherited_record, dict):
            return fail("Clang AST fixture lacks the external record for inherited-provenance coverage")
        inherited_location = inherited_record.get("loc")
        if not isinstance(inherited_location, dict):
            return fail("external record has no location to model the omitted-file schema")
        inherited_inner.remove(inherited_record)
        inherited_location.pop("file", None)
        inherited_location["includedFrom"] = {"file": str(source)}
        inherited_inner.append(inherited_record)

        inherited_ast_path = temporary_root / "inherited-header-provenance.json"
        inherited_ast_path.write_text(
            layout_dump + json.dumps(inherited_provenance_ast, separators=(",", ":")),
            encoding="utf-8",
        )
        inherited_environment = environment.copy()
        inherited_environment["ELISA_FAKE_CLANG_JSON"] = str(inherited_ast_path)
        inherited_translation = subprocess.run(
            [str(translator), str(source)],
            cwd=ROOT,
            env=inherited_environment,
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
        if inherited_translation.returncode != 0 or not inherited_translation.stdout:
            return fail("translator rejected an included declaration with omitted file provenance", inherited_translation.stderr)
        if "UnusedExternal" in inherited_translation.stdout:
            return fail(
                "includedFrom-only external record inherited main-file provenance from an earlier sibling",
                inherited_translation.stderr,
                inherited_translation.stdout,
            )

        native = subprocess.run(
            [clang, "-std=c11", "-I", str(header_directory), str(source), "-o", str(temporary_root / "native")],
            cwd=temporary_root,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if native.returncode != 0:
            return fail("native control did not compile", native.stderr)

        if compiler is not None:
            generated = temporary_root / "transitive_alias_chain.elisa"
            object_file = temporary_root / "transitive_alias_chain.o"
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
                return fail("Elisa compiler rejected the transitive-layout translation", compiled.stderr, generated.read_text(encoding="utf-8"))

            linked = subprocess.run(
                ["clang", "-Wl,-dead_strip", "-o", str(temporary_root / "generated"), str(object_file)],
                cwd=temporary_root,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if linked.returncode != 0:
                return fail("generated transitive-alias object did not link", linked.stderr)

            native_run = subprocess.run([str(temporary_root / "native")], timeout=30, check=False)
            generated_run = subprocess.run([str(temporary_root / "generated")], timeout=30, check=False)
            if native_run.returncode != generated_run.returncode or native_run.returncode != 0:
                return fail(
                    f"native/generated nested-layout behavior differs ({native_run.returncode}/{generated_run.returncode})"
                )


    verification = "compile/runtime parity" if compiler is not None else "translation and native-control checks"
    print(f"transitive declaration closure check OK (hidden typedef chain, C tag collision; {verification})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
