#!/usr/bin/env python3
"""Verify Clang frontend deadlines cover direct and compilation-db launches."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "testdata/fixtures/simple.c"
TRANSLATOR = Path(
    sys.argv[1]
    if len(sys.argv) > 1
    else os.environ.get("ELISA_TRANSLATOR_BIN", ROOT / "build/elisa-c-transpiler")
).resolve()

FAKE_CLANG = r"""#!/bin/sh
set -eu
for argument in "$@"; do
    if [ "$argument" = "-dM" ]; then
        printf '#define __CHAR_BIT__ 8\n#define __SIZEOF_SHORT__ 2\n#define __SIZEOF_INT__ 4\n#define __SIZEOF_LONG__ 8\n#define __SIZEOF_LONG_LONG__ 8\n#define __SIZEOF_POINTER__ 8\n#define __SIZE_TYPE__ long unsigned int\n'
        exit 0
    fi
done
( sleep 1.7; : > "$ELISA_TIMEOUT_MARKER" ) &
child=$!
printf '{"kind":"TranslationUnitDecl","inner":[]}\n'
wait "$child"
"""


def run_case(
    translator: Path,
    fake_bin: Path,
    marker: Path,
    mode: str,
    temporary: Path,
) -> None:
    command = [str(translator), "--frontend-timeout-seconds", "1"]
    output_directory: Optional[Path] = None
    if mode == "direct":
        command.append(str(SOURCE))
    else:
        database = temporary / f"compile_commands_{mode}.json"
        entry: dict[str, object] = {
            "directory": str(ROOT),
            "file": str(SOURCE),
        }
        words = ["clang", "-std=c11", "-c", str(SOURCE.relative_to(ROOT))]
        if mode == "command":
            entry["command"] = " ".join(words)
        else:
            entry["arguments"] = words
        database.write_text(json.dumps([entry]), encoding="utf-8")
        output_directory = temporary / f"output_{mode}"
        output_directory.mkdir()
        command.extend(["--compile-commands", str(database), "--output-dir", str(output_directory)])

    environment = os.environ.copy()
    environment["PATH"] = f"{fake_bin}{os.pathsep}{environment.get('PATH', '')}"
    environment["ELISA_TIMEOUT_MARKER"] = str(marker)
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=8,
        check=False,
    )
    expected = f"Clang frontend exceeded --frontend-timeout-seconds 1 while processing {SOURCE}"
    if result.returncode != 1 or result.stdout or expected not in result.stderr:
        raise AssertionError(
            f"{mode} frontend timeout contract failed: exit={result.returncode}, "
            f"stdout={result.stdout!r}, stderr={result.stderr!r}"
        )
    if output_directory is not None and any(output_directory.iterdir()):
        raise AssertionError(f"{mode} frontend timeout published partial project output")


def main() -> int:
    if not TRANSLATOR.is_file() or not os.access(TRANSLATOR, os.X_OK):
        print(f"missing translator executable: {TRANSLATOR}", file=sys.stderr)
        return 2

    invalid = subprocess.run(
        [str(TRANSLATOR), "--frontend-timeout-seconds", "0", str(SOURCE)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=8,
        check=False,
    )
    if invalid.returncode != 2 or "--frontend-timeout-seconds requires a positive decimal integer" not in invalid.stderr:
        raise AssertionError(
            f"invalid frontend deadline was not rejected: exit={invalid.returncode}, "
            f"stderr={invalid.stderr!r}"
        )

    with tempfile.TemporaryDirectory(prefix="elisa-clang-timeout-") as temporary_name:
        temporary = Path(temporary_name)
        fake_bin = temporary / "bin"
        fake_bin.mkdir()
        fake_clang = fake_bin / "clang"
        fake_clang.write_text(FAKE_CLANG, encoding="utf-8")
        fake_clang.chmod(0o755)

        markers = [temporary / f"descendant-{mode}.survived" for mode in ("direct", "command", "arguments")]
        for mode, marker in zip(("direct", "command", "arguments"), markers):
            run_case(TRANSLATOR, fake_bin, marker, mode, temporary)

        # A surviving descendant writes its marker after the timeout. Wait past
        # that point so the assertion checks process-group cleanup, not timing.
        time.sleep(1.9)
        survivors = [str(marker) for marker in markers if marker.exists()]
        if survivors:
            raise AssertionError(f"timed-out Clang descendants survived: {survivors}")

    print("Clang frontend deadlines passed: direct, command, arguments, descendant cleanup")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
