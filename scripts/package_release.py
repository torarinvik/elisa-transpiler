#!/usr/bin/env python3
"""Assemble a relocatable Elisa C translator release directory.

The packager copies an already-built translator and the exact Elisa support
sources selected by the caller. It does not build the translator or choose a
license on the project's behalf. Every release therefore requires explicit
license files and an explicit version.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import stat
import tempfile


SCHEMA = "elisa-transpiler-release-v1"
REQUIRED_STDLIB = (
    "collections.elisa",
    "elisacore_json.elisa",
    "elisacore_runtime.elisa",
)
SOURCE_SUFFIXES = {".elisa", ".elisai"}
SHA256_RE = re.compile(r"[0-9a-f]{64}")


class ReleaseError(Exception):
    """A release input or destination violates the packaging contract."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_tree(root: Path) -> list[Path]:
    """Return regular files under root and reject symlinks/special files."""
    if not root.is_dir():
        raise ReleaseError("support source is not a directory: %s" % root)
    files: list[Path] = []
    for current, directories, names in os.walk(root, followlinks=False):
        current_path = Path(current)
        for name in list(directories):
            path = current_path / name
            if path.is_symlink():
                raise ReleaseError("support tree contains a symlink: %s" % path)
        for name in names:
            path = current_path / name
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode):
                raise ReleaseError("support tree contains a symlink: %s" % path)
            if not stat.S_ISREG(mode):
                raise ReleaseError("support tree contains a non-regular file: %s" % path)
            files.append(path)
    return sorted(files, key=lambda path: path.relative_to(root).as_posix())


def copy_tree_sources(source: Path, destination: Path, label: str) -> None:
    files = validate_tree(source)
    selected = [path for path in files if path.suffix in SOURCE_SUFFIXES]
    if not selected:
        raise ReleaseError("no Elisa source files found in %s: %s" % (label, source))
    destination.mkdir(parents=True, exist_ok=True)
    for path in selected:
        relative = path.relative_to(source)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        target.chmod(0o644)


def parse_license_spec(value: str) -> tuple[str, Path]:
    label, separator, path_text = value.partition("=")
    if not separator or not label or not path_text:
        raise argparse.ArgumentTypeError("license must use NAME=PATH")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", label):
        raise argparse.ArgumentTypeError("license name must be a simple identifier")
    return label, Path(path_text).expanduser().resolve()


def load_verified_build_record(path: Path, expected_target: str | None) -> tuple[str, str, dict[str, object]]:
    """Require fresh compiler provenance before producing a release candidate."""
    try:
        raw = path.expanduser().resolve(strict=True).read_bytes()
        record = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReleaseError("cannot read compiler compatibility record: %s" % error) from error
    if not isinstance(record, dict) or record.get("schema") != "elisa-transpiler-compiler-compatibility-v1":
        raise ReleaseError("unsupported compiler compatibility record schema")
    record_target = record.get("target")
    if not isinstance(record_target, str) or not record_target:
        raise ReleaseError("compiler compatibility record is missing its target")
    if expected_target is not None and record_target != expected_target:
        raise ReleaseError("release target does not match the verified compiler target")
    pair = record.get("compiler_pair")
    validation = record.get("translator_validation")
    if not isinstance(pair, dict) or not isinstance(validation, dict):
        raise ReleaseError("compiler compatibility record is missing compiler or translator state")
    if validation.get("status") != "verified" or validation.get("current_translator_sources_verified") is not True or validation.get("compiler_products_current") is not True:
        raise ReleaseError("compiler compatibility record does not verify current translator sources and products")
    stage0 = pair.get("stage0")
    stage1 = pair.get("stage1")
    if not isinstance(stage0, dict) or not isinstance(stage1, dict):
        raise ReleaseError("compiler compatibility record is missing Stage0 or Stage1")
    if stage0.get("source_freshness_verified") is not True or stage1.get("source_freshness_verified") is not True:
        raise ReleaseError("compiler compatibility record has stale compiler products")
    if stage1.get("bootstrap_reproduced_from_stage0") is not True:
        raise ReleaseError("Stage1 bootstrap has not been reproduced from the recorded Stage0")
    stage0_executable = stage0.get("executable")
    stage1_executable = stage1.get("executable")
    stage1_runtime = stage1.get("runtime")
    if not all(isinstance(item, dict) for item in (stage0_executable, stage1_executable, stage1_runtime)):
        raise ReleaseError("compiler compatibility record is missing product hashes")
    hashes = (stage0_executable.get("sha256"), stage1_executable.get("sha256"), stage1_runtime.get("sha256"))
    if any(not isinstance(value, str) or not SHA256_RE.fullmatch(value) for value in hashes):
        raise ReleaseError("compiler compatibility record contains an invalid product hash")
    if not all(isinstance(item.get("source_revision"), str) and item["source_revision"] for item in (stage0, stage1)):
        raise ReleaseError("compiler compatibility record is missing source revisions")
    summary: dict[str, object] = {
        "target": record_target,
        "stage0": {
            "source_revision": stage0["source_revision"],
            "executable_sha256": hashes[0],
        },
        "stage1": {
            "source_revision": stage1["source_revision"],
            "executable_sha256": hashes[1],
            "runtime_sha256": hashes[2],
        },
    }
    return hashlib.sha256(raw).hexdigest(), record_target, summary


