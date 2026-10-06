#!/bin/sh
set -eu

root_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root_dir"

transpiler=${ELISA_TRANSLATOR_BIN:-$root_dir/build/elisa-c-transpiler}
if [ ! -x "$transpiler" ]; then
    echo "missing translator executable: $transpiler" >&2
    exit 2
fi

output=$(mktemp)
diagnostics=$(mktemp)
partial_ast=$(mktemp)
project_output=$(mktemp -d)
conflict_output=$(mktemp -d)
normalization_db=$(mktemp)
mismatch_response=$(mktemp)
transaction_db=$(mktemp)
transaction_output=$(mktemp -d)
cleanup_test_files() {
    for temporary_file in "$output" "$diagnostics" "$partial_ast" \
        "$normalization_db" "$mismatch_response" "$transaction_db"; do
        unlink "$temporary_file"
    done
    for generated_file in \
        "$project_output/compile_command_quoted.elisa" \
        "$project_output/compile_command_quoted_2.elisa" \
        "$project_output/identity_alias.elisa" \
        "$project_output/language_override.elisa" \
        "$project_output/elisa_project.elisa" \
        "$conflict_output/compile_command_quoted.elisa" \
        "$conflict_output/compile_command_quoted_2.elisa" \
        "$conflict_output/elisa_project.elisa" \
        "$conflict_output/empty.rsp" \
        "$conflict_output/oversized.rsp" \
        "$conflict_output/cycle.rsp" \
        "$conflict_output/malformed.rsp" \
        "$conflict_output/identity_alias.c"; do
        if [ -f "$generated_file" ]; then unlink "$generated_file"; fi
    done
    for generated_file in \
        "$transaction_output/simple.elisa" \
        "$transaction_output/elisa_project.elisa" \
        "$transaction_output/zz_transaction_failure.c"; do
        if [ -f "$generated_file" ]; then unlink "$generated_file"; fi
    done
    rmdir "$project_output"
    rmdir "$conflict_output"
    rmdir "$transaction_output"
}
trap cleanup_test_files EXIT HUP INT TERM

set +e
clang -std=c11 -fsyntax-only -Xclang -ast-dump=json \
    testdata/fixtures/clang_failure.c >"$partial_ast" 2>/dev/null
clang_status=$?
set -e

if [ "$clang_status" -eq 0 ] || [ ! -s "$partial_ast" ] || \
    ! rg -q '"kind": "TranslationUnitDecl"' "$partial_ast"; then
    echo "failure fixture no longer makes Clang emit partial AST with a failing status" >&2
    exit 1
fi

set +e
clang++ -std=gnu++11 -fsyntax-only -Xclang -ast-dump=json \
    testdata/fixtures/clang_failure.cpp >"$partial_ast" 2>/dev/null
clangxx_status=$?
set -e

if [ "$clangxx_status" -eq 0 ] || [ ! -s "$partial_ast" ] || \
    ! rg -q '"kind": "TranslationUnitDecl"' "$partial_ast"; then
    echo "failure fixture no longer makes Clang++ emit partial AST with a failing status" >&2
    exit 1
fi

set +e
"$transpiler" --max-frontend-output-bytes 64 testdata/fixtures/simple.c >"$output" 2>"$diagnostics"
status=$?
set -e

if [ "$status" -eq 0 ] || [ -s "$output" ] || \
    ! rg -q 'exceeded --max-frontend-output-bytes while processing testdata/fixtures/simple.c' "$diagnostics"; then
    echo "frontend byte limit did not reject oversized Clang output cleanly" >&2
    cat "$diagnostics" >&2
    exit 1
fi

set +e
"$transpiler" --max-frontend-output-bytes 0 testdata/fixtures/simple.c >"$output" 2>"$diagnostics"
status=$?
set -e

if [ "$status" -ne 2 ] || [ -s "$output" ] || \
    ! rg -q -- '--max-frontend-output-bytes requires a positive decimal integer' "$diagnostics"; then
    echo "invalid frontend byte limit was not rejected during option parsing" >&2
    cat "$diagnostics" >&2
    exit 1
fi

"$transpiler" testdata/fixtures/simple.c >"$partial_ast"
"$transpiler" --frontend-stats testdata/fixtures/simple.c >"$output" 2>"$diagnostics"
if [ ! -s "$output" ] || ! cmp -s "$partial_ast" "$output" || \
    ! rg -q 'frontend-stats source=.*raw_json_bytes=[1-9][0-9]* projected_json_bytes=[1-9][0-9]* parsed_arena_bytes=[1-9][0-9]* projected_json_values=[1-9][0-9]*' "$diagnostics"; then
    echo "frontend stats changed output or omitted raw/projected/arena bytes and projected JSON values" >&2
    cat "$diagnostics" >&2
    exit 1
fi
if ! rg -q 'frontend-phase source=.* phase=json-parsed parsed_arena_bytes=[1-9][0-9]* .* declarations=' "$diagnostics" || \
    ! rg -q 'frontend-phase source=.* phase=functions-lowered .* expressions=[1-9][0-9]* statements=[1-9][0-9]*' "$diagnostics"; then
    echo "frontend phase stats omitted parse or lowering progress" >&2
    cat "$diagnostics" >&2
    exit 1
fi

"$transpiler" testdata/fixtures/no_translator_default_macros.c >"$output" 2>"$diagnostics"
if [ -s "$diagnostics" ] || ! rg -q 'return 42' "$output"; then
    echo "direct translation injected default feature-test or fortify macros" >&2
    cat "$diagnostics" >&2
    exit 1
fi

set +e
"$transpiler" --frontend-stats --max-frontend-json-values 2 \
    testdata/fixtures/simple.c >"$output" 2>"$diagnostics"
