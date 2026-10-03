#!/usr/bin/env python3
"""Run bounded, deterministic translator metamorphic checks.

These checks deliberately use a tiny source program. They catch
source-name-dependent lowering and partial-output leaks quickly, rather than
replacing the native/generated differential fixture suite.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TIMEOUT_SECONDS = 20

BASE_SOURCE = """\
int add(int left, int right) {
    int result = left + right;
    return result;
}

int main(void) {
    return add(19, 23);
}
"""

RENAME_PAIRS = (
    ("add", "entry_add"),
    ("left", "lhs_value"),
    ("right", "rhs_value"),
    ("result", "sum_value"),
)

RENAMED_SOURCE = BASE_SOURCE
for _old_name, _new_name in RENAME_PAIRS:
    RENAMED_SOURCE = RENAMED_SOURCE.replace(_old_name, _new_name)


def run_translator(transpiler: Path, source: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(transpiler), str(source)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
        check=False,
    )


def main() -> int:
    configured_transpiler = (
        sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "build/elisa-c-transpiler")
    )
    transpiler = Path(configured_transpiler).expanduser()
    if not transpiler.is_absolute():
        transpiler = ROOT / transpiler
    transpiler = transpiler.resolve()
    if not transpiler.is_file() or not transpiler.stat().st_mode & 0o111:
        print(f"missing translator executable: {transpiler}", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory(prefix="elisa-metamorphic-") as temporary_directory:
        temporary_root = Path(temporary_directory)
        base_path = temporary_root / "base.c"
        renamed_path = temporary_root / "renamed.c"
        truncated_path = temporary_root / "truncated.c"
        base_path.write_text(BASE_SOURCE, encoding="utf-8")
        renamed_path.write_text(RENAMED_SOURCE, encoding="utf-8")
        truncated_path.write_text("int main(void) { return 0;", encoding="utf-8")

        base = run_translator(transpiler, base_path)
        base_repeat = run_translator(transpiler, base_path)
        renamed = run_translator(transpiler, renamed_path)
        if base.returncode != 0 or base_repeat.returncode != 0 or renamed.returncode != 0:
            print("safe-renaming metamorphic case did not translate", file=sys.stderr)
            print(base.stderr, end="", file=sys.stderr)
            print(base_repeat.stderr, end="", file=sys.stderr)
            print(renamed.stderr, end="", file=sys.stderr)
            return 1
        if not base.stdout or not base_repeat.stdout or not renamed.stdout:
            print("safe-renaming metamorphic case emitted empty Elisa", file=sys.stderr)
            return 1
        if base.stdout != base_repeat.stdout or base.stderr != base_repeat.stderr:
            print("repeated translation was not byte-for-byte deterministic", file=sys.stderr)
            return 1

        normalized_renamed = renamed.stdout
        for _old_name, _new_name in RENAME_PAIRS:
            normalized_renamed = normalized_renamed.replace(_new_name, _old_name)
        if normalized_renamed != base.stdout:
            print("translation changed after a semantics-neutral identifier rename", file=sys.stderr)
            return 1

        truncated = run_translator(transpiler, truncated_path)
        if (
            truncated.returncode == 0
            or truncated.stdout
            or "Clang failed while processing" not in truncated.stderr
        ):
            print("truncated source was accepted or published partial Elisa", file=sys.stderr)
            print(truncated.stderr, end="", file=sys.stderr)
            return 1

    print("metamorphic translator checks OK (determinism, safe renaming, truncated input)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