def inventory(package_root: Path) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for path in sorted(package_root.rglob("*"), key=lambda item: item.relative_to(package_root).as_posix()):
        if path.is_dir():
            continue
        if path.name == "release-manifest.json":
            continue
        mode = path.stat().st_mode
        if not stat.S_ISREG(mode):
            raise ReleaseError("staged package contains a non-regular file: %s" % path)
        result.append({
            "path": path.relative_to(package_root).as_posix(),
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
            "mode": "0755" if mode & 0o111 else "0644",
        })
    return result


def assemble_release(
    *,
    version: str,
    translator: Path,
    cpp_lib_dir: Path,
    elisa_std_dir: Path,
    licenses: list[tuple[str, Path]],
    build_record: Path,
    clang_identity: str,
    output_dir: Path,
    target: str | None,
) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.+_-]*", version):
        raise ReleaseError("version must be a simple version identifier")
    if not clang_identity.strip() or "\n" in clang_identity or "\r" in clang_identity:
        raise ReleaseError("Clang identity must be one nonempty line")
    translator = translator.expanduser().resolve(strict=True)
    cpp_lib_dir = cpp_lib_dir.expanduser().resolve(strict=True)
    elisa_std_dir = elisa_std_dir.expanduser().resolve(strict=True)
    output_dir = output_dir.expanduser()
    output_dir = output_dir.parent.resolve() / output_dir.name
    if not translator.is_file() or not os.access(translator, os.X_OK):
        raise ReleaseError("translator is missing or not executable: %s" % translator)
    if not licenses:
        raise ReleaseError("at least one explicit --license NAME=PATH is required")
    names = [name.casefold() for name, _ in licenses]
    if len(set(names)) != len(names):
        raise ReleaseError("license names must be unique")
    for label, path in licenses:
        if not path.is_file() or path.is_symlink():
            raise ReleaseError("license input is missing or not a regular file (%s): %s" % (label, path))
    build_record_hash, record_target, toolchain_summary = load_verified_build_record(build_record, target)
    target = record_target
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", target):
        raise ReleaseError("verified build record has an invalid target identifier")
    cpp_files = validate_tree(cpp_lib_dir)
    if not any(path.suffix in SOURCE_SUFFIXES for path in cpp_files):
        raise ReleaseError("no Elisa compatibility sources found: %s" % cpp_lib_dir)
    std_files = validate_tree(elisa_std_dir)
    available_stdlib = {path.name for path in std_files}
    missing = sorted(set(REQUIRED_STDLIB) - available_stdlib)
    if missing:
        raise ReleaseError("Elisa standard library is missing required modules: %s" % ", ".join(missing))

    for source_root in (cpp_lib_dir, elisa_std_dir):
        if source_root == output_dir or source_root in output_dir.parents or output_dir in source_root.parents:
            raise ReleaseError("release destination overlaps a support source tree: %s" % source_root)

    if output_dir.exists() or output_dir.is_symlink():
        raise ReleaseError("refusing to replace existing release path: %s" % output_dir)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="." + output_dir.name + ".staging-", dir=output_dir.parent))
    try:
        binary_destination = staging / "bin" / "elisa-c-transpiler"
        binary_destination.parent.mkdir(parents=True)
        shutil.copyfile(translator, binary_destination)
        binary_destination.chmod(0o755)
        copy_tree_sources(cpp_lib_dir, staging / "cpp_lib", "cpp_lib")
        copy_tree_sources(elisa_std_dir, staging / "elisa_std", "Elisa standard library")

        license_manifest: list[dict[str, str]] = []
        for name, source in sorted(licenses, key=lambda item: item[0]):
            target_path = staging / "licenses" / (name + ".txt")
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target_path)
            target_path.chmod(0o644)
            license_manifest.append({"name": name, "path": target_path.relative_to(staging).as_posix()})

        usage = (
            "# Elisa C translator release %s\n\n"
            "This directory is relocatable. Clang must be available on PATH.\n\n"
            "Translate a source file with:\n\n"
            "```sh\n"
            "./bin/elisa-c-transpiler --cpp-lib-dir ./cpp_lib \\\n"
            "  --elisa-std-dir ./elisa_std source.c\n"
            "```\n\n"
            "Generated Elisa must be built with a compatible Elisa compiler and its matching runtime.\n"
            "The release manifest lists the exact packaged files and SHA-256 hashes.\n"
        ) % version
        with (staging / "README.md").open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(usage)
        (staging / "README.md").chmod(0o644)

        manifest = {
            "schema": SCHEMA,
            "version": version,
            "target": target,
            "package_host": platform.system().lower() + "-" + platform.machine().lower(),
            "dependencies": {"clang": clang_identity},
            "build_record_sha256": build_record_hash,
            "toolchain": toolchain_summary,
            "translator": "bin/elisa-c-transpiler",
            "support_directories": {"cpp_lib": "cpp_lib", "elisa_std": "elisa_std"},
            "licenses": license_manifest,
            "files": inventory(staging),
        }
        manifest_path = staging / "release-manifest.json"
        with manifest_path.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        manifest_path.chmod(0o644)
        # The staging directory is created beside the destination, so this
        # publication is an atomic same-filesystem rename and never replaces a
        # previously existing release.
        os.rename(staging, output_dir)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return output_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--translator", required=True, type=Path)
    parser.add_argument("--cpp-lib-dir", required=True, type=Path)
    parser.add_argument("--elisa-std-dir", required=True, type=Path)
    parser.add_argument("--license", action="append", default=[], type=parse_license_spec, metavar="NAME=PATH")
    parser.add_argument("--build-record", required=True, type=Path, help="verified docs/compiler_compatibility.json")
    parser.add_argument("--clang-identity", required=True, help="first line of the Clang version output used by this release")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--target", help="require the build record to name this target (default: use its target)")
    args = parser.parse_args()
    try:
        result = assemble_release(
            version=args.version,
            translator=args.translator,
            cpp_lib_dir=args.cpp_lib_dir,
            elisa_std_dir=args.elisa_std_dir,
            licenses=args.license,
            build_record=args.build_record,
            clang_identity=args.clang_identity,
            output_dir=args.output_dir,
            target=args.target,
        )
    except (OSError, ReleaseError) as error:
        parser.error(str(error))
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