limit_exit=$?
set -e
if [ "$limit_exit" -ne 1 ] || [ -s "$output" ] || \
    ! rg -q 'frontend-stats source=.*parsed_arena_bytes=0 projected_json_values=3' "$diagnostics" || \
    ! rg -q 'projected AST exceeded --max-frontend-json-values 2 while processing testdata/fixtures/simple.c' "$diagnostics"; then
    echo "frontend JSON-value limit did not reject the AST before DOM allocation" >&2
    cat "$diagnostics" >&2
    exit 1
fi

set +e
"$transpiler" --max-frontend-json-values 0 testdata/fixtures/simple.c >"$output" 2>"$diagnostics"
limit_exit=$?
set -e
if [ "$limit_exit" -ne 2 ] || [ -s "$output" ] || \
    ! rg -q -- '--max-frontend-json-values requires a positive decimal integer' "$diagnostics"; then
    echo "invalid frontend JSON-value limit was not rejected during option parsing" >&2
    cat "$diagnostics" >&2
    exit 1
fi

# Use a fake successful Clang driver to prove that malformed raw JSON is not
# made to look valid by the projection dropping fields or closing a truncated
# `inner` array. The normal parser must receive the original malformed input.
for malformed_ast in \
    testdata/fixtures/truncated_clang_ast.json \
    testdata/fixtures/malformed_dropped_clang_ast_field.json; do
    set +e
    PATH="$root_dir/testdata/fake_tools:$PATH" \
        ELISA_FAKE_CLANG_JSON="$root_dir/$malformed_ast" \
        "$transpiler" testdata/fixtures/simple.c >"$output" 2>"$diagnostics"
    malformed_exit=$?
    set -e
    if [ "$malformed_exit" -eq 0 ] || [ -s "$output" ] || \
        ! rg -q 'Clang emitted invalid or over-depth AST JSON while processing testdata/fixtures/simple.c' "$diagnostics"; then
        echo "translator accepted or obscured malformed raw Clang JSON from $malformed_ast" >&2
        cat "$diagnostics" >&2
        exit 1
    fi
done

# Raw UTF-8 scalar boundaries must survive strict preflight in fields that the
# projection discards. One fake-AST run exercises every legal boundary without
# multiplying the expensive translator invocations.
python3 - "$partial_ast" <<'PY'
from pathlib import Path
import sys

valid = (
    b"\xc2\x80\xdf\xbf\xe0\xa0\x80\xed\x9f\xbf\xee\x80\x80"
    b"\xef\xbf\xbf\xf0\x90\x80\x80\xf4\x8f\xbf\xbf"
)
Path(sys.argv[1]).write_bytes(
    b'{"kind":"TranslationUnitDecl","inner":[],"ignored":"' + valid + b'"}'
)
PY
set +e
PATH="$root_dir/testdata/fake_tools:$PATH" \
    ELISA_FAKE_CLANG_JSON="$partial_ast" \
    "$transpiler" testdata/fixtures/simple.c >"$output" 2>"$diagnostics"
valid_utf8_exit=$?
set -e
if [ "$valid_utf8_exit" -ne 0 ] || [ ! -s "$output" ]; then
    echo "translator rejected valid raw UTF-8 scalar boundaries in Clang JSON" >&2
    cat "$diagnostics" >&2
    exit 1
fi

# Exercise malformed lead, continuation, overlong, surrogate, out-of-range and
# truncation cases. Each must fail before DOM construction/publication.
for invalid_utf8_case in \
    isolated-continuation isolated-final-continuation \
    overlong-two-byte invalid-two-byte-lead invalid-two-byte-continuation \
    overlong-three-byte invalid-three-byte-continuation surrogate \
    overlong-four-byte invalid-four-byte-continuation out-of-range \
    invalid-lead-f5 invalid-lead-ff truncated-two-byte \
    truncated-three-byte truncated-four-byte; do
    python3 - "$partial_ast" "$invalid_utf8_case" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
invalid = {
    "isolated-continuation": b"\x80",
    "isolated-final-continuation": b"\xbf",
    "overlong-two-byte": b"\xc0\xaf",
    "invalid-two-byte-lead": b"\xc1\xbf",
    "invalid-two-byte-continuation": b"\xc2 ",
    "overlong-three-byte": b"\xe0\x80\x80",
    "invalid-three-byte-continuation": b"\xe1\x80 ",
    "surrogate": b"\xed\xa0\x80",
    "overlong-four-byte": b"\xf0\x80\x80\x80",
    "invalid-four-byte-continuation": b"\xf1\x80\x80 ",
    "out-of-range": b"\xf4\x90\x80\x80",
    "invalid-lead-f5": b"\xf5\x80\x80\x80",
    "invalid-lead-ff": b"\xff",
    "truncated-two-byte": b"\xc2",
    "truncated-three-byte": b"\xe2\x82",
    "truncated-four-byte": b"\xf0\x90\x80",
}[sys.argv[2]]
path.write_bytes(b'{"kind":"TranslationUnitDecl","inner":[],"ignored":"' + invalid + b'"}')
PY
    set +e
    PATH="$root_dir/testdata/fake_tools:$PATH" \
        ELISA_FAKE_CLANG_JSON="$partial_ast" \
        "$transpiler" testdata/fixtures/simple.c >"$output" 2>"$diagnostics"
    malformed_utf8_exit=$?
    set -e
    if [ "$malformed_utf8_exit" -eq 0 ] || [ -s "$output" ] || \
        ! rg -q 'Clang emitted invalid or over-depth AST JSON while processing testdata/fixtures/simple.c' "$diagnostics"; then
        echo "translator accepted malformed raw UTF-8 in Clang JSON ($invalid_utf8_case)" >&2
        cat "$diagnostics" >&2
        exit 1
    fi
done

