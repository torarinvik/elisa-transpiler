#!/usr/bin/env python3
"""Compiler-free tests for bounded deterministic AST JSON minimization."""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from ast_json_minimize import minimize_ast_json
import test_ast_depth as ast_depth


class AstJsonMinimizeTests(unittest.TestCase):
    def test_removes_irrelevant_json_while_preserving_the_mismatch(self):
        original = {
            "kind": "TranslationUnitDecl",
            "inner": [
                {"kind": "NoiseDecl", "name": "unrelated", "detail": {"n": 17}},
                {"kind": "FunctionDecl", "name": "trigger", "junk": [1, 2, 3]},
                {"kind": "NoiseDecl", "name": "also-unrelated"},
            ],
            "metadata": {"padding": "a fairly long value", "enabled": True},
        }

        def mismatch(value):
            return any(
                isinstance(node, dict) and node.get("name") == "trigger"
                for node in value.get("inner", [])
            )

        reduced, probes = minimize_ast_json(original, mismatch)
        self.assertGreater(probes, 1)
        self.assertLess(len(json.dumps(reduced)), len(json.dumps(original)))
        self.assertEqual(reduced["kind"], "TranslationUnitDecl")
        self.assertIn("inner", reduced)
        self.assertTrue(mismatch(reduced))

    def test_non_mismatch_is_returned_without_candidate_probes(self):
        original = {"kind": "TranslationUnitDecl", "inner": [], "extra": "kept"}
        calls = []

        reduced, probes = minimize_ast_json(
            original,
            lambda value: calls.append(value) or False,
        )

        self.assertIs(reduced, original)
        self.assertEqual(probes, 1)
        self.assertEqual(len(calls), 1)

    def test_probe_budget_and_root_envelope_are_enforced(self):
        original = {
            "kind": "TranslationUnitDecl",
            "inner": [{"kind": "Decl", "unused": "large"}],
            "extra": [1, 2, 3, 4],
        }
        calls = []

        reduced, probes = minimize_ast_json(
            original,
            lambda value: calls.append(value) or True,
            max_probes=3,
            max_candidates=100,
        )

        self.assertEqual(probes, 3)
        self.assertEqual(len(calls), probes)
        self.assertEqual(reduced["kind"], "TranslationUnitDecl")
        self.assertIn("inner", reduced)
        self.assertLess(len(json.dumps(reduced)), len(json.dumps(original)))

    def test_candidate_budget_is_enforced(self):
        original = {"kind": "TranslationUnitDecl", "inner": [], "extra": list(range(20))}
        calls = []

        _, probes = minimize_ast_json(
            original,
            lambda value: calls.append(value) or False,
            max_probes=100,
            max_candidates=2,
        )

        self.assertLessEqual(probes, 3)
        self.assertLessEqual(len(calls), 3)

    def test_output_is_deterministic(self):
        original = {"kind": "TranslationUnitDecl", "inner": [1, 2, 3], "extra": "noise"}
        predicate = lambda value: value.get("inner") != []

        first = minimize_ast_json(original, predicate)
        second = minimize_ast_json(original, predicate)
        self.assertEqual(first, second)

    def test_rejects_nonpositive_budgets(self):
        for keyword in ({"max_probes": 0}, {"max_candidates": 0}):
            with self.subTest(keyword=keyword), self.assertRaises(ValueError):
                minimize_ast_json({}, lambda value: True, **keyword)

    def test_content_addressed_regression_store_is_replayable_and_non_overwriting(self):
        original = {
            "kind": "TranslationUnitDecl",
            "inner": [],
            "noise": "minimized seed",
        }
        with tempfile.TemporaryDirectory(prefix="ast-regression-store-") as temporary:
            directory = Path(temporary)
            first = ast_depth.save_projection_regression(directory, "bad/name", original)
            first_contents = first.read_bytes()
            repeated = ast_depth.save_projection_regression(directory, "bad/name", original)
            changed = ast_depth.save_projection_regression(
                directory,
                "bad/name",
                {**original, "noise": "different minimized seed"},
            )

            self.assertEqual(first, repeated)
            self.assertNotEqual(first, changed)
            self.assertEqual(json.loads(first_contents), original)
            self.assertNotIn("/", first.name)
            first.write_text("corrupted", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                ast_depth.save_projection_regression(directory, "bad/name", original)
            with self.assertRaises(ValueError):
                ast_depth.save_projection_regression(directory, "invalid", {"inner": []})
            with self.assertRaises(ValueError):
                ast_depth.save_projection_regression(
                    directory,
                    "oversized",
                    {
                        "kind": "TranslationUnitDecl",
                        "inner": [],
                        "noise": "x" * 5000,
                    },
                )
            capped_directory = directory / "capped"
            capped_directory.mkdir()
            for index in range(ast_depth.MAX_SAVED_PROJECTION_REGRESSIONS):
                (capped_directory / ("seed-%02d.json" % index)).write_text(
                    "{}\n", encoding="utf-8"
                )
            with self.assertRaises(ValueError):
                ast_depth.save_projection_regression(
                    capped_directory, "one-too-many", original
                )

    def test_persisted_regressions_are_loaded_into_the_projection_corpus(self):
        saved_ast = {
            "kind": "TranslationUnitDecl",
            "inner": [],
            "metadata": {"replay": True},
        }
        with tempfile.TemporaryDirectory(prefix="ast-regression-replay-") as temporary:
            root = Path(temporary)
            directory = root / ast_depth.PROJECTION_REGRESSION_RELATIVE_DIR
            ast_depth.save_projection_regression(directory, "replay_case", saved_ast)
            with patch.object(ast_depth, "ROOT", root):
                mutations = ast_depth.deterministic_projection_mutations()

        saved = [(name, text) for name, text in mutations if name.startswith("saved_")]
        self.assertEqual(len(saved), 1)
        self.assertEqual(json.loads(saved[0][1]), saved_ast)

    def test_only_oracle_confirmed_minimized_ast_is_persisted(self):
        original = {
            "kind": "TranslationUnitDecl",
            "inner": [
                {"kind": "NoiseDecl", "name": "discard"},
                {"kind": "FunctionDecl", "name": "trigger", "noise": [1, 2]},
            ],
            "metadata": "discard",
        }

        def reproduces(value):
            return any(
                isinstance(node, dict) and node.get("name") == "trigger"
                for node in value.get("inner", [])
            )

        with tempfile.TemporaryDirectory(prefix="ast-confirmed-regression-") as temporary:
            directory = Path(temporary) / "confirmed"
            minimized, probes, saved_path = (
                ast_depth.minimize_and_persist_projection_mismatch(
                    "confirmed", original, reproduces, directory
                )
            )
            self.assertIsNotNone(saved_path)
            self.assertTrue(reproduces(minimized))
            self.assertEqual(json.loads(saved_path.read_text(encoding="utf-8")), minimized)
            self.assertGreater(probes, 0)
            self.assertLessEqual(probes, 8)

            unconfirmed_directory = Path(temporary) / "unconfirmed"
            calls = []
            unchanged, unconfirmed_probes, unconfirmed_path = (
                ast_depth.minimize_and_persist_projection_mismatch(
                    "unconfirmed",
                    original,
                    lambda value: calls.append(value) or False,
                    unconfirmed_directory,
                )
            )
            self.assertIs(unchanged, original)
            self.assertEqual(unconfirmed_probes, 1)
            self.assertEqual(len(calls), 1)
            self.assertIsNone(unconfirmed_path)
            self.assertFalse(unconfirmed_directory.exists())

    def test_ast_probe_persists_stable_mismatch_but_not_transient_mismatch(self):
        def run_probe(root, mode):
            root.mkdir(parents=True)
            transpiler = root / "fake-transpiler"
            transpiler.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            transpiler.chmod(0o755)
            calls = 0

            def fake_run_case(transpiler, fake_clang, ast_path, *options, timeout=30):
                nonlocal calls
                calls += 1
                value = json.loads(Path(ast_path).read_text(encoding="utf-8"))
                mismatch = "metadata" in value and (
                    mode == "stable" or calls == 3
                )
                return subprocess.CompletedProcess(
                    [str(transpiler)],
                    0,
                    "projection mismatch\n" if mismatch else "baseline\n",
                    "",
                )

            errors = io.StringIO()
            with (
                patch.object(ast_depth, "ROOT", root),
                patch.object(ast_depth, "run_case", side_effect=fake_run_case),
                patch.object(sys, "argv", ["test_ast_depth.py", str(transpiler)]),
                contextlib.redirect_stderr(errors),
            ):
                result = ast_depth.main()
            self.assertEqual(result, 1)
            return calls, errors.getvalue()

        with tempfile.TemporaryDirectory(prefix="ast-projection-main-path-") as temporary:
            root = Path(temporary)
            stable_calls, stable_errors = run_probe(root / "stable", "stable")
            stable_regressions = list(
                (root / "stable" / ast_depth.PROJECTION_REGRESSION_RELATIVE_DIR).glob(
                    "*.json"
                )
            )
            self.assertEqual(len(stable_regressions), 1)
            self.assertGreater(stable_calls, 3)
            self.assertIn("saved minimized AST regression:", stable_errors)
            with patch.object(ast_depth, "ROOT", root / "stable"):
                replayed = ast_depth.deterministic_projection_mutations()
            saved = [
                json.loads(text)
                for name, text in replayed
                if name.startswith("saved_")
            ]
            self.assertEqual(saved, [json.loads(stable_regressions[0].read_text())])

            transient_root = root / "transient"
            transient_calls, transient_errors = run_probe(
                transient_root, "transient"
            )
            transient_directory = (
                transient_root / ast_depth.PROJECTION_REGRESSION_RELATIVE_DIR
            )
            self.assertEqual(transient_calls, 4)
            self.assertIn("no regression saved", transient_errors)
            self.assertFalse(transient_directory.exists())


if __name__ == "__main__":
    unittest.main()
