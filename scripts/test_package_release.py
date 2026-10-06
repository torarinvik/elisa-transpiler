#!/usr/bin/env python3
"""Compiler-independent tests for relocatable release assembly."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from package_release import ReleaseError, SCHEMA, assemble_release


class PackageReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="translator-release-")
        self.root = Path(self.temporary.name)
        self.translator = self.root / "build output" / "elisa-c-transpiler"
        self.translator.parent.mkdir()
        self.translator.write_text("#!/bin/sh\nprintf '%s\\n' \"$*\"\n", encoding="utf-8")
        self.translator.chmod(0o755)
        self.cpp_lib = self.root / "cpp source"
        self.cpp_lib.mkdir()
        (self.cpp_lib / "unordered_map.elisa").write_text("include \"unordered_map_core.elisa\"\n", encoding="utf-8")
        (self.cpp_lib / "unordered_map_core.elisa").write_text("module cpp\n", encoding="utf-8")
        self.stdlib = self.root / "selected stdlib"
        self.stdlib.mkdir()
        for filename in ("collections.elisa", "elisacore_json.elisa", "elisacore_runtime.elisa"):
            (self.stdlib / filename).write_text("module " + filename.removesuffix(".elisa") + "\n", encoding="utf-8")
        self.license = self.root / "project license.txt"
        self.license.write_text("license text\n", encoding="utf-8")
        self.build_record = self.root / "compiler compatibility.json"
        self.build_record.write_text(json.dumps({
            "schema": "elisa-transpiler-compiler-compatibility-v1",
            "target": "darwin-arm64",
            "compiler_pair": {
                "stage0": {
                    "source_revision": "a" * 40,
                    "source_freshness_verified": True,
                    "executable": {"sha256": "1" * 64},
                },
                "stage1": {
                    "source_revision": "b" * 40,
                    "source_freshness_verified": True,
                    "bootstrap_reproduced_from_stage0": True,
                    "executable": {"sha256": "2" * 64},
                    "runtime": {"sha256": "3" * 64},
                },
            },
            "translator_validation": {
                "status": "verified",
                "current_translator_sources_verified": True,
                "compiler_products_current": True,
            },
        }), encoding="utf-8")

    def tearDown(self):
        self.temporary.cleanup()

    def package(self, output: Path) -> Path:
        return assemble_release(
            version="1.2.3",
            translator=self.translator,
            cpp_lib_dir=self.cpp_lib,
            elisa_std_dir=self.stdlib,
            licenses=[("Project", self.license)],
            build_record=self.build_record,
            clang_identity="Apple clang version 21.0.0",
            output_dir=output,
            target="darwin-arm64",
        )

    def test_package_has_self_contained_paths_and_content_hashes(self):
        output = self.package(self.root / "release")
        manifest = json.loads((output / "release-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema"], SCHEMA)
        self.assertEqual(manifest["version"], "1.2.3")
        self.assertEqual(manifest["target"], "darwin-arm64")
        self.assertEqual(manifest["dependencies"]["clang"], "Apple clang version 21.0.0")
        self.assertEqual(manifest["toolchain"]["stage1"]["runtime_sha256"], "3" * 64)
        self.assertEqual(manifest["support_directories"], {"cpp_lib": "cpp_lib", "elisa_std": "elisa_std"})
        self.assertEqual(manifest["licenses"], [{"name": "Project", "path": "licenses/Project.txt"}])
        entries = {entry["path"]: entry for entry in manifest["files"]}
        self.assertIn("bin/elisa-c-transpiler", entries)
        self.assertIn("cpp_lib/unordered_map_core.elisa", entries)
        self.assertIn("elisa_std/elisacore_runtime.elisa", entries)
        self.assertEqual(entries["bin/elisa-c-transpiler"]["mode"], "0755")
        for relative, entry in entries.items():
            content = (output / relative).read_bytes()
            self.assertEqual(hashlib.sha256(content).hexdigest(), entry["sha256"])
            self.assertEqual(len(content), entry["size_bytes"])
            self.assertNotIn(str(self.root), content.decode("utf-8", "ignore"))

        relocated = self.root / "relocated package"
        shutil.move(output, relocated)
        command = [str(relocated / "bin" / "elisa-c-transpiler"), "--cpp-lib-dir", str(relocated / "cpp_lib"), "--elisa-std-dir", str(relocated / "elisa_std"), "source.c"]
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        self.assertIn(str(relocated / "cpp_lib"), result.stdout)
        self.assertIn(str(relocated / "elisa_std"), result.stdout)

    def test_two_assemblies_from_the_same_inputs_are_byte_identical(self):
        first = self.package(self.root / "release-a")
        second = self.package(self.root / "release-b")
        files_a = sorted(path.relative_to(first) for path in first.rglob("*") if path.is_file())
        files_b = sorted(path.relative_to(second) for path in second.rglob("*") if path.is_file())
        self.assertEqual(files_a, files_b)
        self.assertEqual(
            {name: (first / name).read_bytes() for name in files_a},
            {name: (second / name).read_bytes() for name in files_b},
        )

    def test_existing_destination_is_never_replaced(self):
        output = self.root / "existing"
        output.mkdir()
        sentinel = output / "keep.txt"
        sentinel.write_text("user data", encoding="utf-8")
        with self.assertRaisesRegex(ReleaseError, "refusing to replace"):
            self.package(output)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "user data")

    def test_destination_cannot_be_inside_a_support_tree(self):
        with self.assertRaisesRegex(ReleaseError, "overlaps a support source tree"):
            self.package(self.cpp_lib / "release")

    def test_explicit_license_input_is_required(self):
        with self.assertRaisesRegex(ReleaseError, "explicit --license"):
            assemble_release(
                version="1.2.3", translator=self.translator, cpp_lib_dir=self.cpp_lib,
                elisa_std_dir=self.stdlib, licenses=[], build_record=self.build_record,
                clang_identity="Apple clang version 21.0.0",
                output_dir=self.root / "release",
                target="darwin-arm64",
            )

    def test_required_stdlib_modules_are_checked_before_publication(self):
        (self.stdlib / "collections.elisa").unlink()
        output = self.root / "release"
        with self.assertRaisesRegex(ReleaseError, "missing required modules: collections.elisa"):
            self.package(output)
        self.assertFalse(output.exists())
        self.assertFalse(list(self.root.glob(".release.staging-*")))

    def test_support_symlinks_are_rejected(self):
        target = self.root / "external.elisa"
        target.write_text("module external\n", encoding="utf-8")
        (self.cpp_lib / "linked.elisa").symlink_to(target)
        with self.assertRaisesRegex(ReleaseError, "contains a symlink"):
            self.package(self.root / "release")

    def test_license_symlink_and_missing_file_are_rejected(self):
        link = self.root / "license-link.txt"
        link.symlink_to(self.license)
        with self.assertRaisesRegex(ReleaseError, "license input is missing or not a regular file"):
            assemble_release(
                version="1.2.3", translator=self.translator, cpp_lib_dir=self.cpp_lib,
                elisa_std_dir=self.stdlib, licenses=[("Project", link)],
                build_record=self.build_record,
                clang_identity="Apple clang version 21.0.0",
                output_dir=self.root / "release", target="darwin-arm64",
            )

    def test_release_identifiers_cannot_escape_paths(self):
        with self.assertRaisesRegex(ReleaseError, "version must be"):
            assemble_release(
                version="../1.2.3", translator=self.translator, cpp_lib_dir=self.cpp_lib,
                elisa_std_dir=self.stdlib, licenses=[("Project", self.license)],
                build_record=self.build_record,
                clang_identity="Apple clang version 21.0.0",
                output_dir=self.root / "release", target="darwin-arm64",
            )

    def test_release_refuses_stale_or_mismatched_build_provenance(self):
        data = json.loads(self.build_record.read_text(encoding="utf-8"))
        data["translator_validation"]["status"] = "pending"
        self.build_record.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(ReleaseError, "does not verify current translator"):
            self.package(self.root / "release")


if __name__ == "__main__":
    unittest.main()