# Syntax-valid but schema-invalid roots must fail closed after parsing. Keep
# this contract deliberately narrow: the projector requires a TranslationUnitDecl
# object with an array-valued inner field, while nested Clang fields remain
# version-tolerant and are handled by the existing lowering diagnostics.
for schema_case in \
    ast_schema_missing_kind.json \
    ast_schema_wrong_kind.json \
    ast_schema_wrong_kind_utf8.json \
    ast_schema_missing_inner.json \
    ast_schema_wrong_inner.json \
    ast_schema_non_object.json; do
    set +e
    PATH="$root_dir/testdata/fake_tools:$PATH" \
        ELISA_FAKE_CLANG_JSON="$root_dir/testdata/fixtures/$schema_case" \
        "$transpiler" testdata/fixtures/simple.c >"$output" 2>"$diagnostics"
    schema_exit=$?
    set -e
    if [ "$schema_exit" -eq 0 ] || [ -s "$output" ] || \
        ! rg -q 'Clang AST schema violation: (root-not-object|missing-required-field:root\.(kind|inner)|unsupported-root-kind) while processing testdata/fixtures/simple.c' "$diagnostics"; then
        echo "translator accepted syntax-valid invalid AST schema from $schema_case" >&2
        cat "$diagnostics" >&2
        exit 1
    fi
done

set +e
"$transpiler" testdata/fixtures/clang_failure.c >"$output" 2>"$diagnostics"
status=$?
set -e

if [ "$status" -eq 0 ]; then
    echo "translator accepted a source file rejected by Clang" >&2
    exit 1
fi
if [ -s "$output" ]; then
    echo "translator emitted partial Elisa after Clang failed" >&2
    exit 1
fi
if ! rg -q 'Clang failed while processing testdata/fixtures/clang_failure.c' "$diagnostics"; then
    echo "missing source-qualified Clang failure diagnostic" >&2
    cat "$diagnostics" >&2
    exit 1
fi
if ! rg -q 'error:' "$diagnostics"; then
    echo "Clang stderr was not captured and relayed independently" >&2
    cat "$diagnostics" >&2
    exit 1
fi

set +e
"$transpiler" testdata/fixtures/clang_failure.cpp >"$output" 2>"$diagnostics"
status=$?
set -e

if [ "$status" -eq 0 ]; then
    echo "translator accepted a C++ source file rejected by Clang" >&2
    exit 1
fi
if [ -s "$output" ]; then
    echo "translator emitted partial Elisa after Clang++ failed" >&2
    exit 1
fi
if ! rg -q 'Clang failed while processing testdata/fixtures/clang_failure.cpp' "$diagnostics"; then
    echo "missing source-qualified Clang++ failure diagnostic" >&2
    cat "$diagnostics" >&2
    exit 1
fi
if ! rg -q 'error:' "$diagnostics"; then
    echo "Clang++ stderr was not captured and relayed independently" >&2
    cat "$diagnostics" >&2
    exit 1
fi

set +e
"$transpiler" --compile-commands testdata/fixtures/clang_failure_compile_commands.json \
    --output-dir "$project_output" >"$output" 2>"$diagnostics"
status=$?
set -e

if [ "$status" -eq 0 ]; then
    echo "project translation accepted a source rejected by Clang" >&2
    exit 1
fi
if [ -s "$output" ]; then
    echo "project translation emitted stdout after Clang failed" >&2
    exit 1
fi
if ! rg -q 'Clang failed while processing testdata/fixtures/clang_failure.c' "$diagnostics"; then
    echo "missing source-qualified project Clang failure diagnostic" >&2
    cat "$diagnostics" >&2
    exit 1
fi
if ! rg -q 'error:' "$diagnostics"; then
    echo "compile-database Clang stderr was not captured and relayed" >&2
    cat "$diagnostics" >&2
    exit 1
fi
if [ -n "$(find "$project_output" -type f -print -quit)" ]; then
    echo "project translation left a generated unit after Clang failed" >&2
    exit 1
fi

set +e
"$transpiler" --compile-commands testdata/fixtures/clang_failure_cpp_compile_commands.json \
    --output-dir "$project_output" >"$output" 2>"$diagnostics"
status=$?
set -e

if [ "$status" -eq 0 ]; then
    echo "C++ compilation database accepted a source rejected by Clang++" >&2
    exit 1
fi
if [ -s "$output" ]; then
    echo "C++ project translation emitted stdout after Clang++ failed" >&2
    exit 1
fi
if ! rg -q 'Clang failed while processing testdata/fixtures/clang_failure.cpp' "$diagnostics"; then
    echo "missing source-qualified project Clang++ failure diagnostic" >&2
    cat "$diagnostics" >&2
    exit 1
fi
if [ -n "$(find "$project_output" -type f -print -quit)" ]; then
    echo "C++ project translation left a generated unit after Clang++ failed" >&2
    exit 1
fi

set +e
"$transpiler" --max-frontend-output-bytes 64 \
    --compile-commands testdata/fixtures/forward_compile_commands.json \
    --output-dir "$project_output" >"$output" 2>"$diagnostics"
status=$?
set -e

if [ "$status" -eq 0 ] || [ -s "$output" ] || \
    ! rg -q 'compilation database exceeded --max-frontend-output-bytes: testdata/fixtures/forward_compile_commands.json' "$diagnostics"; then
    echo "frontend byte limit did not reject an oversized compilation database" >&2
    cat "$diagnostics" >&2
    exit 1
fi
if [ -n "$(find "$project_output" -type f -print -quit)" ]; then
    echo "oversized compilation database left generated project files" >&2
    exit 1
fi

set +e
"$transpiler" --compile-commands testdata/fixtures/compile_command_shell_operator.json \
    --output-dir "$project_output" >"$output" 2>"$diagnostics"
status=$?
set -e

if [ "$status" -eq 0 ] || [ -s "$output" ] || \
    ! rg -q 'unsupported or malformed syntax in compilation command for testdata/fixtures/compile_command_quoted.c' "$diagnostics"; then
    echo "shell control syntax in a compilation command was not rejected safely" >&2
    cat "$diagnostics" >&2
    exit 1
