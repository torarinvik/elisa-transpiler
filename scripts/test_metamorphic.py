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

POINTER_INDEX_SOURCE = """\
int first_value(int *argv) {
    return argv[0];
}

int main(void) {
    int values[1] = {42};
    return first_value(values);
}
"""
def _identifier_character(character: str) -> bool:
    return character == "_" or character.isalnum()


def normalize_identifier(source: str, old_name: str, new_name: str) -> str:
    """Rename a code identifier without rewriting quoted text or comments."""
    if not old_name:
        raise ValueError("old identifier must not be empty")

    output: list[str] = []
    index = 0
    quote: str | None = None
    escaped = False
    in_comment = False
    while index < len(source):
        character = source[index]
        if in_comment:
            output.append(character)
            if character == "\n":
                in_comment = False
            index += 1
            continue
        if quote is not None:
            output.append(character)
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            index += 1
            continue
        if character in ('"', "'"):
            quote = character
            output.append(character)
            index += 1
            continue
        if character == "#":
            in_comment = True
            output.append(character)
            index += 1
            continue

        end = index + len(old_name)
        if source.startswith(old_name, index):
            left_is_identifier = index > 0 and _identifier_character(source[index - 1])
            right_is_identifier = end < len(source) and _identifier_character(source[end])
            if not left_is_identifier and not right_is_identifier:
                output.append(new_name)
                index = end
                continue

        output.append(character)
        index += 1
    return "".join(output)


RENAMED_SOURCE = BASE_SOURCE
for _old_name, _new_name in RENAME_PAIRS:
    RENAMED_SOURCE = normalize_identifier(RENAMED_SOURCE, _old_name, _new_name)

POINTER_INDEX_RENAMED_SOURCE = normalize_identifier(
    POINTER_INDEX_SOURCE, "argv", "cursor"
)


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
        pointer_index_path = temporary_root / "pointer-index.c"
        pointer_index_renamed_path = temporary_root / "pointer-index-renamed.c"
        truncated_path = temporary_root / "truncated.c"
        base_path.write_text(BASE_SOURCE, encoding="utf-8")
        renamed_path.write_text(RENAMED_SOURCE, encoding="utf-8")
        pointer_index_path.write_text(POINTER_INDEX_SOURCE, encoding="utf-8")
        pointer_index_renamed_path.write_text(
            POINTER_INDEX_RENAMED_SOURCE, encoding="utf-8"
        )
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
            normalized_renamed = normalize_identifier(
                normalized_renamed, _new_name, _old_name
            )
        if normalized_renamed != base.stdout:
            print("translation changed after a semantics-neutral identifier rename", file=sys.stderr)
            return 1

        pointer_index = run_translator(transpiler, pointer_index_path)
        pointer_index_renamed = run_translator(transpiler, pointer_index_renamed_path)
        if (
            pointer_index.returncode != 0
            or pointer_index_renamed.returncode != 0
            or not pointer_index.stdout
            or not pointer_index_renamed.stdout
        ):
            print("pointer-index safe-renaming case did not translate", file=sys.stderr)
            print(pointer_index.stderr, end="", file=sys.stderr)
            print(pointer_index_renamed.stderr, end="", file=sys.stderr)
            return 1
        normalized_pointer_index = normalize_identifier(
            pointer_index_renamed.stdout, "cursor", "argv"
        )
        if normalized_pointer_index != pointer_index.stdout:
            print(
                "pointer-index translation changed after renaming its base variable",
                file=sys.stderr,
            )
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

    print(
        "metamorphic translator checks OK "
        "(determinism, scalar/pointer-index safe renaming, truncated input)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
