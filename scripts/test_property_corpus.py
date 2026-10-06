#!/usr/bin/env python3
"""Compiler-free tests for the bounded C property-program generator."""

from __future__ import annotations

import unittest
from pathlib import Path
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from property_corpus import BUILDERS, MAX_CASES, MAX_SEED, MAX_SOURCE_BYTES, generate_programs
import run_fixture_manifest
from run_property_corpus import (
    FAMILY_BY_PROGRAM,
    build_manifest_case,
    persist_content_addressed_source,
    run_toolchain_digest,
    run_seed,
)


def _integer_declaration(source: str, name: str) -> int:
    match = re.search(
        r"\b(?:int32_t|int)\s+" + re.escape(name) + r"\s*=\s*(-?\d+)\s*;",
        source,
    )
    if match is None:
        raise AssertionError("missing integer declaration for " + name)
    return int(match.group(1))


def _uint32_declaration(source: str, name: str) -> int:
    match = re.search(r"\buint32_t\s+" + re.escape(name) + r"\s*=\s*(\d+)u\s*;", source)
    if match is None:
        raise AssertionError("missing uint32_t declaration for " + name)
    return int(match.group(1))


class PropertyCorpusTests(unittest.TestCase):
    @staticmethod
    def write_executable(path: Path, text: str) -> Path:
        path.write_text("#!/bin/sh\n" + text + "\n", encoding="utf-8")
        path.chmod(0o755)
        return path

    def test_content_addressed_source_publication_is_atomic_under_racing_writers(self):
        content = b"int main(void) { return 0; }\n"
        with tempfile.TemporaryDirectory(prefix="property-source-race-") as temporary:
            destination = Path(temporary) / "snapshot.c"
            with ThreadPoolExecutor(max_workers=8) as workers:
                futures = [
                    workers.submit(persist_content_addressed_source, destination, content)
                    for _ in range(32)
                ]
                for future in futures:
                    future.result()
            self.assertEqual(destination.read_bytes(), content)
            self.assertEqual(sorted(path.name for path in destination.parent.iterdir()), [
                "snapshot.c",
            ])

    def test_content_addressed_source_collision_preserves_existing_bytes(self):
        with tempfile.TemporaryDirectory(prefix="property-source-collision-") as temporary:
            destination = Path(temporary) / "snapshot.c"
            original = b"user or previous-run data\n"
            destination.write_bytes(original)
            with self.assertRaisesRegex(RuntimeError, "does not match"):
                persist_content_addressed_source(destination, b"different source\n")
            self.assertEqual(destination.read_bytes(), original)

    def test_run_artifact_namespace_changes_with_tool_identity(self):
        with tempfile.TemporaryDirectory(prefix="property-toolchain-key-") as temporary:
            root = Path(temporary)
            translator = self.write_executable(root / "translator", "exit 0")
            compiler_a = self.write_executable(root / "elisac-a", "exit 0")
            compiler_b = self.write_executable(root / "elisac-b", "exit 0")
            first = run_toolchain_digest(translator, compiler_a, None)
            same = run_toolchain_digest(translator, compiler_a, None)
            changed = run_toolchain_digest(translator, compiler_b, None)
            self.assertEqual(first, same)
            self.assertNotEqual(first, changed)
            self.write_executable(compiler_a, "exit 1")
            self.assertNotEqual(first, run_toolchain_digest(translator, compiler_a, None))

    def test_generates_each_required_semantic_family_deterministically(self):
        expected = (
            "integer_operations",
            "pointers",
            "aggregates",
            "sequencing",
            "control_flow",
        )
        first = generate_programs(1729)
        second = generate_programs(1729)
        self.assertEqual(tuple(program.family for program in first), expected)
        self.assertEqual(first, second)
        self.assertEqual(len(first), MAX_CASES)

    def test_each_program_is_bounded_and_standalone(self):
        for seed in (0, 1, 1729, MAX_SEED):
            with self.subTest(seed=seed):
                programs = generate_programs(seed)
                for program in programs:
                    self.assertLessEqual(
                        len(program.source.encode("utf-8")), MAX_SOURCE_BYTES
                    )
                    self.assertEqual(program.source.count("int main(void)"), 1)
                    self.assertTrue(program.source.rstrip().endswith("}"))
                    self.assertIn("? 0 : 1;", program.source)

    def test_fixed_program_and_byte_budgets_hold_across_seed_sample(self):
        expected_families = tuple(name for name, _ in BUILDERS)
        for seed in tuple(range(256)) + (MAX_SEED,):
            with self.subTest(seed=seed):
                programs = generate_programs(seed)
                self.assertEqual(len(programs), MAX_CASES)
                self.assertEqual(
                    tuple(program.family for program in programs), expected_families
                )
                self.assertTrue(
                    all(
                        len(program.source.encode("utf-8")) <= MAX_SOURCE_BYTES
                        for program in programs
                    )
                )
                for program in programs:
                    with self.subTest(seed=seed, family=program.family):
                        self.assert_generated_operations_stay_defined(program)

    def assert_generated_operations_stay_defined(self, program):
        source = program.source
        int_max = (1 << 31) - 1

        if program.family == "integer_operations":
            self.assertIn("#include <stdint.h>", source)
            for name in ("left", "right", "shift_base"):
                self.assertRegex(
                    source,
                    r"\bint32_t\s+" + re.escape(name) + r"\s*=\s*-?\d+;",
                )
            left = _integer_declaration(source, "left")
            right = _integer_declaration(source, "right")
            shift_base = _integer_declaration(source, "shift_base")
            shift_amount = _integer_declaration(source, "shift_amount")
            self.assertTrue(1 <= left <= 1000)
            self.assertTrue(1 <= right <= 1000)
            self.assertLessEqual(left * right, int_max)
            self.assertEqual(left + 0, left)
            self.assertEqual(0 + left, left)
            self.assertEqual(left * 1, left)
            self.assertEqual(1 * left, left)
            self.assertEqual(left // 1, left)
            self.assertEqual(left | 0, left)
            self.assertEqual(0 | left, left)
            self.assertEqual(left ^ 0, left)
            self.assertEqual(0 ^ left, left)
            self.assertTrue(1 <= shift_base <= 31)
            self.assertTrue(0 <= shift_amount <= 4)
            self.assertLessEqual(shift_base << shift_amount, int_max)
            self.assertNotIn("<< -", source)
            for identity in (
                "left + 0 == left",
                "0 + left == left",
                "left * 1 == left",
                "1 * left == left",
                "left / 1 == left",
                "(left | 0) == left",
                "(0 | left) == left",
                "(left ^ 0) == left",
                "(0 ^ left) == left",
                "(unsigned_left << 0) == unsigned_left",
                "(unsigned_left >> 0) == unsigned_left",
            ):
                self.assertIn(identity, source)
            unsigned_left = _uint32_declaration(source, "unsigned_left")
            unsigned_right = _uint32_declaration(source, "unsigned_right")
            unsigned_shift = _integer_declaration(source, "unsigned_shift")
            self.assertTrue(1 <= unsigned_right <= 1000)
            self.assertGreaterEqual(unsigned_left, 0x100000000 - unsigned_right)
            self.assertLessEqual(unsigned_left, 0xFFFFFFFF)
            self.assertGreater(unsigned_left + unsigned_right, 0xFFFFFFFF)
            self.assertTrue(0 <= unsigned_shift < 32)
            expected_unsigned_sum = (unsigned_left + unsigned_right) & 0xFFFFFFFF
            self.assertIn(
                "uint32_t unsigned_sum = unsigned_left + unsigned_right;",
                source,
            )
            self.assertIn(
                "unsigned_sum == %du" % expected_unsigned_sum,
                source,
            )
            self.assertIn(
                "(unsigned_left >> unsigned_shift) == %du"
                % (unsigned_left >> unsigned_shift),
                source,
            )
            self.assertIn(
                "(unsigned_left & unsigned_right) == %du"
                % (unsigned_left & unsigned_right),
                source,
            )
            return

        if program.family == "pointers":
            match = re.search(
                r"int values\[(\d+)\] = \{([^}]*)\};", source
            )
            self.assertIsNotNone(match)
            length = int(match.group(1))
            values = [int(value.strip()) for value in match.group(2).split(",")]
            offset_match = re.search(r"int \*cursor = values \+ (\d+);", source)
            step_match = re.search(r"\*\(cursor \+ (\d+)\)", source)
            self.assertIsNotNone(offset_match)
            self.assertIsNotNone(step_match)
            offset = int(offset_match.group(1))
            step = int(step_match.group(1))
            self.assertEqual(len(values), length)
            self.assertTrue(all(1 <= value <= 100 for value in values))
            self.assertTrue(0 <= offset < length)
            self.assertTrue(1 <= step and offset + step < length)
            self.assertIn(
                "readonly_values[%d] == %d" % (offset + step, values[offset + step]),
                source,
            )
            self.assertIn(
                "values + %d == readonly_values + %d" % (length, length), source
            )
            return

        if program.family == "aggregates":
            match = re.search(r"Sample initial = \{(-?\d+), (-?\d+), (-?\d+)\};", source)
            self.assertIsNotNone(match)
            self.assertTrue(all(-100 <= int(value) <= 100 for value in match.groups()))
            self.assertIn("Sample copied = initial;", source)
            return

        if program.family == "sequencing":
            start = _integer_declaration(source, "counter")
            delta_match = re.search(r"counter \+= (-?\d+);", source)
            self.assertIsNotNone(delta_match)
            delta = int(delta_match.group(1))
            self.assertTrue(1 <= start <= 100)
            self.assertTrue(-100 <= delta <= 100)
            self.assertIn("int previous = counter++;", source)
            self.assertIn("int advanced = ++counter;", source)
            self.assertLessEqual(abs(start + 2 + delta), int_max)
            return

        if program.family == "control_flow":
            limit_match = re.search(r"index < (\d+)", source)
            skip_match = re.search(r"if \(index == (\d+)\)", source)
            bias_match = re.search(r"total \+= 2 \* index - (-?\d+);", source)
            expected_match = re.search(r"return total == (-?\d+) \? 0 : 1;", source)
            self.assertIsNotNone(limit_match)
            self.assertIsNotNone(skip_match)
            self.assertIsNotNone(bias_match)
            self.assertIsNotNone(expected_match)
            limit = int(limit_match.group(1))
            skipped = int(skip_match.group(1))
            bias = int(bias_match.group(1))
            expected = sum(
                (2 * index - bias) if index % 3 == 0 else (index + bias)
                for index in range(limit)
                if index != skipped
            )
            self.assertTrue(4 <= limit <= 12)
            self.assertTrue(0 <= skipped < limit)
            self.assertTrue(-20 <= bias <= 20)
            self.assertEqual(int(expected_match.group(1)), expected)
            self.assertEqual(source.count("break;"), 3)
            self.assertLessEqual(abs(expected), int_max)
            return

        self.fail("unrecognized generated property family: " + program.family)

    def test_seed_changes_generated_inputs_without_changing_case_order(self):
        first = generate_programs(1729)
        second = generate_programs(1730)
        self.assertEqual(
            tuple(program.family for program in first),
            tuple(program.family for program in second),
        )
        self.assertNotEqual(first, second)

    def test_rejects_out_of_range_or_noninteger_seeds(self):
        for seed in (-1, MAX_SEED + 1, True, 1.5, "7"):
            with self.subTest(seed=seed), self.assertRaises(ValueError):
                generate_programs(seed)

    def test_generated_cases_use_the_canonical_differential_manifest_contract(self):
        for program in generate_programs(1729):
            with self.subTest(family=program.family):
                case = build_manifest_case(
                    program,
                    Path("/tmp/property-source.c"),
                    1729,
                )
                run_fixture_manifest.validate_case(case, 0)
                self.assertEqual(case["expected_exit_code"], 0)
                self.assertEqual(case["compare"], ["stdout", "stderr", "exit_code"])
                self.assertIn("{source}", case["capture_files"])
                self.assertFalse(
                    set(FAMILY_BY_PROGRAM[program.family])
                    - run_fixture_manifest.FEATURE_FAMILIES
                )
                self.assertIn("runtime_parity", FAMILY_BY_PROGRAM[program.family])

    def test_runner_executes_cases_serially_with_all_resource_limits(self):
        calls = []

        def fake_run_case(case, arguments, feature_families):
            source = Path(case["source"])
            self.assertTrue(source.is_file())
            self.assertEqual(arguments.max_rss_kb, 123456)
            self.assertEqual(arguments.max_output_bytes, 654321)
            self.assertEqual(arguments.default_timeout_seconds, 17.0)
            self.assertEqual(arguments.min_system_free_percent, 60)
            calls.append(
                (
                    case["name"],
                    tuple(feature_families),
                    source,
                    tuple(case["capture_files"]),
                    arguments.output_dir,
                )
            )
            return {"status": "passed"}

        with tempfile.TemporaryDirectory(prefix="property-runner-test-") as temporary:
            root = Path(temporary)
            output_dir = root / "artifacts"
            translator = self.write_executable(root / "translator", "exit 0")
            elisa_compiler = self.write_executable(root / "elisa-compiler-a", "exit 0")
            changed_compiler = self.write_executable(root / "elisa-compiler-b", "exit 0")
            with patch.object(run_fixture_manifest, "run_case", side_effect=fake_run_case):
                passed, failed = run_seed(
                    seed=1729,
                    translator=translator,
                    elisa_compiler=elisa_compiler,
                    elisa_runtime=None,
                    output_dir=output_dir,
                    max_rss_kb=123456,
                    timeout_seconds=17.0,
                    max_output_bytes=654321,
                    min_system_free_percent=60,
                )
                changed_passed, changed_failed = run_seed(
                    seed=1729,
                    translator=translator,
                    elisa_compiler=changed_compiler,
                    elisa_runtime=None,
                    output_dir=output_dir,
                    max_rss_kb=123456,
                    timeout_seconds=17.0,
                    max_output_bytes=654321,
                    min_system_free_percent=60,
                )
            self.assertTrue(all(source.is_file() for _, _, source, _, _ in calls))
            self.assertTrue(
                all("{source}" in captures for _, _, _, captures, _ in calls)
            )
            self.assertNotEqual(calls[0][4], calls[MAX_CASES][4])
            self.assertEqual(calls[0][2], calls[MAX_CASES][2])
            expected_sources = {
                program.family: program.source for program in generate_programs(1729)
            }
            for name, _, source, _, _ in calls:
                family = name[len("property_") :].rsplit("_seed_", 1)[0]
                self.assertEqual(
                    source.read_text(encoding="utf-8"), expected_sources[family]
                )

        self.assertEqual((passed, failed), (MAX_CASES, 0))
        self.assertEqual((changed_passed, changed_failed), (MAX_CASES, 0))
        self.assertEqual(
            [name for name, _, _, _, _ in calls],
            ["property_%s_seed_1729" % program.family for program in generate_programs(1729)] * 2,
        )


if __name__ == "__main__":
    unittest.main()