fi
if [ -n "$(find "$project_output" -type f -print -quit)" ]; then
    echo "rejected shell command left generated project files" >&2
    exit 1
fi

# Reject malformed database commands before an earlier-sorting direct source
# can start Clang and report its unrelated source error.
set +e
"$transpiler" --compile-commands testdata/fixtures/compile_command_shell_operator.json \
    --output-dir "$project_output" testdata/fixtures/clang_failure.c \
    >"$output" 2>"$diagnostics"
status=$?
set -e

if [ "$status" -eq 0 ] || [ -s "$output" ] || \
    ! rg -q 'unsupported or malformed syntax in compilation command for testdata/fixtures/compile_command_quoted.c' "$diagnostics"; then
    echo "malformed compilation command was not rejected before translating another input" >&2
    cat "$diagnostics" >&2
    exit 1
fi
if [ -n "$(find "$project_output" -type f -print -quit)" ]; then
    echo "preflight-rejected compilation command left generated project files" >&2
    exit 1
fi

set +e
"$transpiler" --compile-commands testdata/fixtures/compile_command_missing_output.json \
    --output-dir "$project_output" >"$output" 2>"$diagnostics"
status=$?
set -e

if [ "$status" -eq 0 ] || [ -s "$output" ] || \
    ! rg -q 'unsupported or malformed syntax in compilation command for testdata/fixtures/compile_command_quoted.c' "$diagnostics"; then
    echo "malformed output option in compilation command was not rejected before launch" >&2
    cat "$diagnostics" >&2
    exit 1
fi
if [ -n "$(find "$project_output" -type f -print -quit)" ]; then
    echo "malformed output option left generated project files" >&2
    exit 1
fi

set +e
"$transpiler" --compile-commands testdata/fixtures/invalid_compile_command_arguments.json \
    --output-dir "$project_output" >"$output" 2>"$diagnostics"
status=$?
set -e

if [ "$status" -eq 0 ] || [ -s "$output" ] || \
    ! rg -q 'invalid compilation command for testdata/fixtures/compile_command_quoted.c' "$diagnostics"; then
    echo "malformed argv-array compilation command was not rejected cleanly" >&2
    cat "$diagnostics" >&2
    exit 1
fi
if [ -n "$(find "$project_output" -type f -print -quit)" ]; then
    echo "malformed argv-array compilation command left generated project files" >&2
    exit 1
fi

"$transpiler" --compile-commands testdata/fixtures/compile_command_quoted_command.json \
    --output-dir "$project_output" >"$output" 2>"$diagnostics"
if [ -s "$output" ] || ! rg -q 'return 42' "$project_output/compile_command_quoted.elisa"; then
    echo "quoted compilation-command arguments were not preserved" >&2
    cat "$diagnostics" >&2
    exit 1
fi

python3 - "$normalization_db" "$root_dir" <<'PY'
import json
import pathlib
import shlex
import sys

database, root = sys.argv[1:]
root_path = pathlib.Path(root)
source = "testdata/fixtures/compile_command_quoted.c"
include = "testdata/fixtures/quoted include"
command = (
    "ELISA_TRANSLATOR_LAUNCHER_TEST=1 clang -std=c11 -I "
    + shlex.quote(include)
    + " "
    + shlex.quote(source)
)
common = {
    "directory": str(root_path),
    "file": source,
}
command_entry = {**common, "command": command}
arguments_entry = {
    **common,
    "arguments": [
        "env", "ELISA_TRANSLATOR_LAUNCHER_TEST=1", "clang", "-std=c11",
        "-I", include, source,
    ],
}
pathlib.Path(database).write_text(json.dumps([command_entry, arguments_entry]), encoding="utf-8")
PY

set +e
"$transpiler" --compile-commands "$normalization_db" \
    --output-dir "$project_output" >"$output" 2>"$diagnostics"
launcher_status=$?
set -e
if [ "$launcher_status" -ne 0 ] || [ -s "$output" ] || \
    ! rg -q 'return 42' "$project_output/compile_command_quoted.elisa" || \
    [ -e "$project_output/compile_command_quoted_2.elisa" ] || \
    [ "$(rg -c '^include "compile_command_quoted.elisa"$' "$project_output/elisa_project.elisa")" -ne 1 ]; then
    echo "leading environment assignment and explicit env launcher did not normalize to one direct-argv translation" >&2
    cat "$diagnostics" >&2
    exit 1
fi

python3 - "$normalization_db" "$project_output" "$root_dir" <<'PY'
import json
import pathlib
import sys

database, directory, root = sys.argv[1:]
root_path = pathlib.Path(root)
source = root_path / "testdata/fixtures/compile_command_quoted.c"
include = root_path / "testdata/fixtures/quoted include"
entry = {
    "directory": directory,
    "file": str(source),
    "arguments": [
        "clang", "-std=c11", "-I" + str(include), "-MD", "-MF", "generated.d",
        "-MT", "compile_command_quoted.o", "-MQ", "quoted target", "-MJ",
        "generated.json", "-serialize-diagnostics", "generated.dia", "-save-temps",
        "-ftime-trace", "-c", "-o", "generated.o", str(source),
    ],
}
pathlib.Path(database).write_text(json.dumps([entry]), encoding="utf-8")
PY

"$transpiler" --compile-commands "$normalization_db" \
    --output-dir "$project_output" >"$output" 2>"$diagnostics"
if [ -s "$output" ] || ! rg -q 'return 42' "$project_output/compile_command_quoted.elisa"; then
    echo "output/dependency option normalization changed the source compilation context" >&2
    cat "$diagnostics" >&2
    exit 1
fi
for generated_file in generated.o generated.d generated.json generated.dia \
    compile_command_quoted.i compile_command_quoted.s; do
    if [ -e "$project_output/$generated_file" ]; then
        echo "AST extraction left build artifact after normalizing compiler options: $generated_file" >&2
        exit 1
    fi
