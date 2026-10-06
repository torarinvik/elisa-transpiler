#!/usr/bin/env python3
"""Emit reproducible input, translator, output, and compiler identities."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any


MANIFEST_SCHEMA = "elisa-transpiler-compiler-compatibility-v1"
REVISION_PATTERN = re.compile(r"[0-9a-f]{40}")
HASH_PATTERN = re.compile(r"[0-9a-f]{64}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_output_distinct(output_value: str | Path, protected_values: list[str | Path]) -> None:
    output_path = Path(output_value).resolve(strict=False)
    for protected_value in protected_values:
        if not str(protected_value):
            continue
        protected_path = Path(protected_value).resolve(strict=False)
        if output_path == protected_path:
            raise ValueError(
                "refusing to overwrite source, tool, manifest, or coverage input: "
                + str(protected_value)
            )


def resolve_executable(value: str) -> Path:
    candidate = Path(value)
    if os.sep in value or candidate.is_absolute():
        resolved = candidate.resolve(strict=True)
    else:
        located = shutil.which(value)
        if located is None:
            raise FileNotFoundError(f"translator executable not found: {value}")
        resolved = Path(located).resolve(strict=True)
    if not resolved.is_file():
        raise ValueError(f"translator is not a regular file: {resolved}")
    if not resolved.stat().st_mode & 0o111:
        raise PermissionError(f"translator is not executable: {resolved}")
    return resolved


def read_manifest(path: Path) -> tuple[str, dict[str, Any] | None, str | None]:
    if not path.exists():
        return "missing", None, None
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    try:
        manifest = json.loads(payload.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return "invalid", None, digest
    if not isinstance(manifest, dict) or manifest.get("schema") != MANIFEST_SCHEMA:
        return "invalid", None, digest
    if not valid_manifest_shape(manifest):
        return "invalid", None, digest
    return "valid", manifest, digest


def valid_manifest_shape(manifest: dict[str, Any]) -> bool:
    pair = manifest.get("compiler_pair")
    validation = manifest.get("translator_validation")
    if (
        not isinstance(manifest.get("target"), str)
        or not isinstance(pair, dict)
        or not isinstance(validation, dict)
        or not isinstance(validation.get("status"), str)
        or not isinstance(validation.get("current_translator_sources_verified"), bool)
        or not isinstance(validation.get("compiler_products_current"), bool)
    ):
        return False
    for stage in ("stage0", "stage1"):
        entry = pair.get(stage)
        executable = entry.get("executable") if isinstance(entry, dict) else None
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("source_revision"), str)
            or not REVISION_PATTERN.fullmatch(entry["source_revision"])
            or not isinstance(entry.get("source_worktree_clean"), bool)
            or not isinstance(entry.get("source_freshness_verified"), bool)
            or not isinstance(executable, dict)
            or not isinstance(executable.get("sha256"), str)
            or not HASH_PATTERN.fullmatch(executable["sha256"])
            or not isinstance(executable.get("artifact_source_revision"), str)
            or not REVISION_PATTERN.fullmatch(executable["artifact_source_revision"])
        ):
            return False
        if stage == "stage1":
            runtime = entry.get("runtime")
            if (
                not isinstance(runtime, dict)
                or not isinstance(runtime.get("sha256"), str)
                or not HASH_PATTERN.fullmatch(runtime["sha256"])
                or not isinstance(runtime.get("artifact_source_revision"), str)
                or not REVISION_PATTERN.fullmatch(runtime["artifact_source_revision"])
            ):
                return False
    return True


def source_revision(manifest: dict[str, Any], stage: str) -> str:
    pair = manifest.get("compiler_pair", {})
    entry = pair.get(stage, {}) if isinstance(pair, dict) else {}
    value = entry.get("source_revision") if isinstance(entry, dict) else None
    return json_value(value) if isinstance(value, str) and value else "unknown"


def product_freshness(manifest: dict[str, Any], stage: str) -> str:
    pair = manifest.get("compiler_pair", {})
    entry = pair.get(stage, {}) if isinstance(pair, dict) else {}
    if not isinstance(entry, dict):
        return "unknown"
    source = entry.get("source_revision")
    executable = entry.get("executable", {})
    executable_source = executable.get("artifact_source_revision") if isinstance(executable, dict) else None
    if not isinstance(source, str) or not isinstance(executable_source, str):
        return "unknown"
    fresh = (
        source == executable_source
        and entry.get("source_freshness_verified") is True
    )
    if stage == "stage1":
        runtime = entry.get("runtime", {})
        runtime_source = runtime.get("artifact_source_revision") if isinstance(runtime, dict) else None
        if not isinstance(runtime_source, str):
            return "unknown"
        fresh = (
            fresh
            and source == runtime_source
            and entry.get("source_freshness_verified") is True
        )
    return "true" if fresh else "false"


def manifest_field(manifest: dict[str, Any], section: str, name: str) -> str:
    pair = manifest.get("compiler_pair", {})
    entry = pair.get(section, {}) if isinstance(pair, dict) else {}
    value = entry.get(name) if isinstance(entry, dict) else None
    return json_value(value) if isinstance(value, (str, bool, int)) else "unknown"


def artifact_field(manifest: dict[str, Any], stage: str, artifact: str, name: str) -> str:
    pair = manifest.get("compiler_pair", {})
    entry = pair.get(stage, {}) if isinstance(pair, dict) else {}
    artifact_record = entry.get(artifact, {}) if isinstance(entry, dict) else {}
    value = artifact_record.get(name) if isinstance(artifact_record, dict) else None
    return json_value(value) if isinstance(value, (str, bool, int)) else "unknown"


def boolean_text(value: object) -> str:
    return str(value).lower() if isinstance(value, bool) else "unknown"


def json_value(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


def report(
    source: Path,
    output: Path,
    translator_value: str | Path,
    manifest_path: Path,
    expected_source_hash: str | None = None,
    expected_translator_hash: str | None = None,
) -> list[tuple[str, str]]:
    source_hash = sha256_file(source)
    if expected_source_hash is not None and source_hash != expected_source_hash:
        raise ValueError("source changed while translation was running")
    translator_argument = str(translator_value)
    if os.sep in translator_argument or Path(translator_argument).is_absolute():
        translator_invocation = Path(translator_argument).absolute()
    else:
        located_translator = shutil.which(translator_argument)
        if located_translator is None:
            raise FileNotFoundError(f"translator executable not found: {translator_argument}")
        translator_invocation = Path(located_translator).absolute()
    translator = resolve_executable(translator_argument)
    translator_hash = sha256_file(translator)
    if expected_translator_hash is not None and translator_hash != expected_translator_hash:
        raise ValueError("translator executable changed while translation was running")
    manifest_status, manifest, manifest_digest = read_manifest(manifest_path)
    fields = [
        ("provenance_schema", "elisa-quality-provenance-v1"),
        ("translation_mode", "single-file"),
        ("translator_arguments", json_value(["--dump-typed-ir", "--explain-rewrites"])),
        ("translator_argument", json_value(translator_argument)),
        ("typed_ir_schema", "typed-ir-v16"),
        ("source_path", json_value(str(source))),
        ("generated_elisa_path", json_value(str(output))),
        ("source_sha256", source_hash),
        ("generated_elisa_sha256", sha256_file(output)),
        ("translator_invocation_path", json_value(str(translator_invocation))),
        ("translator_resolved_path", json_value(str(translator))),
        ("translator_sha256", translator_hash),
        ("compiler_manifest_path", json_value(str(manifest_path.resolve()))),
        ("compiler_manifest_status", manifest_status),
        ("compiler_manifest_sha256", manifest_digest or "unavailable"),
    ]
    if manifest is None:
        fields.extend(
            [
                ("compiler_target", "unknown"),
                ("stage0_source_revision", "unknown"),
                ("stage0_source_worktree_clean", "unknown"),
                ("stage0_source_freshness_verified", "unknown"),
                ("stage0_executable_source_revision", "unknown"),
                ("stage0_executable_sha256", "unknown"),
                ("stage0_products_fresh", "unknown"),
                ("stage1_source_revision", "unknown"),
                ("stage1_source_worktree_clean", "unknown"),
                ("stage1_source_freshness_verified", "unknown"),
                ("stage1_executable_source_revision", "unknown"),
                ("stage1_executable_sha256", "unknown"),
                ("stage1_runtime_source_revision", "unknown"),
                ("stage1_runtime_sha256", "unknown"),
                ("stage1_products_fresh", "unknown"),
                ("translator_validation_status", "unknown"),
                ("translator_sources_verified", "unknown"),
                ("compiler_products_current", "unknown"),
            ]
        )
        return fields

    validation = manifest["translator_validation"]
    target = manifest.get("target")
    fields.extend(
        [
            ("compiler_target", json_value(target if isinstance(target, str) else "unknown")),
            ("stage0_source_revision", source_revision(manifest, "stage0")),
            (
                "stage0_source_worktree_clean",
                manifest_field(manifest, "stage0", "source_worktree_clean"),
            ),
            (
                "stage0_source_freshness_verified",
                manifest_field(manifest, "stage0", "source_freshness_verified"),
            ),
            (
                "stage0_executable_source_revision",
                artifact_field(manifest, "stage0", "executable", "artifact_source_revision"),
            ),
            (
                "stage0_executable_sha256",
                artifact_field(manifest, "stage0", "executable", "sha256"),
            ),
            ("stage0_products_fresh", product_freshness(manifest, "stage0")),
            ("stage1_source_revision", source_revision(manifest, "stage1")),
            (
                "stage1_source_worktree_clean",
                manifest_field(manifest, "stage1", "source_worktree_clean"),
            ),
            (
                "stage1_source_freshness_verified",
                manifest_field(manifest, "stage1", "source_freshness_verified"),
            ),
            (
                "stage1_executable_source_revision",
                artifact_field(manifest, "stage1", "executable", "artifact_source_revision"),
            ),
            (
                "stage1_executable_sha256",
                artifact_field(manifest, "stage1", "executable", "sha256"),
            ),
            (
                "stage1_runtime_source_revision",
                artifact_field(manifest, "stage1", "runtime", "artifact_source_revision"),
            ),
            (
                "stage1_runtime_sha256",
                artifact_field(manifest, "stage1", "runtime", "sha256"),
            ),
            ("stage1_products_fresh", product_freshness(manifest, "stage1")),
            (
                "translator_validation_status",
                json_value(validation["status"])
                if isinstance(validation.get("status"), str)
                else "unknown",
            ),
            (
                "translator_sources_verified",
                boolean_text(validation.get("current_translator_sources_verified")),
            ),
            (
                "compiler_products_current",
                boolean_text(validation.get("compiler_products_current")),
            ),
        ]
    )
    return fields


def main(argv: list[str]) -> int:
    if len(argv) == 3 and argv[1] == "--json-string":
        print(json_value(argv[2]))
        return 0
    if len(argv) >= 5 and argv[1] == "--check-output":
        try:
            assert_output_distinct(argv[2], argv[3:])
        except (OSError, ValueError) as error:
            print(f"quality provenance: {error}", file=sys.stderr)
            return 2
        return 0
    if len(argv) == 3 and argv[1] == "--hash-file":
        try:
            path = Path(argv[2]).resolve(strict=True)
            if not path.is_file():
                raise ValueError(f"not a regular file: {path}")
            print(sha256_file(path))
        except (OSError, ValueError) as error:
            print(f"quality provenance: {error}", file=sys.stderr)
            return 2
        return 0
    if len(argv) != 7:
        print(
            "usage: quality_provenance.py SOURCE GENERATED_ELISA TRANSLATOR "
            "COMPILER_MANIFEST SOURCE_SHA256 TRANSLATOR_SHA256\n"
            "       quality_provenance.py --json-string TEXT\n"
            "       quality_provenance.py --check-output OUTPUT PROTECTED_PATH...\n"
            "       quality_provenance.py --hash-file PATH",
            file=sys.stderr,
        )
        return 2
    try:
        source = Path(argv[1]).resolve(strict=True)
        output = Path(argv[2]).resolve(strict=True)
        manifest_path = Path(argv[4]).resolve()
        if not source.is_file() or not output.is_file():
            raise ValueError("source and generated Elisa paths must be regular files")
        for key, value in report(
            source,
            output,
            argv[3],
            manifest_path,
            argv[5],
            argv[6],
        ):
            print(f"{key}: {value}")
    except (OSError, ValueError, PermissionError) as error:
        print(f"quality provenance: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
