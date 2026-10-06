#!/usr/bin/env python3
"""Compiler-independent tests for translation quality-report provenance."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import quality_provenance  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest_data() -> dict[str, object]:
    return {
        "schema": quality_provenance.MANIFEST_SCHEMA,
        "target": "test-target",
        "compiler_pair": {
            "stage0": {
                "source_revision": "0" * 40,
                "source_worktree_clean": True,
                "source_freshness_verified": True,
                "executable": {
                    "sha256": "a" * 64,
                    "artifact_source_revision": "0" * 40,
                },
            },
            "stage1": {
                "source_revision": "1" * 40,
                "source_worktree_clean": False,
                "source_freshness_verified": False,
                "executable": {
                    "sha256": "b" * 64,
                    "artifact_source_revision": "1" * 40,
                },
                "runtime": {
                    "sha256": "c" * 64,
                    "artifact_source_revision": "2" * 40,
                },
            },
        },
        "translator_validation": {
            "status": "pending",
            "current_translator_sources_verified": False,
            "compiler_products_current": False,
        },
    }


class QualityProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.source = self.root / "sample source.c"
        self.output = self.root / "sample output.elisa"
        self.translator = self.root / "fake translator"
        self.manifest = self.root / "compiler compatibility.json"
        self.source.write_text("int main(void) { return 0; }\n", encoding="utf-8")
        self.output.write_text("def main() -> i32:\n    return 0\n", encoding="utf-8")
        self.translator.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        self.translator.chmod(0o755)
        self.manifest.write_text(json.dumps(manifest_data()), encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    @staticmethod
    def as_dict(fields: list[tuple[str, str]]) -> dict[str, str]:
        return dict(fields)

    def test_report_pins_source_output_translator_and_compiler_products(self) -> None:
        fields = self.as_dict(
            quality_provenance.report(
                self.source, self.output, self.translator, self.manifest
            )
        )
        self.assertEqual(fields["provenance_schema"], "elisa-quality-provenance-v1")
        self.assertEqual(fields["source_sha256"], digest(self.source))
        self.assertEqual(fields["generated_elisa_sha256"], digest(self.output))
        self.assertEqual(fields["translator_sha256"], digest(self.translator))
        self.assertEqual(
            fields["translator_invocation_path"], json.dumps(str(self.translator))
        )
        self.assertEqual(
            fields["translator_resolved_path"], json.dumps(str(self.translator.resolve()))
        )
        self.assertEqual(fields["compiler_manifest_sha256"], digest(self.manifest))
        self.assertEqual(fields["compiler_manifest_status"], "valid")
        self.assertEqual(fields["stage0_source_revision"], json.dumps("0" * 40))
        self.assertEqual(fields["stage0_products_fresh"], "true")
        self.assertEqual(fields["stage1_executable_sha256"], '"' + "b" * 64 + '"')
        self.assertEqual(fields["stage1_runtime_sha256"], '"' + "c" * 64 + '"')
        self.assertEqual(fields["stage1_products_fresh"], "false")
        self.assertEqual(fields["translator_validation_status"], '"pending"')
        self.assertEqual(fields["translator_sources_verified"], "false")
        self.assertEqual(fields["compiler_products_current"], "false")

    def test_artifact_source_revision_must_match_and_be_verified(self) -> None:
        data = manifest_data()
        pair = data["compiler_pair"]
        assert isinstance(pair, dict)
        stage0 = pair["stage0"]
        assert isinstance(stage0, dict)
        stage0["source_freshness_verified"] = False
        self.manifest.write_text(json.dumps(data), encoding="utf-8")
        fields = self.as_dict(
            quality_provenance.report(
                self.source, self.output, self.translator, self.manifest
            )
        )
        self.assertEqual(fields["stage0_products_fresh"], "false")

    def test_missing_or_invalid_manifest_is_explicitly_not_verified(self) -> None:
        absent = self.root / "absent.json"
        missing = self.as_dict(
            quality_provenance.report(self.source, self.output, self.translator, absent)
        )
        self.assertEqual(missing["compiler_manifest_status"], "missing")
        self.assertEqual(missing["compiler_manifest_sha256"], "unavailable")
        self.assertEqual(missing["translator_validation_status"], "unknown")
        self.assertEqual(missing["stage1_products_fresh"], "unknown")

        self.manifest.write_text("{ truncated", encoding="utf-8")
        invalid = self.as_dict(
            quality_provenance.report(
                self.source, self.output, self.translator, self.manifest
            )
        )
        self.assertEqual(invalid["compiler_manifest_status"], "invalid")
        self.assertEqual(invalid["compiler_manifest_sha256"], digest(self.manifest))
        self.assertEqual(invalid["compiler_products_current"], "unknown")

    def test_manifest_data_cannot_inject_additional_report_lines(self) -> None:
        data = manifest_data()
        data["target"] = "target\ntranslator_validation_status: verified"
        self.manifest.write_text(json.dumps(data), encoding="utf-8")
        fields = self.as_dict(
            quality_provenance.report(
                self.source, self.output, self.translator, self.manifest
            )
        )
        self.assertEqual(
            fields["compiler_target"],
            json.dumps("target\ntranslator_validation_status: verified", separators=(",", ":")),
        )
        self.assertEqual(fields["translator_validation_status"], '"pending"')

    def test_paths_with_newlines_are_json_encoded(self) -> None:
        source_with_newline = self.root / "first line\nsecond line.c"
        source_with_newline.write_text("int value;\n", encoding="utf-8")
        fields = self.as_dict(
            quality_provenance.report(
                source_with_newline, self.output, self.translator, self.manifest
            )
        )
        self.assertEqual(
            fields["source_path"], json.dumps(str(source_with_newline))
        )
        self.assertEqual(
            quality_provenance.json_value("line1\nline2"), '"line1\\nline2"'
        )

    def test_non_executable_translator_is_rejected(self) -> None:
        self.translator.chmod(0o644)
        with self.assertRaises(PermissionError):
            quality_provenance.resolve_executable(str(self.translator))

    def test_symlink_invocation_and_resolved_binary_are_both_identified(self) -> None:
        alias = self.root / "translator alias"
        alias.symlink_to(self.translator)
        fields = self.as_dict(
            quality_provenance.report(
                self.source, self.output, alias, self.manifest
            )
        )
        self.assertEqual(
            fields["translator_invocation_path"], json.dumps(str(alias.absolute()))
        )
        self.assertEqual(
            fields["translator_resolved_path"], json.dumps(str(self.translator.resolve()))
        )

    def test_source_or_translator_mutation_during_run_is_rejected(self) -> None:
        initial_source_hash = digest(self.source)
        self.source.write_text("int main(void) { return 1; }\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "source changed"):
            quality_provenance.report(
                self.source,
                self.output,
                self.translator,
                self.manifest,
                expected_source_hash=initial_source_hash,
            )

        initial_translator_hash = digest(self.translator)
        self.translator.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "translator executable changed"):
            quality_provenance.report(
                self.source,
                self.output,
                self.translator,
                self.manifest,
                expected_translator_hash=initial_translator_hash,
            )

    def test_output_collision_check_resolves_existing_symlinks(self) -> None:
        with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
            quality_provenance.assert_output_distinct(self.source, [self.source])
        alias = self.root / "source alias.c"
        alias.symlink_to(self.source)
        with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
            quality_provenance.assert_output_distinct(alias, [self.source])
        with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
            quality_provenance.assert_output_distinct(self.manifest, [self.manifest])
        quality_provenance.assert_output_distinct(
            self.root / "safe output.elisa", [self.source, self.translator, self.manifest]
        )

    def test_checked_in_manifest_pins_reported_compiler_artifact_hashes(self) -> None:
        root = Path(__file__).resolve().parent.parent
        manifest_path = root / "docs" / "compiler_compatibility.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        fields = self.as_dict(
            quality_provenance.report(
                self.source, self.output, self.translator, manifest_path
            )
        )
        self.assertEqual(fields["compiler_manifest_sha256"], digest(manifest_path))
        for stage in ("stage0", "stage1"):
            compiler = manifest["compiler_pair"][stage]
            self.assertEqual(
                fields[f"{stage}_executable_sha256"],
                json.dumps(compiler["executable"]["sha256"]),
            )
            self.assertEqual(
                fields[f"{stage}_source_revision"],
                json.dumps(compiler["source_revision"]),
            )
        self.assertEqual(
            fields["stage1_runtime_sha256"],
            json.dumps(manifest["compiler_pair"]["stage1"]["runtime"]["sha256"]),
        )
        self.assertEqual(
            fields["translator_validation_status"],
            json.dumps(manifest["translator_validation"]["status"]),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