done

"$transpiler" --compile-commands testdata/fixtures/compile_command_quoted_arguments.json \
    --output-dir "$project_output" >"$output" 2>"$diagnostics"
if [ -s "$output" ] || ! rg -q 'return 42' "$project_output/compile_command_quoted.elisa"; then
    echo "arguments-array compilation context was not preserved" >&2
    cat "$diagnostics" >&2
    exit 1
fi

"$transpiler" --compile-commands testdata/fixtures/language_override_compile_commands.json \
    --output-dir "$project_output" >"$output" 2>"$diagnostics"
if [ -s "$output" ] || ! rg -q 'return 42' "$project_output/language_override.elisa"; then
    echo "database -x, -std, or -D settings were not preserved for a .c source" >&2
    cat "$diagnostics" >&2
    exit 1
fi

"$transpiler" --compile-commands testdata/fixtures/compile_command_duplicate_exact.json \
    --output-dir "$project_output" >"$output" 2>"$diagnostics"
if [ -s "$output" ] || ! rg -q 'return 42' "$project_output/compile_command_quoted.elisa" || \
    [ -e "$project_output/compile_command_quoted_2.elisa" ] || \
    [ "$(rg -c '^include "compile_command_quoted.elisa"$' "$project_output/elisa_project.elisa")" -ne 1 ]; then
    echo "identical duplicate compilation entries were not collapsed to one translation" >&2
    cat "$diagnostics" >&2
    exit 1
fi

set +e
"$transpiler" --compile-commands testdata/fixtures/compile_command_duplicate_conflict.json \
    --output-dir "$conflict_output" >"$output" 2>"$diagnostics"
status=$?
set -e
if [ "$status" -eq 0 ] || [ -s "$output" ] || \
    ! rg -q 'conflicting compilation database entries for testdata/fixtures/compile_command_quoted.c' "$diagnostics" || \
    [ -n "$(find "$conflict_output" -type f -print -quit)" ]; then
    echo "conflicting compile commands were not rejected before emitting project files" >&2
    cat "$diagnostics" >&2
    exit 1
fi

python3 - "$normalization_db" "$root_dir" <<'PY'
import json
import pathlib
import sys

database, root = sys.argv[1:]
root_path = pathlib.Path(root)
source = str(root_path / "testdata/fixtures/compile_command_quoted.c")
alias = str(root_path / "testdata/fixtures/response") + "/../compile_command_quoted.c"
arguments = ["clang", "-I", str(root_path / "testdata/fixtures/quoted include"), source]
entries = [
    {"directory": str(root_path), "file": source, "arguments": arguments},
    {"directory": str(root_path), "file": alias, "arguments": arguments},
]
pathlib.Path(database).write_text(json.dumps(entries), encoding="utf-8")
PY

set +e
"$transpiler" --compile-commands "$normalization_db" \
    --output-dir "$project_output" >"$output" 2>"$diagnostics"
status=$?
set -e
if [ "$status" -ne 0 ] || [ -s "$output" ] || ! rg -q 'return 42' "$project_output/compile_command_quoted.elisa" || \
    [ -e "$project_output/compile_command_quoted_2.elisa" ] || \
    [ "$(rg -c '^include "compile_command_quoted.elisa"$' "$project_output/elisa_project.elisa")" -ne 1 ]; then
    echo "filesystem-alias duplicate compilation entries were not collapsed" >&2
    cat "$diagnostics" >&2
    exit 1
fi

python3 - "$normalization_db" "$root_dir" <<'PY'
import json
import pathlib
import sys

database, root = sys.argv[1:]
root_path = pathlib.Path(root)
source = str(root_path / "testdata/fixtures/compile_command_quoted.c")
alias = str(root_path / "testdata/fixtures/response") + "/../compile_command_quoted.c"
include = str(root_path / "testdata/fixtures/quoted include")
entries = [
    {"directory": str(root_path), "file": source, "arguments": ["clang", "-I", include, source]},
    {"directory": str(root_path), "file": alias, "arguments": ["clang", "-I", include, "-DTRANSLATOR_ALIAS_CONFLICT=1", source]},
]
pathlib.Path(database).write_text(json.dumps(entries), encoding="utf-8")
PY

set +e
"$transpiler" --compile-commands "$normalization_db" \
    --output-dir "$conflict_output" >"$output" 2>"$diagnostics"
status=$?
set -e
if [ "$status" -eq 0 ] || [ -s "$output" ] || \
    ! rg -q 'conflicting compilation database entries' "$diagnostics" || \
    [ -n "$(find "$conflict_output" -type f -print -quit)" ]; then
    echo "conflicting settings through a canonical source alias were not rejected" >&2
    cat "$diagnostics" >&2
    exit 1
fi

python3 - "$normalization_db" "$root_dir" <<'PY'
import json
import pathlib
import sys

database, root = sys.argv[1:]
root_path = pathlib.Path(root)
source = "testdata/fixtures/compile_command_quoted.c"
include = "testdata/fixtures/quoted include"
entries = [
    {
        "directory": str(root_path),
        "file": source,
        "command": f"clang -std=c11 -I'{include}' -c {source} -o /dev/null",
    },
    {
        "directory": str(root_path),
        "file": source,
        "arguments": ["clang", "-std=c11", "-I" + include, "-c", source, "-o", "/dev/null"],
    },
]
pathlib.Path(database).write_text(json.dumps(entries), encoding="utf-8")
PY

set +e
"$transpiler" --compile-commands "$normalization_db" \
    --output-dir "$project_output" >"$output" 2>"$diagnostics"
status=$?
set -e
if [ "$status" -ne 0 ] || [ -s "$output" ] || ! rg -q 'return 42' "$project_output/compile_command_quoted.elisa" || \
    [ -e "$project_output/compile_command_quoted_2.elisa" ] || \
    [ "$(rg -c '^include "compile_command_quoted.elisa"$' "$project_output/elisa_project.elisa")" -ne 1 ]; then
    echo "equivalent command and arguments entries were not compared by normalized argv" >&2
    cat "$diagnostics" >&2
    exit 1
