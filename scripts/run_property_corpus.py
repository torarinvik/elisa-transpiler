#!/usr/bin/env python3
"""Run generated property C programs through the bounded differential runner."""

from __future__ import annotations

import argparse
import hashlib
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import run_fixture_manifest
from property_corpus import MAX_SEED, generate_programs


DEFAULT_MAX_RSS_KB = 1_572_864
DEFAULT_TIMEOUT_SECONDS = 90.0
DEFAULT_OUTPUT_BYTES = 64 * 1024 * 1024
RUN_ARTIFACT_SCHEMA = "elisa-property-run-v1"

FAMILY_BY_PROGRAM = {
    "integer_operations": ["integer_semantics", "expressions", "runtime_parity"],
    "pointers": ["pointers", "qualifiers", "runtime_parity"],
    "aggregates": ["records", "initialization", "runtime_parity"],
    "sequencing": ["evaluation_order", "operators", "runtime_parity"],
    "control_flow": ["control_flow", "runtime_parity"],
}


def build_manifest_case(
    program, source: Path, seed: int, native_compiler: str = "clang"
) -> dict[str, object]:
    """Describe one generated source using the canonical fixture-runner stages."""
    return {
        "name": "property_%s_seed_%d" % (program.family, seed),
        "source": str(source.resolve()),
        "translate_argv": ["{translator}", "{source}"],
        "native_build_argv": [native_compiler, "-std=c11", "{source}", "-o", "{native}"],
        "elisa_compile_argv": [
            "{elisa_bin}", "-emit", "obj", "-O0", "-o", "{object}", "{generated}"
        ],
        "elisa_link_argv": [
            native_compiler, "-Wl,-dead_strip", "-o", "{elisa_executable}", "{object}"
        ],
        "native_run_argv": ["{native}"],
        "elisa_run_argv": ["{elisa_executable}"],
        "expected_exit_code": 0,
        "compare": ["stdout", "stderr", "exit_code"],
        "capture_files": [
            "{source}", "{generated}", "{native}", "{object}", "{elisa_executable}"
        ],
    }


