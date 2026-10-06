#!/usr/bin/env python3
"""Compiler-independent tests for the pinned Wolf4SDL compile database generator."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wolf_compile_commands as generator  # noqa: E402
from wolf_compile_commands import parse_make_dry_run, under  # noqa: E402


class WolfCompileCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path("/tmp/wolf4sdl fixture with spaces").resolve()
        self.units = ["opl3.c", "wl_menu.cpp"]

    def test_preserves_makefile_c_and_host_default_cxx_context(self) -> None:
        output = "\n".join([
            "clang -O2 -g -I/opt/SDL/include -Wall -std=gnu99 -Wimplicit-int -c opl3.c -o opl3.o",
            "clang++ -O2 -g -I/opt/SDL/include -Wall -c wl_menu.cpp -o wl_menu.o",
        ])
        commands = parse_make_dry_run(output, self.root, self.units)
        self.assertEqual([Path(item["file"]).name for item in commands], self.units)
        self.assertEqual(commands[0]["arguments"][0], "clang")
        self.assertIn("-std=gnu99", commands[0]["arguments"])
        self.assertNotIn("-std=gnu99", commands[1]["arguments"])
        self.assertEqual(commands[0]["directory"], str(self.root))
        self.assertEqual(Path(commands[1]["output"]).name, "wl_menu.o")

    def test_parser_accepts_actual_make_dry_run_output_without_building(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "unit.c").touch()
            (root / "unit.cpp").touch()
            (root / "Makefile").write_text(
                """CCFLAGS += -Wall -std=gnu99
CXXFLAGS += -Wall
all: unit.c.o unit.cpp.o
unit.c.o: unit.c
\t$(CC) $(CCFLAGS) -c $< -o $@
unit.cpp.o: unit.cpp
\t$(CXX) $(CXXFLAGS) -c $< -o $@
""",
                encoding="utf-8",
            )
            result = subprocess.run(
                ["make", "-B", "-n", "--no-print-directory", "Q=", "CC=clang", "CXX=clang++", "all"],
                cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                check=False, env={"PATH": os.environ["PATH"], "LC_ALL": "C"},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            commands = parse_make_dry_run(result.stdout, root, ["unit.c", "unit.cpp"])
            self.assertEqual([Path(item["file"]).name for item in commands], ["unit.c", "unit.cpp"])

    def test_pinned_makefile_generates_full_database_without_invoking_compilers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake_bin = root / "bin"
            build = root / "build" / "wolf4sdl"
            fake_bin.mkdir()
            compiler_log = root / "compiler-invocations.log"
            fake_pkg_config = fake_bin / "pkg-config"
            fake_pkg_config.write_text(
                """#!/bin/sh
case "$*" in
  *--exists*) exit 0 ;;
  *--cflags*) printf '%s\\n' '-I/fixture/SDL/include' ;;
  *--libs*) printf '%s\\n' '-lSDL2 -lSDL2_mixer' ;;
  *--modversion*) printf '%s\\n' '2.30.0' ;;
  *--version*) printf '%s\\n' 'pkg-config fixture' ;;
  *) exit 4 ;;
esac
""",
                encoding="utf-8",
            )
            fake_pkg_config.chmod(0o755)
            for executable in ("clang", "clang++"):
                fake_compiler = fake_bin / executable
                fake_compiler.write_text(
                    """#!/bin/sh
case "$1" in
  --version) printf '%s\\n' 'Clang fixture version' ;;
  -dumpmachine) printf '%s\\n' 'aarch64-wolf-fixture' ;;
  *) printf '%s\\n' "$*" >> "$ELISA_FAKE_CLANG_LOG"; exit 97 ;;
