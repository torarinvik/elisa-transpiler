#!/usr/bin/env python3
"""Validate pinned upstream corpus identities and documented test contexts."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import unittest
from copy import deepcopy
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "testdata" / "upstream" / "corpus_manifest.json"
HASH40 = re.compile(r"[0-9a-f]{40}\Z")
HASH64 = re.compile(r"[0-9a-f]{64}\Z")
ALLOWED_IDENTITIES = {"vendored-git-tree", "nested-git-commit"}


def safe_repo_path(value: object) -> PurePosixPath | None:
    if not isinstance(value, str) or not value or "\\" in value:
        return None
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        return None
    return path


def validate_shape(manifest: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        return ["manifest must be an object with schema_version 1"]
    corpora = manifest.get("corpora")
    if not isinstance(corpora, list) or not corpora:
        return ["manifest corpora must be a non-empty array"]
    repository_hashes = manifest.get("repository_file_hashes", {})
    if not isinstance(repository_hashes, dict):
        errors.append("repository_file_hashes must be an object")
        repository_hashes = {}
    for relative, digest in repository_hashes.items():
        if safe_repo_path(relative) is None or not isinstance(digest, str) or not HASH64.fullmatch(digest):
            errors.append("repository_file_hashes contains an invalid path or SHA-256")
    names: set[str] = set()
    for index, entry in enumerate(corpora):
        where = f"corpora[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{where} must be an object")
            continue
        name = entry.get("name")
        if not isinstance(name, str) or not name or name in names:
            errors.append(f"{where}.name must be a unique non-empty string")
        else:
            names.add(name)
        if safe_repo_path(entry.get("root")) is None:
            errors.append(f"{where}.root must be a safe repository-relative path")
        if not isinstance(entry.get("required_for_suite"), bool):
            errors.append(f"{where}.required_for_suite must be a boolean")
        identity = entry.get("source_identity")
        if not isinstance(identity, dict) or identity.get("kind") not in ALLOWED_IDENTITIES:
            errors.append(f"{where}.source_identity has an unsupported kind")
        elif identity["kind"] == "vendored-git-tree":
            if not isinstance(identity.get("tree"), str) or not HASH40.fullmatch(identity["tree"]):
                errors.append(f"{where}.source_identity.tree must be a full Git object ID")
            if not isinstance(identity.get("recorded_by_commit"), str) or not HASH40.fullmatch(identity["recorded_by_commit"]):
                errors.append(f"{where}.source_identity.recorded_by_commit must be a full Git commit ID")
            upstream_revision = identity.get("upstream_revision")
            if upstream_revision is not None and (
                not isinstance(upstream_revision, str) or not HASH40.fullmatch(upstream_revision)
            ):
                errors.append(f"{where}.source_identity.upstream_revision must be null or a full commit ID")
        elif not isinstance(identity.get("commit"), str) or not HASH40.fullmatch(identity["commit"]):
            errors.append(f"{where}.source_identity.commit must be a full Git commit ID")
        license_info = entry.get("license")
        if not isinstance(license_info, dict) or not isinstance(license_info.get("spdx"), str):
            errors.append(f"{where}.license must identify an SPDX expression")
        elif not isinstance(license_info.get("files"), list) or not license_info["files"]:
            errors.append(f"{where}.license.files must be a non-empty array")
        for field in ("provenance_files",):
            files = entry.get(field)
            if not isinstance(files, list) or not files:
                errors.append(f"{where}.{field} must be a non-empty array")
            elif any(safe_repo_path(item) is None for item in files):
                errors.append(f"{where}.{field} contains an unsafe path")
        if isinstance(license_info, dict):
            license_paths = [*license_info.get("files", []), *license_info.get("separate_notice_files", [])]
            if any(safe_repo_path(item) is None for item in license_paths):
                errors.append(f"{where}.license files contain an unsafe path")
        translation = entry.get("translation")
        if not isinstance(translation, dict) or not isinstance(translation.get("suite_script"), (str, type(None))):
            errors.append(f"{where}.translation must identify its suite script or an explicit null")
        elif translation.get("source") is not None and safe_repo_path(translation["source"]) is None:
            errors.append(f"{where}.translation.source must be a safe relative path")
        elif translation.get("source_root", "corpus") not in ("corpus", "repository"):
            errors.append(f"{where}.translation.source_root must be corpus or repository")
        elif translation.get("argv") is not None and (
            not isinstance(translation["argv"], list)
            or not translation["argv"]
            or any(not isinstance(arg, str) for arg in translation["argv"])
        ):
            errors.append(f"{where}.translation.argv must be a non-empty argv array")
        if isinstance(translation, dict):
            generator = translation.get("compile_database_generator")
            if generator is not None and safe_repo_path(generator) is None:
                errors.append(f"{where}.translation.compile_database_generator must be a safe relative path")
            database = translation.get("generated_compile_database")
            database_path = safe_repo_path(database) if database is not None else None
            if database is not None and (database_path is None or database_path.parts[0] != "build"):
                errors.append(f"{where}.translation.generated_compile_database must be a build-relative path")
        native = entry.get("native")
        if not isinstance(native, dict) or native.get("kind") not in ("commands", "documented-context-only"):
            errors.append(f"{where}.native must identify commands or a documented-only context")
        elif native["kind"] == "commands":
            commands = native.get("commands")
            if not isinstance(commands, list) or not commands or any(
                not isinstance(command, list) or not command or any(not isinstance(arg, str) for arg in command)
                for command in commands
            ):
                errors.append(f"{where}.native.commands must be non-empty argv arrays")
        elif native["kind"] == "documented-context-only":
            for field in ("makefile",):
                if safe_repo_path(native.get(field)) is None:
                    errors.append(f"{where}.native.{field} must be a safe corpus-relative path")
            for field in ("configured_source_units", "all_source_units", "not_in_default_build"):
                values = native.get(field)
                if not isinstance(values, list) or any(safe_repo_path(value) is None for value in values):
                    errors.append(f"{where}.native.{field} must be an array of safe relative paths")
    if manifest.get("canonical_suite_command") != "sh scripts/test.sh --suite upstream":
        errors.append("canonical_suite_command must name the upstream acceptance command")
    return errors


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=root, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False,
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def cpp_code_tokens(source: str) -> list[str]:
    """Tokenize enough C++ to find namespace uses outside comments/literals."""
    tokens: list[str] = []
    index = 0
    raw_prefixes = ("u8R\"", "uR\"", "UR\"", "LR\"", "R\"")
    while index < len(source):
        if source[index].isspace():
            index += 1
            continue
        if source.startswith("//", index):
            newline = source.find("\n", index + 2)
            index = len(source) if newline < 0 else newline + 1
            continue
        if source.startswith("/*", index):
            closing = source.find("*/", index + 2)
            index = len(source) if closing < 0 else closing + 2
            continue

        raw_prefix = next(
            (prefix for prefix in raw_prefixes if source.startswith(prefix, index)),
            None,
        )
        if raw_prefix is not None:
            delimiter_start = index + len(raw_prefix)
            open_paren = source.find("(", delimiter_start, delimiter_start + 17)
            if open_paren < 0:
                index += len(raw_prefix)
                continue
            delimiter = source[delimiter_start:open_paren]
            closing = source.find(")" + delimiter + '"', open_paren + 1)
            index = len(source) if closing < 0 else closing + len(delimiter) + 2
            continue

        if source[index] in ('"', "'"):
            quote = source[index]
            index += 1
            while index < len(source):
                if source[index] == "\\":
                    index += 2
                elif source[index] == quote:
                    index += 1
                    break
                else:
                    index += 1
            continue

        character = source[index]
        if character == "_" or character.isascii() and character.isalpha():
            end = index + 1
            while end < len(source):
                part = source[end]
                if part != "_" and not (part.isascii() and part.isalnum()):
                    break
                end += 1
            tokens.append(source[index:end])
            index = end
            continue
        if source.startswith("::", index):
            tokens.append("::")
            index += 2
            continue
        index += 1
    return tokens


def cpp_std_symbols(source: str) -> set[str]:
    tokens = cpp_code_tokens(source)
    symbols: set[str] = set()
    index = 0
    while index + 2 < len(tokens):
        if tokens[index] != "std" or tokens[index + 1] != "::":
            index += 1
            continue
        symbol_index = index + 2
        # Normalize the common libc++/libstdc++ inline implementation
        # namespaces while retaining the public standard-library entity.
        if tokens[symbol_index].startswith("__") and symbol_index + 2 < len(tokens) and tokens[symbol_index + 1] == "::":
            symbol_index += 2
        symbols.add(tokens[symbol_index])
        index = symbol_index + 1
    return symbols


def read_source_for_cpp_scan(path: Path) -> str:
    # The pinned legacy game source contains non-UTF-8 comments. Replacement
    # decoding preserves ASCII C++ identifiers while keeping the audit usable.
    return path.read_bytes().decode("utf-8", errors="replace")


def resolve_inside(root: Path, base: Path, value: str) -> Path | None:
    relative = safe_repo_path(value)
    if relative is None:
        return None
    resolved = (base / Path(*relative.parts)).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        return None
    return resolved


def verify_manifest(root: Path, manifest: dict[str, Any]) -> list[str]:
    errors = validate_shape(manifest)
    if errors:
        return errors
    for entry in manifest["corpora"]:
        name = entry["name"]
        identity = entry["source_identity"]
        if identity["kind"] == "nested-git-commit":
            indexed = git(root, "ls-files", "--stage", "--", entry["root"])
            rows = [line.split() for line in indexed.stdout.splitlines()]
            if indexed.returncode != 0 or len(rows) != 1 or len(rows[0]) < 4:
                errors.append(f"{name}: superproject index is missing its submodule gitlink")
            elif rows[0][0] != "160000" or rows[0][1] != identity["commit"] or rows[0][2] != "0":
                errors.append(f"{name}: superproject gitlink does not match pinned commit {identity['commit']}")
        corpus_root = resolve_inside(root, root, entry["root"])
        if corpus_root is None or not corpus_root.is_dir():
            if entry["required_for_suite"]:
                errors.append(f"{name}: required corpus checkout is missing: {entry['root']}")
            continue
        if identity["kind"] == "vendored-git-tree":
            tree_spec = f"{identity['recorded_by_commit']}:{entry['root']}"
            recorded_tree = git(root, "rev-parse", tree_spec)
            if recorded_tree.returncode != 0 or recorded_tree.stdout.strip() != identity["tree"]:
                errors.append(f"{name}: recorded Git tree does not match {tree_spec}")
            changed = git(root, "diff", "--quiet", identity["recorded_by_commit"], "--", entry["root"])
            if changed.returncode != 0:
                errors.append(f"{name}: vendored source differs from its recorded snapshot")
        else:
            actual = git(root, "-C", str(corpus_root), "rev-parse", "HEAD")
            if actual.returncode != 0 or actual.stdout.strip() != identity["commit"]:
                errors.append(f"{name}: nested checkout is not at pinned commit {identity['commit']}")
            dirty = git(root, "-C", str(corpus_root), "status", "--porcelain", "--untracked-files=no")
            if dirty.returncode != 0 or dirty.stdout.strip():
                errors.append(f"{name}: tracked files in nested checkout are modified")
        for relative in [
            *entry["provenance_files"],
            *entry["license"]["files"],
            *entry["license"].get("separate_notice_files", []),
        ]:
            path = resolve_inside(root, corpus_root, relative)
            if path is None or not path.is_file():
                errors.append(f"{name}: required corpus/license file is missing: {relative}")
        translation_source = entry["translation"].get("source")
        if translation_source:
            source_base = root if entry["translation"].get("source_root") == "repository" else corpus_root
            path = resolve_inside(root, source_base, translation_source)
            if path is None or not path.is_file():
                errors.append(f"{name}: translation source is missing: {translation_source}")
        suite_script = entry["translation"].get("suite_script")
        if suite_script:
            path = resolve_inside(root, root, suite_script)
            if path is None or not path.is_file():
                errors.append(f"{name}: translation suite script is missing: {suite_script}")
        compile_database_generator = entry["translation"].get("compile_database_generator")
        if compile_database_generator:
            path = resolve_inside(root, root, compile_database_generator)
            if path is None or not path.is_file():
                errors.append(f"{name}: compile database generator is missing: {compile_database_generator}")
        if entry["native"]["kind"] == "documented-context-only" and entry["native"].get("makefile"):
            native = entry["native"]
            makefile_path = resolve_inside(root, corpus_root, native["makefile"])
            if makefile_path is None or not makefile_path.is_file():
                errors.append(f"{name}: documented native Makefile is missing: {native['makefile']}")
            else:
                makefile_text = makefile_path.read_text(encoding="utf-8")
                makefile_sources = re.findall(r"^SRCS\s*\+=\s*([^\s#]+)", makefile_text, re.MULTILINE)
                if makefile_sources != native["configured_source_units"]:
                    errors.append(f"{name}: configured source-unit inventory differs from its Makefile")
                tracked = git(root, "-C", str(corpus_root), "ls-files", "--", "*.c", "*.cpp")
                tracked_units = sorted(tracked.stdout.splitlines())
                if tracked.returncode != 0 or tracked_units != native["all_source_units"]:
                    errors.append(f"{name}: checked-in C/C++ translation-unit inventory differs from manifest")
                expected_excluded = sorted(set(native["all_source_units"]) - set(native["configured_source_units"]))
                if expected_excluded != sorted(native["not_in_default_build"]):
                    errors.append(f"{name}: default-build exclusions do not match source inventory")
                if native.get("c_standard") != "gnu99" or "CCFLAGS += -std=gnu99" not in makefile_text:
                    errors.append(f"{name}: C language standard differs from Makefile")
                if native.get("cxx_standard") != "host compiler default" or "CXXFLAGS += $(CFLAGS)" not in makefile_text:
                    errors.append(f"{name}: C++ language-mode policy differs from Makefile")
                if "SDL_CONFIG  ?= pkg-config sdl2 SDL2_mixer" not in makefile_text:
                    errors.append(f"{name}: SDL pkg-config dependency context differs from Makefile")
                for flag in native.get("common_warning_flags", []):
                    if f"CFLAGS += {flag}" not in makefile_text:
                        errors.append(f"{name}: common Makefile warning flag is missing: {flag}")
                for flag in native.get("c_only_warning_flags", []):
                    if f"CCFLAGS += {flag}" not in makefile_text:
                        errors.append(f"{name}: C-only Makefile warning flag is missing: {flag}")
    for relative, expected in manifest.get("repository_file_hashes", {}).items():
        path = resolve_inside(root, root, relative)
        if path is None or not path.is_file() or sha256(path) != expected:
            errors.append(f"repository test input hash mismatch: {relative}")
    return errors


def load_manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("corpus manifest root must be an object")
    return value


class CorpusProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = load_manifest(MANIFEST_PATH)

    def test_checked_in_sources_match_their_pins(self) -> None:
        self.assertEqual(verify_manifest(ROOT, self.manifest), [])

    def test_cpp_library_inventory_ignores_comments_and_literals(self) -> None:
        source = r'''\
            // std::commented_out
            const char *ordinary = "std::inside_string";
            const char *character = 'x';
            const char *raw = R"tag(std::inside_raw_string)tag";
            /* std::inside_block_comment */
            std::vector<int> values;
            std::__1::string name;
        '''
        self.assertEqual(cpp_std_symbols(source), {"vector", "string"})

    def test_corpus_cpp_library_priority_inventory(self) -> None:
        corpora = {item["name"]: item for item in self.manifest["corpora"]}
        wolf_root = ROOT / corpora["Wolf4SDL"]["root"]
        wolf_symbols = set()
        for path in wolf_root.rglob("*"):
            if path.is_file() and path.suffix in (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp"):
                wolf_symbols.update(cpp_std_symbols(read_source_for_cpp_scan(path)))
        self.assertEqual(wolf_symbols, {"unordered_map"})

        inih_root = ROOT / corpora["inih"]["root"]
        inih_wrapper_symbols = set()
        for directory in (inih_root / "cpp", inih_root / "examples"):
            for path in directory.rglob("*"):
                if path.is_file() and path.suffix in (".cc", ".cpp", ".cxx", ".h", ".hpp"):
                    inih_wrapper_symbols.update(cpp_std_symbols(read_source_for_cpp_scan(path)))
        self.assertEqual(
            inih_wrapper_symbols,
            {"cout", "map", "set", "string", "to_string", "transform", "vector"},
        )

        for corpus_name in ("inih", "kilo", "cJSON"):
            entry = corpora[corpus_name]
            source = entry["translation"].get("source")
            base = ROOT if entry["translation"].get("source_root") == "repository" else ROOT / entry["root"]
            self.assertIsInstance(source, str)
            self.assertEqual(cpp_std_symbols(read_source_for_cpp_scan(base / source)), set())

    def test_path_traversal_is_rejected(self) -> None:
        manifest = deepcopy(self.manifest)
        manifest["corpora"][0]["root"] = "../outside"
        errors = validate_shape(manifest)
        self.assertTrue(any("safe repository-relative path" in error for error in errors))

    def test_hash_mismatch_for_local_harness_is_reported(self) -> None:
        manifest = deepcopy(self.manifest)
        manifest["repository_file_hashes"]["testdata/fixtures/cjson_smoke.c"] = "0" * 64
        errors = verify_manifest(ROOT, manifest)
        self.assertTrue(any("repository test input hash mismatch: testdata/fixtures/cjson_smoke.c" in error for error in errors))

    def test_missing_corpus_file_is_reported(self) -> None:
        manifest = deepcopy(self.manifest)
        manifest["corpora"][0]["provenance_files"].append("missing.c")
        errors = verify_manifest(ROOT, manifest)
        self.assertTrue(any("required corpus/license file is missing: missing.c" in error for error in errors))

    def test_nested_commit_pin_is_validated_as_a_full_revision(self) -> None:
        manifest = deepcopy(self.manifest)
        manifest["corpora"][2]["source_identity"]["commit"] = "not-a-commit"
        errors = validate_shape(manifest)
        self.assertTrue(any("full Git commit ID" in error for error in errors))

    def test_submodule_gitlink_must_match_the_pinned_nested_commit(self) -> None:
        manifest = deepcopy(self.manifest)
        manifest["corpora"][2]["source_identity"]["commit"] = "0" * 40
        errors = verify_manifest(ROOT, manifest)
        self.assertTrue(any("superproject gitlink does not match" in error for error in errors))

    def test_wolf_unit_inventory_is_bound_to_the_vendored_makefile(self) -> None:
        manifest = deepcopy(self.manifest)
        wolf = next(item for item in manifest["corpora"] if item["name"] == "Wolf4SDL")
        wolf["native"]["configured_source_units"].pop()
        errors = verify_manifest(ROOT, manifest)
        self.assertTrue(any("configured source-unit inventory differs from its Makefile" in error for error in errors))

    def test_wolf_compile_database_generator_is_present_and_build_output_is_local(self) -> None:
        manifest = deepcopy(self.manifest)
        wolf = next(item for item in manifest["corpora"] if item["name"] == "Wolf4SDL")
        wolf["translation"]["compile_database_generator"] = "../outside.py"
        wolf["translation"]["generated_compile_database"] = "testdata/compile_commands.json"
        errors = validate_shape(manifest)
        self.assertTrue(any("compile_database_generator must be a safe" in error for error in errors))
        self.assertTrue(any("generated_compile_database must be a build-relative" in error for error in errors))

        wolf["translation"]["compile_database_generator"] = "scripts/missing_generator.py"
        wolf["translation"]["generated_compile_database"] = "build/wolf/compile_commands.json"
        errors = verify_manifest(ROOT, manifest)
        self.assertTrue(any("compile database generator is missing" in error for error in errors))

    def test_vendored_upstream_revision_is_validated_when_recorded(self) -> None:
        manifest = deepcopy(self.manifest)
        manifest["corpora"][0]["source_identity"]["upstream_revision"] = "26254ee"
        errors = validate_shape(manifest)
        self.assertTrue(any("null or a full commit ID" in error for error in errors))


if __name__ == "__main__":
    unittest.main(verbosity=2)
