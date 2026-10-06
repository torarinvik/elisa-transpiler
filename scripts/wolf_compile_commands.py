#!/usr/bin/env python3
"""Generate a local Clang compilation database from Wolf4SDL's pinned Makefile."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "testdata" / "upstream" / "corpus_manifest.json"
CORPUS = ROOT / "testdata" / "upstream" / "wolf4sdl"
BUILD_ROOT = ROOT / "build" / "wolf4sdl"
MAKEFILE = CORPUS / "Makefile"
CONFIG = CORPUS / "config.default"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run(
    argv: Sequence[str], cwd: Path | None = None, env: dict[str, str] | None = None,
) -> str:
    try:
        result = subprocess.run(
            list(argv), cwd=cwd, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=False,
            env={**(os.environ if env is None else env), "LC_ALL": "C"},
        )
    except OSError as error:
        raise ValueError(f"cannot run {argv[0]}: {error}") from error
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise ValueError(f"command failed ({result.returncode}): {shlex.join(argv)}\n{detail}")
    return result.stdout


def pinned_wolf_entry() -> dict[str, object]:
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        entry = next(item for item in manifest["corpora"] if item["name"] == "Wolf4SDL")
        expected = entry["source_identity"]["commit"]
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as error:
        raise ValueError(f"cannot read the Wolf4SDL corpus pin from {MANIFEST}: {error}") from error
    actual = run(["git", "-C", str(CORPUS), "rev-parse", "HEAD"]).strip()
    if actual != expected:
        raise ValueError(f"Wolf4SDL checkout is at {actual}, but the manifest pins {expected}")
    dirty = run(["git", "-C", str(CORPUS), "status", "--porcelain", "--untracked-files=no"])
    if dirty.strip():
        raise ValueError("Wolf4SDL tracked files are modified; refusing to describe a non-pinned build context")
    native = entry["native"]
    units = native["configured_source_units"]
    makefile_sources = re.findall(r"^SRCS\s*\+=\s*([^\s#]+)", MAKEFILE.read_text(encoding="utf-8"), re.MULTILINE)
    if makefile_sources != units:
        raise ValueError("Wolf4SDL Makefile source list differs from the pinned corpus manifest")
    if native.get("required_packages") != ["sdl2", "SDL2_mixer"]:
        raise ValueError("manifest SDL2 package requirements are missing or inconsistent")
    return entry


def parse_make_dry_run(output: str, corpus_root: Path, units: Sequence[str]) -> list[dict[str, object]]:
    expected = set(units)
    commands: dict[str, dict[str, object]] = {}
    for line_number, line in enumerate(output.splitlines(), 1):
        try:
            argv = shlex.split(line, posix=True)
        except ValueError as error:
            raise ValueError(f"cannot parse Make dry-run line {line_number}: {error}") from error
        if "-c" not in argv:
            continue
        if not argv or argv[0] not in ("clang", "clang++"):
            raise ValueError(f"unexpected compiler on Make dry-run line {line_number}: {line}")
        compile_index = argv.index("-c")
        if compile_index + 1 >= len(argv):
            raise ValueError(f"compile command has no source on Make dry-run line {line_number}")
        source_path = (corpus_root / argv[compile_index + 1]).resolve()
        try:
            source = source_path.relative_to(corpus_root.resolve()).as_posix()
        except ValueError as error:
            raise ValueError(f"compile source escapes the pinned Wolf4SDL tree: {source_path}") from error
        if source not in expected:
            raise ValueError(f"Makefile emitted an unexpected source unit: {source}")
        if source in commands:
            raise ValueError(f"Makefile emitted more than one compile command for {source}")
        if "-o" not in argv or argv.index("-o") + 1 >= len(argv):
            raise ValueError(f"compile command for {source} has no object output")
        if source.endswith(".c"):
            if argv[0] != "clang" or argv.count("-std=gnu99") != 1:
                raise ValueError(f"C unit {source} does not retain the Makefile's GNU99 context")
        elif argv[0] != "clang++" or any(flag.startswith("-std=") for flag in argv):
            raise ValueError(f"C++ unit {source} does not retain the Makefile's host-default language mode")
        object_path = argv[argv.index("-o") + 1]
        commands[source] = {
            "directory": str(corpus_root.resolve()),
            "file": str(source_path),
            "arguments": argv,
            "output": str((corpus_root / object_path).resolve()),
        }
    missing = [unit for unit in units if unit not in commands]
    if missing:
        raise ValueError("Make dry-run did not produce compile commands for: " + ", ".join(missing))
    return [commands[unit] for unit in units]


def under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def generate(output: Path, make: str = "make") -> tuple[Path, int]:
    output = Path(output).expanduser()
    provenance_candidate = output.with_name(output.stem + ".provenance.json")
    if output.is_symlink() or provenance_candidate.is_symlink():
        raise ValueError("refusing to replace a symlink output")
    output = output.resolve()
    if not under(output, BUILD_ROOT) or output == BUILD_ROOT.resolve():
        raise ValueError(f"output must be a file under {BUILD_ROOT}")
    provenance_path = output.with_name(output.stem + ".provenance.json")

    entry = pinned_wolf_entry()
    run(["pkg-config", "--exists", "sdl2", "SDL2_mixer"])
    package_versions = {
        package: run(["pkg-config", "--modversion", package]).strip()
        for package in entry["native"]["required_packages"]
    }
    for executable in ("clang", "clang++", make):
        if shutil.which(executable) is None:
            raise ValueError(f"required build tool is not on PATH: {executable}")

    make_environment = os.environ.copy()
    make_environment.pop("MAKEFLAGS", None)
    make_environment.pop("MFLAGS", None)
    make_argv = [
        make, "-B", "-n", "--no-print-directory", "CONFIG=config.default",
        "NO_DEPS=1", "Q=", "CC=clang", "CXX=clang++", "all",
    ]
    dry_run = run(make_argv, cwd=CORPUS, env=make_environment)
    commands = parse_make_dry_run(dry_run, CORPUS, entry["native"]["configured_source_units"])
    database = (json.dumps(commands, indent=2) + "\n").encode()
    tool_info = {}
    for executable in ("clang", "clang++"):
        resolved = shutil.which(executable)
        version = run([executable, "--version"]).splitlines()[0]
        target = run([executable, "-dumpmachine"]).strip()
        tool_info[executable] = {"path": str(Path(resolved).resolve()), "version": version, "target": target}
    make_path = shutil.which(make)
    make_info = {"path": str(Path(make_path).resolve()), "version": run([make, "--version"]).splitlines()[0]}
    pkg_config_path = shutil.which("pkg-config")
    pkg_config_info = {
        "path": str(Path(pkg_config_path).resolve()),
        "version": run(["pkg-config", "--version"]).strip(),
    }
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    identity = entry["source_identity"]
    provenance = {
        "schema_version": 1,
        "corpus_commit": identity["commit"],
        "makefile_sha256": sha256(MAKEFILE.read_bytes()),
        "config_sha256": sha256(CONFIG.read_bytes()),
        "compile_commands_sha256": sha256(database),
        "packages": package_versions,
        "tools": tool_info,
        "make": make_info,
        "pkg_config": pkg_config_info,
        "environment": {
            key: os.environ[key]
            for key in (
                "PKG_CONFIG_PATH", "PKG_CONFIG_LIBDIR", "PKG_CONFIG_SYSROOT_DIR",
                "CPATH", "C_INCLUDE_PATH", "CPLUS_INCLUDE_PATH", "OBJC_INCLUDE_PATH",
                "SDKROOT", "DEVELOPER_DIR", "MACOSX_DEPLOYMENT_TARGET",
            )
            if key in os.environ
        },
        "make_dry_run_argv": make_argv,
        "unit_count": len(commands),
        "manifest_schema_version": manifest["schema_version"],
    }
    atomic_write(output, database)
    atomic_write(provenance_path, (json.dumps(provenance, indent=2) + "\n").encode())
    return output, len(commands)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=BUILD_ROOT / "compile_commands.json")
    parser.add_argument("--make", default="make", help="Make executable (default: make)")
    arguments = parser.parse_args(argv)
    try:
        output, count = generate(arguments.output, arguments.make)
    except (ValueError, OSError, json.JSONDecodeError) as error:
        print(f"wolf compile database: {error}", file=sys.stderr)
        return 2
    print(f"wrote {count} pinned Wolf4SDL compile commands to {output}")
    print(f"provenance: {output.with_name(output.stem + '.provenance.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