esac
""",
                    encoding="utf-8",
                )
                fake_compiler.chmod(0o755)
            path = str(fake_bin) + os.pathsep + os.environ["PATH"]
            with (
                patch.object(generator, "BUILD_ROOT", build),
                patch.dict(os.environ, {"PATH": path, "ELISA_FAKE_CLANG_LOG": str(compiler_log)}),
            ):
                output, count = generator.generate(build / "compile_commands.json")

            database = json.loads(output.read_text(encoding="utf-8"))
            manifest = json.loads(generator.MANIFEST.read_text(encoding="utf-8"))
            wolf = next(item for item in manifest["corpora"] if item["name"] == "Wolf4SDL")
            self.assertEqual(count, 26)
            self.assertEqual(
                [Path(item["file"]).name for item in database],
                wolf["native"]["configured_source_units"],
            )
            c_args = database[0]["arguments"]
            cxx_args = database[1]["arguments"]
            for flag in ("-O2", "-g", "-I/fixture/SDL/include", "-Wall", "-Wpointer-arith", "-Wreturn-type", "-Wwrite-strings", "-Wcast-align"):
                self.assertIn(flag, c_args)
                self.assertIn(flag, cxx_args)
            for flag in ("-Werror-implicit-function-declaration", "-Wimplicit-int", "-Wsequence-point", "-std=gnu99"):
                self.assertIn(flag, c_args)
                self.assertNotIn(flag, cxx_args)
            self.assertFalse(compiler_log.exists(), "make -n unexpectedly invoked a compiler")
            provenance = json.loads(output.with_name("compile_commands.provenance.json").read_text())
            self.assertEqual(provenance["packages"], {"sdl2": "2.30.0", "SDL2_mixer": "2.30.0"})

    def test_missing_duplicate_or_unexpected_unit_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "did not produce"):
            parse_make_dry_run("clang -std=gnu99 -c opl3.c -o opl3.o", self.root, self.units)
        duplicate = "clang -std=gnu99 -c opl3.c -o a.o\nclang -std=gnu99 -c opl3.c -o b.o"
        with self.assertRaisesRegex(ValueError, "more than one"):
            parse_make_dry_run(duplicate, self.root, ["opl3.c"])
        with self.assertRaisesRegex(ValueError, "unexpected source"):
            parse_make_dry_run("clang++ -c other.cpp -o other.o", self.root, self.units)

    def test_rejects_wrong_compiler_language_mode_and_missing_object(self) -> None:
        with self.assertRaisesRegex(ValueError, "C unit"):
            parse_make_dry_run("clang -c opl3.c -o opl3.o", self.root, ["opl3.c"])
        with self.assertRaisesRegex(ValueError, "C\+\+ unit"):
            parse_make_dry_run("clang++ -std=gnu++11 -c wl_menu.cpp -o wl_menu.o", self.root, ["wl_menu.cpp"])
        with self.assertRaisesRegex(ValueError, "no object output"):
            parse_make_dry_run("clang -std=gnu99 -c opl3.c", self.root, ["opl3.c"])

    def test_build_output_must_stay_under_build_root(self) -> None:
        build = Path("/tmp/repo/build/wolf4sdl")
        self.assertTrue(under(build / "compile_commands.json", build))
        self.assertFalse(under(Path("/tmp/repo/compile_commands.json"), build))

    def test_generate_writes_commands_and_matching_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            corpus = root / "wolf"
            build = root / "build" / "wolf4sdl"
            corpus.mkdir()
            makefile = corpus / "Makefile"
            config = corpus / "config.default"
            makefile.write_text("SRCS += opl3.c\nSRCS += wl_menu.cpp\n", encoding="utf-8")
            config.write_text("CFLAGS += -O2 -g\n", encoding="utf-8")
            manifest = root / "corpus_manifest.json"
            manifest.write_text(json.dumps({
                "schema_version": 1,
                "corpora": [{
                    "name": "Wolf4SDL",
                    "source_identity": {"commit": "a" * 40},
                    "native": {
                        "configured_source_units": self.units,
                        "required_packages": ["sdl2", "SDL2_mixer"],
                    },
                }],
            }), encoding="utf-8")
            dry_run = "\n".join([
                "clang -O2 -g -I/SDL/include -Wall -std=gnu99 -c opl3.c -o opl3.o",
                "clang++ -O2 -g -I/SDL/include -Wall -c wl_menu.cpp -o wl_menu.o",
                "clang++ opl3.o wl_menu.o -lSDL2 -lSDL2_mixer -o wolf3d",
            ])

            def fake_run(argv, cwd=None, env=None):
                if argv[:4] == ["git", "-C", str(corpus), "rev-parse"]:
                    return "a" * 40 + "\n"
                if argv[:4] == ["git", "-C", str(corpus), "status"]:
                    return ""
                if argv[:2] == ["pkg-config", "--exists"]:
                    return ""
                if argv[:2] == ["pkg-config", "--modversion"]:
                    return "2.0.0\n"
                if argv == ["make", "--version"]:
                    return "GNU Make test\n"
                if argv[0] == "make" and "--version" not in argv:
                    return dry_run
                if argv[1:] == ["--version"]:
                    return "clang version test\n"
                if argv[1:] == ["-dumpmachine"]:
                    return "aarch64-test\n"
                raise AssertionError(argv)

            with (
                patch.object(generator, "ROOT", root),
                patch.object(generator, "MANIFEST", manifest),
                patch.object(generator, "CORPUS", corpus),
                patch.object(generator, "BUILD_ROOT", build),
                patch.object(generator, "MAKEFILE", makefile),
                patch.object(generator, "CONFIG", config),
                patch.object(generator, "run", side_effect=fake_run),
                patch.object(generator.shutil, "which", side_effect=lambda item: f"/usr/bin/{item}"),
            ):
                output, count = generator.generate(build / "compile_commands.json")

            database = json.loads(output.read_text(encoding="utf-8"))
            provenance_path = build / "compile_commands.provenance.json"
            provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
            self.assertEqual(count, 2)
            self.assertEqual(len(database), 2)
            self.assertEqual(provenance["corpus_commit"], "a" * 40)
            self.assertEqual(provenance["unit_count"], 2)
            self.assertEqual(provenance["make"]["version"], "GNU Make test")
            self.assertEqual(provenance["compile_commands_sha256"], generator.sha256(output.read_bytes()))

    def test_generator_refuses_outputs_outside_build_or_through_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            build = root / "build"
            with patch.object(generator, "BUILD_ROOT", build):
                with self.assertRaisesRegex(ValueError, "must be a file under"):
                    generator.generate(root / "compile_commands.json")
                build.mkdir()
                target = build / "target.json"
                target.write_text("protected", encoding="utf-8")
                link = build / "compile_commands.json"
                link.symlink_to(target)
                with self.assertRaisesRegex(ValueError, "symlink"):
                    generator.generate(link)


if __name__ == "__main__":
    unittest.main(verbosity=2)
