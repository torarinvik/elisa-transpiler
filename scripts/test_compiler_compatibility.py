#!/usr/bin/env python3
"""Validate the checked-in compiler-pair provenance record."""

import json
import hashlib
import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "docs" / "compiler_compatibility.json"
HASH = re.compile(r"^[0-9a-f]{64}$")
REVISION = re.compile(r"^[0-9a-f]{40}$")


class CompilerCompatibilityManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_required_schema_and_compiler_pair(self):
        self.assertEqual(
            self.manifest["schema"], "elisa-transpiler-compiler-compatibility-v1"
        )
        self.assertRegex(self.manifest["recorded_at"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertEqual(set(self.manifest["compiler_pair"]), {"stage0", "stage1"})
        for stage in ("stage0", "stage1"):
            compiler = self.manifest["compiler_pair"][stage]
            self.assertRegex(compiler["source_revision"], REVISION)
            self.assertTrue(compiler["source_worktree_clean"])
            self.assertIsInstance(compiler["source_freshness_verified"], bool)
            self.assertFalse(Path(compiler["worktree"]).is_absolute())
            self.assertRegex(compiler["executable"]["sha256"], HASH)
            artifact_revision = compiler["executable"]["artifact_source_revision"]
            self.assertRegex(artifact_revision, REVISION)
            self.assertEqual(
                compiler["source_freshness_verified"],
                compiler["source_revision"] == artifact_revision,
                "%s freshness must match the executable's recorded source" % stage,
            )
        stage1 = self.manifest["compiler_pair"]["stage1"]
        self.assertRegex(stage1["runtime"]["sha256"], HASH)
        self.assertEqual(
            stage1["executable"]["artifact_source_revision"],
            stage1["runtime"]["artifact_source_revision"],
            "stage1 executable and runtime must come from the same source revision",
        )
        self.assertRegex(stage1["artifact_build_recipe_sha256"], HASH)
        self.assertRegex(stage1["artifact_source_tree_sha256"], HASH)

    def test_pending_validation_is_not_misreported_as_verified(self):
        validation = self.manifest["translator_validation"]
        self.assertEqual(validation["status"], "pending")
        self.assertFalse(validation["current_translator_sources_verified"])
        self.assertFalse(validation["compiler_products_current"])
        self.assertIn("Stage0 source is at", validation["compiler_product_state"])
        self.assertIn("Stage1 source is at", validation["compiler_product_state"])
        self.assertTrue(validation["reason"])
        self.assertGreaterEqual(len(validation["required_checks"]), 2)
        self.assertTrue(self.manifest["update_policy"])

    def test_present_local_worktrees_match_the_pinned_artifacts(self):
        found_worktree = False
        for stage in ("stage0", "stage1"):
            compiler = self.manifest["compiler_pair"][stage]
            worktree = (ROOT / compiler["worktree"]).resolve()
            if not worktree.is_dir():
                continue
            found_worktree = True
            revision = subprocess.check_output(
                ["git", "-C", str(worktree), "rev-parse", "HEAD"], text=True
            ).strip()
            status = subprocess.check_output(
                ["git", "-C", str(worktree), "status", "--porcelain"], text=True
            )
            with self.subTest(stage=stage):
                self.assertEqual(revision, compiler["source_revision"])
                self.assertEqual(status, "", "pinned compiler worktree must be clean")
                artifacts = [compiler["executable"]]
                if stage == "stage1":
                    artifacts.append(compiler["runtime"])
                for artifact in artifacts:
                    path = worktree / artifact["path"]
                    self.assertTrue(path.is_file(), f"missing pinned artifact: {path}")
                    digest_builder = hashlib.sha256()
                    with path.open("rb") as stream:
                        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                            digest_builder.update(chunk)
                    digest = digest_builder.hexdigest()
                    self.assertEqual(digest, artifact["sha256"], str(path))
                if stage == "stage1":
                    freshness_guard = subprocess.run(
                        [
                            "bash",
                            str(worktree / "scripts" / "assert_stage1_fresh.sh"),
                            str(worktree / compiler["executable"]["path"]),
                        ],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(
                        freshness_guard.returncode == 0,
                        compiler["source_freshness_verified"],
                        freshness_guard.stderr,
                    )
        if not found_worktree:
            self.skipTest("the recorded isolated compiler worktrees are not available here")


if __name__ == "__main__":
    unittest.main(verbosity=2)
