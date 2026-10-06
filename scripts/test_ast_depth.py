#!/usr/bin/env python3
"""Exercise bounded raw-Clang-JSON depth and deterministic mutation cases."""

from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Callable

from ast_json_minimize import minimize_ast_json


JSON_MAX_DEPTH = 256
PROJECTION_MUTATION_MAX_BYTES = 4096
PROJECTION_MUTATION_MAX_DEPTH = 32
MAX_SAVED_PROJECTION_REGRESSIONS = 64
SOURCE = "testdata/fixtures/simple.c"
GENERATED_PROJECTION_MUTATION_COUNT = 12
PROJECTION_REGRESSION_RELATIVE_DIR = Path("testdata/fixtures/ast_projection_regressions")


def generated_ast(nested_arrays: int) -> str:
    # Include the TranslationUnitDecl object in the total nesting depth.
    filler = "[" * nested_arrays + "0" + "]" * nested_arrays
    return (
        '{"kind":"TranslationUnitDecl","inner":[],"depthProbe":'
        + filler
        + "}"
    )


def run_case(
    transpiler: Path,
    fake_clang: Path,
    ast_path: Path,
    *options: str,
    timeout: int = 30,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PATH"] = str(fake_clang) + os.pathsep + environment.get("PATH", "")
    environment["ELISA_FAKE_CLANG_JSON"] = str(ast_path)
    return subprocess.run(
        [str(transpiler), *options, SOURCE],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def deterministic_ast_mutations() -> list[tuple[str, str, str]]:
    """Return bounded, replayable raw-JSON and root-schema failure seeds."""
    valid = '{"kind":"TranslationUnitDecl","inner":[],"probe":0}'
    malformed = [
        ("truncated_object", valid[:-1]),
        ("truncated_array", valid.replace("[]", "[", 1)),
        ("trailing_root", valid + "{}"),
        ("invalid_string_escape", valid.replace("TranslationUnitDecl", r"Translation\qUnitDecl", 1)),
        ("leading_zero_number", valid.replace('"probe":0', '"probe":01', 1)),
        ("incomplete_fraction", valid.replace('"probe":0', '"probe":1.', 1)),
        ("incomplete_exponent", valid.replace('"probe":0', '"probe":1e+', 1)),
        ("invalid_literal", valid.replace('"probe":0', '"probe":truX', 1)),
        ("missing_colon", valid.replace('"inner":[]', '"inner" []', 1)),
    ]

    def reject_nonstandard_constant(value: str) -> None:
        raise ValueError("non-standard JSON constant: " + value)

    for name, text in malformed:
        try:
            json.loads(text, parse_constant=reject_nonstandard_constant)
        except (json.JSONDecodeError, ValueError):
            continue
        raise AssertionError("AST mutation seed %s unexpectedly parses as JSON" % name)

    schema_invalid = [
        ("root_not_object", "[]", "root-not-object"),
        ("missing_root_kind", '{"inner":[]}', "missing-required-field:root.kind"),
        ("wrong_root_kind_type", '{"kind":1,"inner":[]}', "unsupported-root-kind"),
        (
            "missing_root_inner",
            '{"kind":"TranslationUnitDecl"}',
            "missing-required-field:root.inner",
        ),
        (
            "wrong_root_inner_type",
            '{"kind":"TranslationUnitDecl","inner":{}}',
            "missing-required-field:root.inner",
        ),
        (
            "duplicate_root_kind",
            '{"kind":"TranslationUnitDecl","kind":"FunctionDecl","inner":[]}',
            "duplicate-field:root.kind",
        ),
        (
            "duplicate_root_inner",
            '{"kind":"TranslationUnitDecl","inner":[],"inner":{}}',
            "duplicate-field:root.inner",
        ),
    ]
    return [
        (name, text, "Clang emitted invalid or over-depth AST JSON")
        for name, text in malformed
    ] + [
        (name, text, "Clang AST schema violation: " + issue)
        for name, text, issue in schema_invalid
    ]


def deterministic_projection_mutations() -> list[tuple[str, str]]:
    """Return fixed and generated valid-root variants that should project identically."""
    mutations = [
        (
            "nested_json_values",
            '{"kind":"TranslationUnitDecl","inner":[],"metadata":'
            '{"items":[null,true,false,0,-1.25,"escaped \\\" text",'
            '{"nested":[{"value":7},[]]}]}}',
        ),
        (
            "discarded_definition_metadata",
            '{"kind":"TranslationUnitDecl","inner":[],"metadata":'
            '{"definitionData":{"isPass":true},"loc":{"offset":8},'
            '"range":{"begin":{"offset":1},"end":{"offset":2}}}}',
        ),
        (
            "macro_origin_location_retention",
            '{"kind":"TranslationUnitDecl","inner":[],"metadata":'
            '{"kind":"NoiseDecl","loc":{"spellingLoc":{"offset":4}}}}',
        ),
    ]

    nested_object: object = "leaf"
    for index in range(8):
        nested_object = {"level_%d" % index: nested_object}
    generated_values = [
        ("null", None),
        ("booleans", [True, False]),
        ("integer_edges", [0, -1, (1 << 63) - 1]),
        ("fractional_exponents", [1.25e-15, -0.0]),
        ("empty_containers", {"array": [], "object": {}}),
        ("escaped_unicode", 'quotes: "\\; Unicode: café ☕ 🦊'),
        ("utf8_scalar_boundaries", "\u0080\u07ff\u0800\ud7ff\ue000\uffff\U00010000\U0010ffff"),
        ("nested_object", nested_object),
        ("wide_array", list(range(32))),
    ]
    for name, value in generated_values:
        root = {
            "kind": "TranslationUnitDecl",
            "inner": [],
            "generatedNoise": value,
        }
        mutations.append(
            (
                "generated_" + name,
                json.dumps(root, ensure_ascii=False, separators=(",", ":")),
            )
        )
    for regression_path in projection_regression_paths():
        if regression_path.stat().st_size > PROJECTION_MUTATION_MAX_BYTES:
            raise ValueError("saved AST projection regression exceeds byte cap: %s" % regression_path)
        mutations.append(
            ("saved_" + regression_path.stem, regression_path.read_text(encoding="utf-8"))
        )
    return mutations


def json_nesting_depth(value: object) -> int:
    """Return container nesting depth for a decoded JSON value."""
    if isinstance(value, dict):
        return 1 + max(
            (json_nesting_depth(child) for child in value.values()), default=0
        )
    if isinstance(value, list):
        return 1 + max((json_nesting_depth(child) for child in value), default=0)
    return 0


def raw_utf8_scalar_cases() -> tuple[list[tuple[str, bytes]], list[tuple[str, bytes]]]:
    """Return UTF-8 boundary and malformed-sequence JSON regression seeds."""
    prefix = b'{"kind":"TranslationUnitDecl","inner":[],"ignored":"'
    suffix = b'"}'
    valid_scalars = [
        ("two_byte_minimum", b"\xc2\x80"),
        ("two_byte_maximum", b"\xdf\xbf"),
        ("three_byte_minimum", b"\xe0\xa0\x80"),
        ("before_surrogate_range", b"\xed\x9f\xbf"),
        ("after_surrogate_range", b"\xee\x80\x80"),
        ("three_byte_maximum", b"\xef\xbf\xbf"),
        ("four_byte_minimum", b"\xf0\x90\x80\x80"),
        ("four_byte_maximum", b"\xf4\x8f\xbf\xbf"),
    ]
    invalid_scalars = [
        ("isolated_continuation", b"\x80"),
        ("isolated_final_continuation", b"\xbf"),
        ("overlong_two_byte", b"\xc0\xaf"),
        ("invalid_two_byte_lead", b"\xc1\xbf"),
        ("invalid_two_byte_continuation", b"\xc2 "),
        ("overlong_three_byte", b"\xe0\x80\x80"),
        ("invalid_three_byte_continuation", b"\xe1\x80 "),
        ("surrogate", b"\xed\xa0\x80"),
        ("overlong_four_byte", b"\xf0\x80\x80\x80"),
        ("invalid_four_byte_continuation", b"\xf1\x80\x80 "),
        ("out_of_range", b"\xf4\x90\x80\x80"),
        ("invalid_lead_f5", b"\xf5\x80\x80\x80"),
        ("invalid_lead_ff", b"\xff"),
        ("truncated_two_byte", b"\xc2"),
        ("truncated_three_byte", b"\xe2\x82"),
        ("truncated_four_byte", b"\xf0\x90\x80"),
    ]
    return (
        [(name, prefix + scalar + suffix) for name, scalar in valid_scalars],
        [(name, prefix + scalar + suffix) for name, scalar in invalid_scalars],
    )


ROOT = Path(__file__).resolve().parents[1]


def projection_regression_paths() -> list[Path]:
    directory = ROOT / PROJECTION_REGRESSION_RELATIVE_DIR
    if not directory.is_dir():
        return []
    paths = sorted(directory.glob("*.json"))
    if len(paths) > MAX_SAVED_PROJECTION_REGRESSIONS:
        raise ValueError("saved projection regression count exceeds the configured cap")
    return paths


def save_projection_regression(directory: Path, name: str, value: object) -> Path:
    """Persist a compact minimized AST without overwriting an existing seed."""
    if (
        not isinstance(value, dict)
        or value.get("kind") != "TranslationUnitDecl"
        or not isinstance(value.get("inner"), list)
    ):
        raise ValueError("saved projection regression must preserve the TranslationUnitDecl envelope")
    payload = (
        json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
        + "\n"
    ).encode("ascii")
    if len(payload) > PROJECTION_MUTATION_MAX_BYTES:
        raise ValueError("saved projection regression exceeds the byte budget")
    if json_nesting_depth(value) > PROJECTION_MUTATION_MAX_DEPTH:
        raise ValueError("saved projection regression exceeds the depth budget")
    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_-") or "ast"
    digest = hashlib.sha256(payload).hexdigest()[:16]
    destination = directory / (safe_name + "-" + digest + ".json")
    directory.mkdir(parents=True, exist_ok=True)
    if (
        not destination.exists()
        and len(list(directory.glob("*.json"))) >= MAX_SAVED_PROJECTION_REGRESSIONS
    ):
        raise ValueError("saved projection regression count exceeds the configured cap")
    try:
        with destination.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        if destination.read_bytes() != payload:
            raise RuntimeError("AST regression hash collision at " + str(destination))
    return destination


def minimize_and_persist_projection_mismatch(
    name: str,
    original_ast: object,
    preserves_mismatch: Callable[[object], bool],
    directory: Path,
    *,
    max_probes: int = 8,
    max_candidates: int = 64,
) -> tuple[object, int, Path | None]:
    """Save only a reduced AST that a bounded oracle probe confirmed."""
    confirmed_candidates: set[str] = set()

    def tracked_predicate(candidate: object) -> bool:
        confirmed = preserves_mismatch(candidate)
        if confirmed:
            confirmed_candidates.add(
                json.dumps(
                    candidate,
                    ensure_ascii=True,
                    allow_nan=False,
                    separators=(",", ":"),
                )
            )
        return confirmed

    minimized_ast, probes = minimize_ast_json(
        original_ast,
        tracked_predicate,
        max_probes=max_probes,
        max_candidates=max_candidates,
    )
    minimized_key = json.dumps(
        minimized_ast,
        ensure_ascii=True,
        allow_nan=False,
        separators=(",", ":"),
    )
    if minimized_key not in confirmed_candidates:
        return minimized_ast, probes, None
    return minimized_ast, probes, save_projection_regression(
        directory, name, minimized_ast
    )


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        seeds = deterministic_ast_mutations()
        if len(seeds) != 16:
            raise AssertionError("expected nine malformed JSON seeds and seven schema seeds")
        schema_seeds = [
            (name, text)
            for name, text, expected_error in seeds
            if expected_error.startswith("Clang AST schema violation: ")
        ]
        if len(schema_seeds) != 7:
            raise AssertionError("expected seven schema-invalid AST roots")
        for _, text in schema_seeds:
            json.loads(text)
        projection_seeds = deterministic_projection_mutations()
        saved_projection_count = len(projection_regression_paths())
        expected_projection_count = GENERATED_PROJECTION_MUTATION_COUNT + saved_projection_count
        if len(projection_seeds) != expected_projection_count:
            raise AssertionError("projection seed count does not match fixed/generated and saved regressions")
        if deterministic_projection_mutations() != projection_seeds:
            raise AssertionError("projection mutation generator is not deterministic")
        for _, text in projection_seeds:
            parsed = json.loads(text)
            if parsed.get("kind") != "TranslationUnitDecl" or not isinstance(parsed.get("inner"), list):
                raise AssertionError("projection seed violates the valid root envelope")
            if len(text.encode("utf-8")) > PROJECTION_MUTATION_MAX_BYTES:
                raise AssertionError("projection seed exceeds the generated byte budget")
            if json_nesting_depth(parsed) > PROJECTION_MUTATION_MAX_DEPTH:
                raise AssertionError("projection seed exceeds the generated depth budget")
        valid_utf8, invalid_utf8 = raw_utf8_scalar_cases()
        if len(valid_utf8) != 8 or len(invalid_utf8) != 16:
            raise AssertionError("expected eight UTF-8 scalar-boundary and sixteen malformed-sequence seeds")
        for name, payload in valid_utf8:
            try:
                parsed = json.loads(payload.decode("utf-8", "strict"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise AssertionError("valid UTF-8 AST seed %s was rejected" % name) from error
            if parsed.get("kind") != "TranslationUnitDecl":
                raise AssertionError("valid UTF-8 AST seed %s lost its root envelope" % name)
        for name, payload in invalid_utf8:
            try:
                decoded = payload.decode("utf-8", "strict")
                json.loads(decoded)
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                continue
            raise AssertionError("invalid UTF-8 AST seed %s unexpectedly parses" % name)
        oversized_json = (
            '{"kind":"TranslationUnitDecl","inner":[],"padding":"'
            + ("x" * 4096)
            + '"}'
        )
        if len(oversized_json.encode("utf-8")) <= 512:
            raise AssertionError("oversized AST seed does not exceed the configured cap")
        json.loads(oversized_json)
        print(
            "AST mutation corpus OK (9 malformed, 7 root-schema, "
            "%d bounded projection-preserving including %d saved regressions, "
            "%d valid/%d invalid UTF-8 seeds)"
            % (len(projection_seeds), saved_projection_count, len(valid_utf8), len(invalid_utf8))
        )
        return 0

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

    fake_clang = ROOT / "testdata/fake_tools"
    with tempfile.TemporaryDirectory(prefix="elisa-ast-depth-") as temporary_directory:
        temporary_root = Path(temporary_directory)
        at_limit_path = temporary_root / "at-limit.json"
        over_limit_path = temporary_root / "over-limit.json"
        at_limit_path.write_text(generated_ast(JSON_MAX_DEPTH - 1), encoding="utf-8")
        over_limit_path.write_text(generated_ast(JSON_MAX_DEPTH), encoding="utf-8")

        at_limit = run_case(transpiler, fake_clang, at_limit_path)
        if at_limit.returncode != 0:
            print("AST at JSON_MAX_DEPTH was rejected", file=sys.stderr)
            print(at_limit.stderr, end="", file=sys.stderr)
            return 1

        baseline_path = temporary_root / "empty-translation-unit.json"
        baseline_path.write_text(
            '{"kind":"TranslationUnitDecl","inner":[]}', encoding="utf-8"
        )
        baseline = run_case(transpiler, fake_clang, baseline_path)
        if baseline.returncode != 0 or not baseline.stdout:
            print("empty translation-unit projection failed", file=sys.stderr)
            print(baseline.stderr, end="", file=sys.stderr)
            return 1

        for name, mutated_json in deterministic_projection_mutations():
            ast_path = temporary_root / (name + ".json")
            ast_path.write_text(mutated_json, encoding="utf-8")
            result = run_case(transpiler, fake_clang, ast_path, timeout=10)
            if result.returncode != 0 or result.stdout != baseline.stdout:
                if result.returncode == 0 and result.stdout != baseline.stdout:
                    original_ast = json.loads(mutated_json)

                    def preserves_projection_mismatch(candidate: object) -> bool:
                        ast_path.write_text(
                            json.dumps(candidate, ensure_ascii=True, separators=(",", ":")),
                            encoding="utf-8",
                        )
                        try:
                            probe = run_case(
                                transpiler, fake_clang, ast_path, timeout=2
                            )
                        except subprocess.TimeoutExpired:
                            return False
                        return (
                            probe.returncode == 0
                            and probe.stdout != baseline.stdout
                        )

                    try:
                        minimized_ast, probes, regression_path = (
                            minimize_and_persist_projection_mismatch(
                                name,
                                original_ast,
                                preserves_projection_mismatch,
                                ROOT / PROJECTION_REGRESSION_RELATIVE_DIR,
                                max_probes=8,
                                max_candidates=64,
                            )
                        )
                    except (OSError, RuntimeError, ValueError) as error:
                        print(
                            "could not minimize/persist AST regression: %s" % error,
                            file=sys.stderr,
                        )
                        minimized_ast, probes, regression_path = original_ast, 0, None
                    print(
                        "minimized projection-mismatch AST after %d probes: %s"
                        % (
                            probes,
                            json.dumps(
                                minimized_ast,
                                ensure_ascii=True,
                                separators=(",", ":"),
                            ),
                        ),
                        file=sys.stderr,
                    )
                    if regression_path is not None:
                        print(
                            "saved minimized AST regression: %s"
                            % regression_path.relative_to(ROOT),
                            file=sys.stderr,
                        )
                    else:
                        print(
                            "minimized AST was not confirmed by its bounded probes; no regression saved",
                            file=sys.stderr,
                        )
                print(
                    "valid AST projection mutation %s changed output or failed" % name,
                    file=sys.stderr,
                )
                print(result.stderr[:2000], end="", file=sys.stderr)
                return 1

        over_limit = run_case(transpiler, fake_clang, over_limit_path)
        expected_diagnostic = (
            "Clang emitted invalid or over-depth AST JSON while processing " + SOURCE
        )
        if (
            over_limit.returncode == 0
            or over_limit.stdout
            or expected_diagnostic not in over_limit.stderr
        ):
            print("over-depth AST was not rejected without partial output", file=sys.stderr)
            print(over_limit.stderr, end="", file=sys.stderr)
            return 1

        for name, mutated_json, expected_error in deterministic_ast_mutations():
            ast_path = temporary_root / (name + ".json")
            ast_path.write_text(mutated_json, encoding="utf-8")
            result = run_case(transpiler, fake_clang, ast_path, timeout=10)
            if (
                result.returncode == 0
                or result.stdout
                or expected_error not in result.stderr
            ):
                print("AST mutation %s was accepted or produced an unexpected failure" % name, file=sys.stderr)
                print(result.stderr[:2000], end="", file=sys.stderr)
                return 1

        oversized_path = temporary_root / "oversized-valid.json"
        oversized_json = (
            '{"kind":"TranslationUnitDecl","inner":[],"padding":"'
            + ("x" * 4096)
            + '"}'
        )
        oversized_path.write_text(oversized_json, encoding="utf-8")
        oversized = run_case(
            transpiler,
            fake_clang,
            oversized_path,
            "--max-frontend-output-bytes",
            "512",
            timeout=10,
        )
        if (
            oversized.returncode == 0
            or oversized.stdout
            or "exceeded --max-frontend-output-bytes" not in oversized.stderr
        ):
            print("oversized AST did not fail at the configured output cap", file=sys.stderr)
            print(oversized.stderr[:2000], end="", file=sys.stderr)
            return 1

    print(
        "AST robustness checks OK (depth boundary, 16 invalid and 3 "
        "projection-preserving mutations, byte cap)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
