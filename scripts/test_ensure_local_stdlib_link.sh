#!/bin/sh
set -eu

root_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
temporary_root=$(mktemp -d "${TMPDIR:-/tmp}/elisa-stdlib-link.XXXXXX")
trap 'rm -rf "$temporary_root"' EXIT HUP INT TERM
helper=$root_dir/scripts/ensure_local_stdlib_link.sh

translator="$temporary_root/translator with spaces"
stdlib_a="$temporary_root/compiler a/elisacore_std"
stdlib_b="$temporary_root/compiler b/elisacore_std"
mkdir -p "$translator/src" "$stdlib_a" "$stdlib_b"

printf 'runtime-a\n' > "$stdlib_a/elisacore_runtime.elisa"
printf 'runtime-b\n' > "$stdlib_b/elisacore_runtime.elisa"
printf 'json\n' > "$stdlib_a/elisacore_json.elisa"
printf 'collections\n' > "$stdlib_a/collections.elisa"
printf 'json\n' > "$stdlib_b/elisacore_json.elisa"
printf 'collections\n' > "$stdlib_b/collections.elisa"

sh "$helper" "$translator" "$stdlib_a"
link=$translator/src/.compiler_std
[ -L "$link" ]
[ -f "$link/elisacore_runtime.elisa" ]
[ "$(cat "$link/elisacore_runtime.elisa")" = runtime-a ]
sh "$helper" "$translator" "$stdlib_a"

if sh "$helper" "$translator" "$stdlib_b" >"$temporary_root/out" 2>"$temporary_root/err"; then
    echo "expected a conflicting standard-library target to be rejected" >&2
    exit 1
fi
grep -q 'refusing to replace conflicting standard library link' "$temporary_root/err"
[ "$(readlink "$link")" = "$(CDPATH= cd -- "$stdlib_a" && pwd -P)" ]

collision=$temporary_root/collision
mkdir -p "$collision/src/.compiler_std"
if sh "$helper" "$collision" "$stdlib_a" >"$temporary_root/out" 2>"$temporary_root/err"; then
    echo "expected a real path collision to be rejected" >&2
    exit 1
fi
grep -q 'refusing to replace non-symlink' "$temporary_root/err"

if sh "$helper" "$temporary_root/missing-translator" "$stdlib_a" >"$temporary_root/out" 2>"$temporary_root/err"; then
    echo "expected a missing translator root to be rejected" >&2
    exit 1
fi

if sh "$helper" "$translator" "$temporary_root/missing-stdlib" >"$temporary_root/out" 2>"$temporary_root/err"; then
    echo "expected a missing standard library to be rejected" >&2
    exit 1
fi

incomplete_stdlib=$temporary_root/incomplete-stdlib
mkdir -p "$incomplete_stdlib"
if sh "$helper" "$translator" "$incomplete_stdlib" >"$temporary_root/out" 2>"$temporary_root/err"; then
    echo "expected a standard library missing required modules to be rejected" >&2
    exit 1
fi
grep -q 'missing elisacore_runtime.elisa' "$temporary_root/err"

echo "local Elisa standard-library link checks passed"
