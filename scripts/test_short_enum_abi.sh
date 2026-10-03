#!/bin/sh
set -eu

root_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root_dir"
translator=${ELISA_TRANSLATOR:-$root_dir/build/elisa-c-transpiler}
compiler_worktree_root=${ELISA_TRANSLATOR_COMPILER_WORKTREES:-$root_dir/../elisa-transpiler-worktrees}
stage0=${ELISAC_BIN:-$compiler_worktree_root/stage0-latest/compiler/bin/elisac-local}
stage1=${ELISA_STAGE1_BIN:-$compiler_worktree_root/transpiler/bin/elisac-stage1}
stage1_runtime=${ELISA_STAGE1_RUNTIME:-$compiler_worktree_root/transpiler/build/runtime/elisacore_runtime.o}
if [ ! -x "$stage0" ]; then
    stage0="$root_dir/../compiler/bin/elisac"
fi
if [ ! -x "$stage1" ]; then
    stage1="$root_dir/../Elisa-compiler/bin/elisac-stage1"
fi
if [ ! -f "$stage1_runtime" ]; then
    stage1_runtime="$root_dir/../Elisa-compiler/build/runtime/elisacore_runtime.o"
fi

[ -x "$translator" ] || { echo "missing translator: $translator" >&2; exit 2; }
[ -x "$stage0" ] || { echo "missing stage0 compiler: $stage0" >&2; exit 2; }
[ -x "$stage1" ] || { echo "missing stage1 compiler: $stage1" >&2; exit 2; }
[ -f "$stage1_runtime" ] || { echo "missing stage1 runtime: $stage1_runtime" >&2; exit 2; }

fixture="$root_dir/testdata/fixtures/short_enum_abi.c"
database="$root_dir/testdata/fixtures/short_enum_abi_compile_commands.json"
work_dir=$(mktemp -d "$root_dir/build/short-enum.XXXXXX")
cleanup_short_enum_test() {
    test_rc=$?
    if [ "$test_rc" -ne 0 ]; then
        for test_log in "$work_dir/translate.stderr" "$work_dir/stage0.stderr" "$work_dir/stage1.stderr"; do
            if [ -f "$test_log" ] && [ -s "$test_log" ]; then
                cat "$test_log" >&2
            fi
        done
    fi
    rm -rf "$work_dir"
    return "$test_rc"
}
trap cleanup_short_enum_test EXIT HUP INT TERM

clang -std=c11 -fshort-enums "$fixture" -o "$work_dir/native"
mkdir -p "$work_dir/project"
"$translator" --compile-commands "$database" --output-dir "$work_dir/project" >"$work_dir/translate.stdout" 2>"$work_dir/translate.stderr"

native_rc=0
"$work_dir/native" || native_rc=$?

for compiler_name in stage0 stage1; do
    compiler=$stage0
    runtime_args=
    if [ "$compiler_name" = stage1 ]; then
        compiler=$stage1
        runtime_args="$stage1_runtime"
    fi
    "$compiler" -emit obj -O0 -o "$work_dir/$compiler_name.o" "$work_dir/project/elisa_project.elisa" >"$work_dir/$compiler_name.stdout" 2>"$work_dir/$compiler_name.stderr"
    if [ -n "$runtime_args" ]; then
        clang -Wl,-dead_strip -o "$work_dir/$compiler_name-run" "$work_dir/$compiler_name.o" "$runtime_args" -lm
    elif [ -f "$root_dir/../compiler/runtime/profile_hooks.c" ]; then
        clang -Wl,-dead_strip -o "$work_dir/$compiler_name-run" "$work_dir/$compiler_name.o" "$root_dir/../compiler/runtime/profile_hooks.c" -lm
    else
        clang -Wl,-dead_strip -o "$work_dir/$compiler_name-run" "$work_dir/$compiler_name.o" -lm
    fi
    generated_rc=0
    "$work_dir/$compiler_name-run" || generated_rc=$?
    if [ "$generated_rc" -ne "$native_rc" ]; then
        echo "$compiler_name result $generated_rc differs from native result $native_rc" >&2
        exit 1
    fi
done

grep -q '^const enum TinyUnsigned of u8:' "$work_dir/project/short_enum_abi.elisa"
grep -q '^const enum TinySigned of i8:' "$work_dir/project/short_enum_abi.elisa"
grep -q '^const enum SmallUnsigned of u16:' "$work_dir/project/short_enum_abi.elisa"
echo "short-enum ABI test passed (native, stage0, stage1; u8/i8/u16 storage)"