fi

python3 - "$normalization_db" "$root_dir" <<'PY'
import json
import pathlib
import sys

database, root = sys.argv[1:]
root_path = pathlib.Path(root)
source = str(root_path / "testdata/fixtures/compile_command_quoted.c")
entries = [
    {
        "directory": str(root_path / "testdata/fixtures/response"),
        "file": source,
        "command": "clang @sub/outer.rsp",
    },
    {
        "directory": str(root_path / "testdata/fixtures/response"),
        "file": source,
        "arguments": ["clang", "@sub/outer.rsp"],
    },
]
pathlib.Path(database).write_text(json.dumps(entries), encoding="utf-8")
PY

set +e
"$transpiler" --compile-commands "$normalization_db" \
    --output-dir "$project_output" >"$output" 2>"$diagnostics"
status=$?
set -e
if [ "$status" -ne 0 ] || [ -s "$output" ] || ! rg -q 'return 42' "$project_output/compile_command_quoted.elisa" || \
    [ -e "$project_output/compile_command_quoted_2.elisa" ] || \
    [ "$(rg -c '^include "compile_command_quoted.elisa"$' "$project_output/elisa_project.elisa")" -ne 1 ]; then
    echo "equivalent response-file command and arguments entries were not normalized identically" >&2
    cat "$diagnostics" >&2
    exit 1
fi
for generated_file in response-generated.o response-generated.d response-generated.json \
    response-generated.dia compile_command_quoted.i compile_command_quoted.s; do
    if [ -e "testdata/fixtures/response/$generated_file" ]; then
        echo "response-file signature comparison left build artifact: $generated_file" >&2
        exit 1
    fi
done

python3 - "$normalization_db" "$root_dir" <<'PY'
import json
import pathlib
import sys

database, root = sys.argv[1:]
root_path = pathlib.Path(root)
source = "testdata/fixtures/compile_command_quoted.c"
include = "testdata/fixtures/quoted include"
entries = [
    {
        "directory": str(root_path),
        "file": source,
        "command": f"clang -std=c11 -I'{include}' -DTRANSLATOR_FORM_CONFLICT=1 {source}",
    },
    {
        "directory": str(root_path),
        "file": source,
        "arguments": ["clang", "-std=c11", "-I" + include, source],
    },
]
pathlib.Path(database).write_text(json.dumps(entries), encoding="utf-8")
PY

set +e
"$transpiler" --compile-commands "$normalization_db" \
    --output-dir "$conflict_output" >"$output" 2>"$diagnostics"
status=$?
set -e
if [ "$status" -eq 0 ] || [ -s "$output" ] || \
    ! rg -q 'conflicting compilation database entries' "$diagnostics" || \
    [ -n "$(find "$conflict_output" -type f -print -quit)" ]; then
    echo "different normalized argv across command/arguments forms was not rejected" >&2
    cat "$diagnostics" >&2
    exit 1
fi

for mismatch_form in command arguments; do
python3 - "$normalization_db" "$root_dir" "$mismatch_form" <<'PY'
import json
import pathlib
import sys

database, root, form = sys.argv[1:]
root_path = pathlib.Path(root)
entry = {
    "directory": str(root_path),
    "file": "testdata/fixtures/compile_command_quoted.c",
}
other_source = "testdata/fixtures/simple.c"
if form == "command":
    entry["command"] = f"clang {other_source}"
else:
    entry["arguments"] = ["clang", other_source]
pathlib.Path(database).write_text(json.dumps([entry]), encoding="utf-8")
PY

set +e
"$transpiler" --compile-commands "$normalization_db" \
    --output-dir "$conflict_output" >"$output" 2>"$diagnostics"
status=$?
set -e
if [ "$status" -eq 0 ] || [ -s "$output" ] || \
    ! rg -q 'compilation database file is not an input operand.*compile_command_quoted.c' "$diagnostics" || \
    [ -n "$(find "$conflict_output" -type f -print -quit)" ]; then
    echo "$mismatch_form entry compiled a source other than its database file" >&2
    cat "$diagnostics" >&2
    exit 1
fi
done

for mismatch_form in command arguments; do
python3 - "$normalization_db" "$mismatch_response" "$root_dir" "$mismatch_form" <<'PY'
import json
import pathlib
import sys

database, response_path, root, form = sys.argv[1:]
root_path = pathlib.Path(root)
pathlib.Path(response_path).write_text("testdata/fixtures/simple.c\n", encoding="utf-8")
entry = {
    "directory": str(root_path),
    "file": "testdata/fixtures/compile_command_quoted.c",
}
response_argument = "@" + response_path
if form == "command":
    entry["command"] = f"clang {response_argument}"
else:
    entry["arguments"] = ["clang", response_argument]
pathlib.Path(database).write_text(json.dumps([entry]), encoding="utf-8")
PY

set +e
"$transpiler" --compile-commands "$normalization_db" \
    --output-dir "$conflict_output" >"$output" 2>"$diagnostics"
status=$?
set -e
if [ "$status" -eq 0 ] || [ -s "$output" ] || \
    ! rg -q 'compilation database file is not an input operand.*compile_command_quoted.c' "$diagnostics" || \
    [ -n "$(find "$conflict_output" -type f -print -quit)" ]; then
    echo "$mismatch_form response-file source operand was not checked against the database file" >&2
    cat "$diagnostics" >&2
    exit 1
fi
done

"$transpiler" --compile-commands "testdata/fixtures/quoted include/compile_commands.json" \
    --output-dir "$project_output" >"$output" 2>"$diagnostics"