def persist_content_addressed_source(path: Path, content: bytes) -> None:
    """Publish an immutable source snapshot without exposing partial writes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != content:
            raise RuntimeError("content-addressed property source does not match: %s" % path)
        return

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix="." + path.name + ".", suffix=".tmp",
            dir=path.parent, delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())

        # A hard-link publishes the fully written inode atomically and fails
        # rather than replacing a file another run (or the user) created.
        try:
            os.link(temporary_path, path)
        except FileExistsError:
            if path.read_bytes() != content:
                raise RuntimeError(
                    "content-addressed property source does not match: %s" % path
                )
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def run_toolchain_digest(
    translator: Path,
    elisa_compiler: Path,
    elisa_runtime: Path | None,
    native_compiler: Path | None = None,
) -> str:
    """Separate preserved run artifacts whenever an executable changes."""
    digest = hashlib.sha256()

    def add_identity(role: str, path: Path | None) -> None:
        digest.update(role.encode("utf-8"))
        digest.update(b"\0")
        if path is None:
            digest.update(b"absent\0")
            return
        resolved = path.resolve(strict=True)
        if not resolved.is_file():
            raise ValueError("run tool is not a regular file: %s" % resolved)
        digest.update(str(resolved).encode("utf-8", "surrogateescape"))
        digest.update(b"\0")
        file_digest = hashlib.sha256()
        with resolved.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                file_digest.update(chunk)
        digest.update(file_digest.hexdigest().encode("ascii"))
        digest.update(b"\0")

    digest.update(RUN_ARTIFACT_SCHEMA.encode("ascii"))
    digest.update(b"\0")
    add_identity("translator", translator)
    add_identity("elisa-compiler", elisa_compiler)
    add_identity("elisa-runtime", elisa_runtime)
    if native_compiler is None:
        native_compiler_command = shutil.which("clang")
        native_compiler = Path(native_compiler_command) if native_compiler_command else None
    add_identity("native-compiler", native_compiler)
    # These argv profiles define how each tool is used. Bump the schema if the
    # fixed property-run commands or target options change.
    digest.update(b"c11-native-and-O0-elisa\0")
    return digest.hexdigest()


def run_seed(
    *,
    seed: int,
    translator: Path,
    elisa_compiler: Path,
    elisa_runtime: Path | None,
    output_dir: Path,
    max_rss_kb: int,
    timeout_seconds: float,
    max_output_bytes: int,
    min_system_free_percent: int | None,
) -> tuple[int, int]:
    """Run all generated programs serially, preserving runner diagnostics/artifacts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    programs = generate_programs(seed)
    corpus_digest = hashlib.sha256()
    for program in programs:
        corpus_digest.update(program.family.encode("ascii"))
        corpus_digest.update(b"\0")
        corpus_digest.update(program.source.encode("utf-8"))
        corpus_digest.update(b"\0")
    corpus_key = "seed-%d-%s" % (seed, corpus_digest.hexdigest()[:16])
    native_compiler = shutil.which("clang")
    if native_compiler is None:
        raise FileNotFoundError("native Clang compiler not found on PATH")
    native_compiler_path = Path(native_compiler).resolve(strict=True)
    toolchain_key = run_toolchain_digest(
        translator, elisa_compiler, elisa_runtime, native_compiler_path
    )
    source_dir = output_dir / "sources" / corpus_key
    run_output_dir = output_dir / "runs" / (corpus_key + "-tools-" + toolchain_key)
    source_dir.mkdir(parents=True, exist_ok=True)

    arguments = SimpleNamespace(
        output_dir=run_output_dir,
        translator=str(translator.resolve()),
        elisa_compiler=str(elisa_compiler.resolve()),
        elisa_runtime=str(elisa_runtime.resolve()) if elisa_runtime else "",
        timeout_seconds=None,
        default_timeout_seconds=timeout_seconds,
        max_rss_kb=max_rss_kb,
        max_output_bytes=max_output_bytes,
        min_system_free_percent=min_system_free_percent,
        system_memory_poll_seconds=1.0,
    )

    passed = 0
    failed = 0
    for program in programs:
        source = source_dir / (program.family + ".c")
        source_bytes = program.source.encode("utf-8")
        persist_content_addressed_source(source, source_bytes)
        case = build_manifest_case(program, source, seed, str(native_compiler_path))
        result = run_fixture_manifest.run_case(
            case,
            arguments,
            FAMILY_BY_PROGRAM[program.family],
        )
        if result["status"] == "passed":
            passed += 1
        else:
            failed += 1
    return passed, failed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--translator", required=True, type=Path)
    parser.add_argument("--elisa-compiler", required=True, type=Path)
    parser.add_argument(
        "--elisa-runtime",
        type=Path,
        default=os.environ.get("ELISA_PROPERTY_CORPUS_RUNTIME") or None,
    )
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--output-dir", type=Path, default=Path("build/property-corpus"))
    parser.add_argument(
        "--max-rss-kb",
        type=int,
        default=os.environ.get("ELISA_FIXTURE_PROCESS_MAX_RSS_KB", str(DEFAULT_MAX_RSS_KB)),
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=os.environ.get(
            "ELISA_PROPERTY_CORPUS_STAGE_TIMEOUT_SECONDS",
            str(DEFAULT_TIMEOUT_SECONDS),
        ),
    )
    parser.add_argument(
        "--max-output-bytes",
        type=int,
        default=os.environ.get(
            "ELISA_FIXTURE_PROCESS_MAX_OUTPUT_BYTES", str(DEFAULT_OUTPUT_BYTES)
        ),
    )
    parser.add_argument(
        "--min-system-free-percent",
        type=int,
        default=int(os.environ.get("ELISA_SETUP_MIN_SYSTEM_FREE_PERCENT", "60"))
        if sys.platform == "darwin"
        else None,
    )
    args = parser.parse_args()

    if not 0 <= args.seed <= MAX_SEED:
        parser.error("--seed must be in the unsigned 32-bit range")
    if (
        args.max_rss_kb <= 0
        or args.max_output_bytes <= 0
        or not math.isfinite(args.timeout_seconds)
        or args.timeout_seconds <= 0
    ):
        parser.error("resource limits and timeout must be positive")
    if args.min_system_free_percent is not None and not 0 <= args.min_system_free_percent <= 100:
        parser.error("--min-system-free-percent must be between 0 and 100")

    translator = args.translator.expanduser()
    elisa_compiler = args.elisa_compiler.expanduser()
    if not translator.is_absolute():
        translator = ROOT / translator
    if not elisa_compiler.is_absolute():
        elisa_compiler = ROOT / elisa_compiler
    if not translator.is_file() or not os.access(translator, os.X_OK):
        parser.error("translator is missing or not executable: %s" % translator)
    if not elisa_compiler.is_file() or not os.access(elisa_compiler, os.X_OK):
        parser.error("Elisa compiler is missing or not executable: %s" % elisa_compiler)

    runtime = args.elisa_runtime.expanduser() if args.elisa_runtime else None
    if runtime and not runtime.is_absolute():
        runtime = ROOT / runtime
    if runtime and not runtime.is_file():
        parser.error("Elisa runtime object does not exist: %s" % runtime)

    output_dir = args.output_dir.expanduser()
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    passed, failed = run_seed(
        seed=args.seed,
        translator=translator,
        elisa_compiler=elisa_compiler,
        elisa_runtime=runtime,
        output_dir=output_dir,
        max_rss_kb=args.max_rss_kb,
        timeout_seconds=args.timeout_seconds,
        max_output_bytes=args.max_output_bytes,
        min_system_free_percent=args.min_system_free_percent,
    )
    print("property corpus summary: passed=%d failed=%d" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