if [ -s "$output" ] || ! rg -q 'return 42' "$project_output/compile_command_quoted.elisa"; then
    echo "compile database path containing spaces was not read directly" >&2
    cat "$diagnostics" >&2
    exit 1
fi

"$transpiler" --compile-commands testdata/fixtures/response_compile_commands.json \
    --output-dir "$project_output" >"$output" 2>"$diagnostics"
if [ -s "$output" ] || ! rg -q 'return 42' "$project_output/compile_command_quoted.elisa"; then
    echo "nested response files did not preserve the compile directory, quoted include, or source" >&2
    cat "$diagnostics" >&2
    exit 1
fi
for generated_file in response-generated.o response-generated.d response-generated.json \
    response-generated.dia compile_command_quoted.i compile_command_quoted.s; do
    if [ -e "testdata/fixtures/response/$generated_file" ]; then
        echo "response-file AST extraction left build artifact: $generated_file" >&2
        exit 1
    fi
done

for response_command_form in command arguments; do
python3 - "$normalization_db" "$root_dir" "$response_command_form" <<'PY'
import json
import pathlib
import sys

database, root, command_form = sys.argv[1:]
root_path = pathlib.Path(root)
entry = {
    "directory": str(root_path / "testdata/fixtures/response"),
    "file": str(root_path / "testdata/fixtures/compile_command_quoted.c"),
}
if command_form == "command":
    entry["command"] = "clang @sub/outer.rsp"
else:
    entry["arguments"] = ["clang", "@sub/outer.rsp"]
pathlib.Path(database).write_text(json.dumps([entry]), encoding="utf-8")
PY

"$transpiler" --compile-commands "$normalization_db" \
    --output-dir "$project_output" >"$output" 2>"$diagnostics"
if [ -s "$output" ] || ! rg -q 'return 42' "$project_output/compile_command_quoted.elisa"; then
    echo "$response_command_form response-file source path did not match the compile database entry" >&2
    cat "$diagnostics" >&2
    exit 1
fi
done

for identity_form in command arguments; do
python3 - "$normalization_db" "$conflict_output" "$root_dir" "$identity_form" <<'PY'
import json
import pathlib
import shlex
import sys

database, temp_dir, root, form = sys.argv[1:]
root_path = pathlib.Path(root)
alias = pathlib.Path(temp_dir) / "identity_alias.c"
target = root_path / "testdata/fixtures/compile_command_quoted.c"
include = root_path / "testdata/fixtures/quoted include"
if alias.exists() or alias.is_symlink():
    alias.unlink()
alias.symlink_to(target)
entry = {
    "directory": str(root_path),
    "file": str(alias),
}
if form == "command":
    entry["command"] = (
        "clang -std=c11 -I " + shlex.quote(str(include)) + " "
        + shlex.quote(str(target))
    )
else:
    entry["arguments"] = [
        "clang", "-std=c11", "-I", str(include), str(target),
    ]
pathlib.Path(database).write_text(json.dumps([entry]), encoding="utf-8")
PY

"$transpiler" --compile-commands "$normalization_db" \
    --output-dir "$project_output" >"$output" 2>"$diagnostics"
if [ -s "$output" ] || ! rg -q 'return 42' "$project_output/identity_alias.elisa"; then
    echo "$identity_form failed to match the compile-db spelling to Clang's physical source path" >&2
    cat "$diagnostics" >&2
    exit 1
fi
done

python3 - "$normalization_db" "$conflict_output" "$root_dir" <<'PY'
import json
import pathlib
import sys

database, output_dir, root = sys.argv[1:]
source = pathlib.Path(root) / "testdata/fixtures/compile_command_quoted.c"
include = pathlib.Path(root) / "testdata/fixtures/quoted include"
directory = pathlib.Path(output_dir).resolve()
(directory / "empty.rsp").write_text("", encoding="utf-8")
entry = {
    "directory": str(directory),
    "file": str(source),
    "arguments": ["clang", "-I" + str(include), "@empty.rsp", str(source)],
}
pathlib.Path(database).write_text(json.dumps([entry]), encoding="utf-8")
PY

"$transpiler" --compile-commands "$normalization_db" \
    --output-dir "$project_output" >"$output" 2>"$diagnostics"
if [ -s "$output" ] || ! rg -q 'return 42' "$project_output/compile_command_quoted.elisa"; then
    echo "empty response files were not treated as empty argv expansions" >&2
    cat "$diagnostics" >&2
    exit 1
fi
unlink "$conflict_output/empty.rsp"

python3 - "$normalization_db" "$conflict_output" "$root_dir" <<'PY'
import json
import pathlib
import sys

database, output_dir, root = sys.argv[1:]
source = pathlib.Path(root) / "testdata/fixtures/compile_command_quoted.c"
entry = {
    "directory": str(pathlib.Path(output_dir).resolve()),
    "file": str(source),
    "arguments": ["clang", "@missing-response-file.rsp"],
}
pathlib.Path(database).write_text(json.dumps([entry]), encoding="utf-8")
PY

set +e
"$transpiler" --compile-commands "$normalization_db" \
    --output-dir "$conflict_output" >"$output" 2>"$diagnostics"
response_status=$?
set -e
if [ "$response_status" -eq 0 ] || [ -s "$output" ] || \
    ! rg -q 'could not read Clang response file .*missing-response-file.rsp while processing .*compile_command_quoted.c' "$diagnostics" || \
    [ -n "$(find "$conflict_output" -type f -print -quit)" ]; then
    echo "missing response file was not rejected before emitting project files" >&2
    cat "$diagnostics" >&2
    exit 1
fi

python3 - "$normalization_db" "$conflict_output" "$root_dir" <<'PY'
import json
import pathlib
import sys

database, output_dir, root = sys.argv[1:]
source = pathlib.Path(root) / "testdata/fixtures/simple.c"
directory = pathlib.Path(output_dir).resolve()
(directory / "malformed.rsp").write_text('"unterminated', encoding="utf-8")
entry = {
    "directory": str(directory),
    "file": str(source),
    "arguments": ["clang", "@malformed.rsp", str(source)],
}
pathlib.Path(database).write_text(json.dumps([entry]), encoding="utf-8")
PY

set +e
"$transpiler" --compile-commands "$normalization_db" \
    --output-dir "$conflict_output" >"$output" 2>"$diagnostics"
response_status=$?
set -e
if [ "$response_status" -eq 0 ] || [ -s "$output" ] || \
    ! rg -q 'malformed or unsupported quoting in Clang response file .*malformed.rsp while processing .*simple.c' "$diagnostics" || \
    [ -n "$(find "$conflict_output" -type f ! -name malformed.rsp -print -quit)" ]; then
    echo "malformed response-file quoting was not reported precisely before Clang launch" >&2
    cat "$diagnostics" >&2
    exit 1
fi
unlink "$conflict_output/malformed.rsp"

python3 - "$normalization_db" "$conflict_output" "$root_dir" <<'PY'
import json
import pathlib
import sys

database, output_dir, root = sys.argv[1:]
source = pathlib.Path(root) / "testdata/fixtures/simple.c"
directory = pathlib.Path(output_dir).resolve()
(directory / "oversized.rsp").write_text(" " * 1024, encoding="utf-8")
entry = {
    "directory": str(directory),
    "file": str(source),
    "arguments": ["clang", "@oversized.rsp", str(source)],
}
payload = json.dumps([entry])
if len(payload.encode("utf-8")) >= 512:
    raise SystemExit("oversized-response test database unexpectedly exceeds 512 bytes")
pathlib.Path(database).write_text(payload, encoding="utf-8")
PY

set +e
"$transpiler" --max-frontend-output-bytes 512 --compile-commands "$normalization_db" \
    --output-dir "$conflict_output" >"$output" 2>"$diagnostics"
response_status=$?
set -e
if [ "$response_status" -eq 0 ] || [ -s "$output" ] || \
    ! rg -q 'response-file expansion exceeded --max-frontend-output-bytes while reading .*oversized.rsp while processing .*simple.c' "$diagnostics" || \
    [ -n "$(find "$conflict_output" -type f ! -name oversized.rsp -print -quit)" ]; then
    echo "response-file byte budget was not enforced before Clang launch" >&2
    cat "$diagnostics" >&2
    exit 1
fi
unlink "$conflict_output/oversized.rsp"

python3 - "$normalization_db" "$conflict_output" "$root_dir" <<'PY'
import json
import pathlib
import sys

database, output_dir, root = sys.argv[1:]
source = pathlib.Path(root) / "testdata/fixtures/simple.c"
directory = pathlib.Path(output_dir).resolve()
(directory / "cycle.rsp").write_text("@cycle.rsp", encoding="utf-8")
entry = {
    "directory": str(directory),
    "file": str(source),
    "arguments": ["clang", "@cycle.rsp", str(source)],
}
pathlib.Path(database).write_text(json.dumps([entry]), encoding="utf-8")
PY

set +e
"$transpiler" --compile-commands "$normalization_db" \
    --output-dir "$conflict_output" >"$output" 2>"$diagnostics"
response_status=$?
set -e
if [ "$response_status" -eq 0 ] || [ -s "$output" ] || \
    ! rg -q 'response-file nesting exceeded the maximum depth of 16 at .*cycle.rsp while processing .*simple.c' "$diagnostics" || \
    [ -n "$(find "$conflict_output" -type f ! -name cycle.rsp -print -quit)" ]; then
    echo "cyclic response files were not rejected at the bounded nesting depth" >&2
    cat "$diagnostics" >&2
    exit 1
fi
unlink "$conflict_output/cycle.rsp"

python3 - "$transaction_db" "$transaction_output" "$root_dir" <<'PY'
import json
import pathlib
import sys

database, output_dir, root = sys.argv[1:]
output = pathlib.Path(output_dir).resolve()
broken = output / "zz_transaction_failure.c"
broken.write_text("int broken( {\n", encoding="utf-8")
simple = pathlib.Path(root) / "testdata/fixtures/simple.c"
payload = [
    {
        "directory": str(pathlib.Path(root).resolve()),
        "file": str(simple.resolve()),
        "command": "clang -std=c11 -c testdata/fixtures/simple.c",
    },
    {
        "directory": str(output),
        "file": str(broken),
        "command": f"clang -std=c11 -c {broken}",
    },
]
pathlib.Path(database).write_text(json.dumps(payload), encoding="utf-8")
(output / "simple.elisa").write_text("previous simple generation\n", encoding="utf-8")
(output / "elisa_project.elisa").write_text("previous project generation\n", encoding="utf-8")
PY

set +e
"$transpiler" --compile-commands "$transaction_db" \
    --output-dir "$transaction_output" >"$output" 2>"$diagnostics"
transaction_exit=$?
set -e
if [ "$transaction_exit" -eq 0 ] || [ -s "$output" ] || \
    ! rg -q 'Clang failed while processing' "$diagnostics" || \
    [ "$(<"$transaction_output/simple.elisa")" != "previous simple generation" ] || \
    [ "$(<"$transaction_output/elisa_project.elisa")" != "previous project generation" ] || \
    [ -e "$transaction_output/zz_transaction_failure.elisa" ] || \
    [ -n "$(find "$transaction_output" -maxdepth 1 -type f \
        ! -name 'zz_transaction_failure.c' \
        ! -name 'simple.elisa' \
        ! -name 'elisa_project.elisa' -print -quit)" ]; then
    echo "failed project translation changed existing outputs or left staging files" >&2
    cat "$diagnostics" >&2
    exit 1
fi

echo "frontend checks OK (C/C++, byte/node bounds, raw JSON validation, independent diagnostics, stats invariance, failures, validated argv, normalized options, source identity, nested/empty/bounded response files and precise response diagnostics)"
