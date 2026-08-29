#!/bin/sh
set -eu

root_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root_dir"

if [ -n "${ELISAC_BIN:-}" ]; then
    elisa_bin=$ELISAC_BIN
elif command -v elisac >/dev/null 2>&1; then
    elisa_bin=$(command -v elisac)
else
    elisa_bin="$HOME/.elisac/elisac"
fi

mkdir -p build

"$elisa_bin" -emit obj -O0 -o build/transpiler.o src/main.elisa
clang -Wl,-dead_strip -o build/elisa-c-transpiler build/transpiler.o -lm

./build/elisa-c-transpiler testdata/fixtures/simple.c > build/simple.generated.elisa
rg -q '^def add\(left: i32, right: i32\) -> i32' build/simple.generated.elisa
rg -q 'return \(left \+ right\)' build/simple.generated.elisa
rg -q '^def main\(\) -> i32' build/simple.generated.elisa
! rg -q '^def elisa_nonnull' build/simple.generated.elisa
! rg -q '^extern va_list' build/simple.generated.elisa
"$elisa_bin" -emit obj -O0 -o build/simple.generated.o build/simple.generated.elisa
clang -Wl,-dead_strip -o build/simple.generated build/simple.generated.o
set +e
./build/simple.generated
simple_rc=$?
set -e
if [ "$simple_rc" -ne 42 ]; then
    echo "simple fixture returned $simple_rc, expected 42" >&2
    exit 1
fi

./build/elisa-c-transpiler --fidelity testdata/fixtures/simple.c > build/simple.fidelity.elisa
rg -q '^def add\(left: mutable i32, right: mutable i32\) -> i32' build/simple.fidelity.elisa

./build/elisa-c-transpiler testdata/fixtures/generic_nonnull.c > build/generic_nonnull.generated.elisa
rg -Fq 'def elisa_nonnull[T](value: mutable T&?) -> mutable T&:' build/generic_nonnull.generated.elisa
! rg -q '^def elisa_nonnull_' build/generic_nonnull.generated.elisa
[ "$(rg -c '^def elisa_nonnull' build/generic_nonnull.generated.elisa)" -eq 1 ]
rg -Fq 'elisa_nonnull(byte)' build/generic_nonnull.generated.elisa
rg -Fq 'elisa_nonnull(number)' build/generic_nonnull.generated.elisa
rg -Fq 'elisa_nonnull(sample)' build/generic_nonnull.generated.elisa
rg -Fq 'elisa_nonnull(text)' build/generic_nonnull.generated.elisa
clang -std=c11 testdata/fixtures/generic_nonnull.c -o build/generic_nonnull.native
"$elisa_bin" -emit obj -O0 -o build/generic_nonnull.generated.o build/generic_nonnull.generated.elisa
clang -Wl,-dead_strip -o build/generic_nonnull.generated build/generic_nonnull.generated.o
set +e
./build/generic_nonnull.native
generic_nonnull_native_rc=$?
./build/generic_nonnull.generated
generic_nonnull_generated_rc=$?
set -e
[ "$generic_nonnull_native_rc" -eq 0 ] && [ "$generic_nonnull_generated_rc" -eq 0 ]

./build/elisa-c-transpiler testdata/fixtures/integer_conversions.c > build/integer_conversions.generated.elisa
rg -q 'return \(\(left\)\.i32\(\) \+ \(right\)\.i32\(\)\)' build/integer_conversions.generated.elisa
clang -std=c11 testdata/fixtures/integer_conversions.c -o build/integer_conversions.native
"$elisa_bin" -emit obj -O0 -o build/integer_conversions.generated.o build/integer_conversions.generated.elisa
clang -Wl,-dead_strip -o build/integer_conversions.generated build/integer_conversions.generated.o
set +e
./build/integer_conversions.native
integer_native_rc=$?
./build/integer_conversions.generated
integer_generated_rc=$?
set -e
[ "$integer_native_rc" -eq 0 ] && [ "$integer_generated_rc" -eq 0 ]

./build/elisa-c-transpiler testdata/fixtures/aggregate.c > build/aggregate.generated.elisa
rg -q '# A small aggregate exercises C' build/aggregate.generated.elisa
rg -q '# The translator should preserve this declaration' build/aggregate.generated.elisa
rg -q 'Pair\{first: 7, second: zeroed, third: zeroed\}' build/aggregate.generated.elisa
clang -std=c11 testdata/fixtures/aggregate.c -o build/aggregate.native
"$elisa_bin" -emit obj -O0 -o build/aggregate.generated.o build/aggregate.generated.elisa
clang -Wl,-dead_strip -o build/aggregate.generated build/aggregate.generated.o
./build/aggregate.native
./build/aggregate.generated

./build/elisa-c-transpiler testdata/fixtures/enum_flags.c > build/enum_flags.generated.elisa
rg -q 'Mode\.MODE_BOTH' build/enum_flags.generated.elisa
clang -std=c11 testdata/fixtures/enum_flags.c -o build/enum_flags.native
"$elisa_bin" -emit obj -O0 -o build/enum_flags.generated.o build/enum_flags.generated.elisa
clang -Wl,-dead_strip -o build/enum_flags.generated build/enum_flags.generated.o
./build/enum_flags.native
./build/enum_flags.generated

./build/elisa-c-transpiler testdata/fixtures/function_pointer.c > build/function_pointer.generated.elisa
! rg -q '^extern operation\(' build/function_pointer.generated.elisa
clang -std=c11 testdata/fixtures/function_pointer.c -o build/function_pointer.native
"$elisa_bin" -emit obj -O0 -o build/function_pointer.generated.o build/function_pointer.generated.elisa
clang -Wl,-dead_strip -o build/function_pointer.generated build/function_pointer.generated.o
set +e
./build/function_pointer.native
function_pointer_native_rc=$?
./build/function_pointer.generated
function_pointer_generated_rc=$?
set -e
[ "$function_pointer_native_rc" -eq 0 ] && [ "$function_pointer_generated_rc" -eq 0 ]

./build/elisa-c-transpiler testdata/fixtures/name_collision.c > build/name_collision.generated.elisa
rg -q '^def elisa_initialize_globals\(' build/name_collision.generated.elisa
rg -q 'elisa_initialize_globals\(\)' build/name_collision.generated.elisa
! rg -q '^def initialize_globals\(' build/name_collision.generated.elisa
"$elisa_bin" -emit obj -O0 -o build/name_collision.generated.o build/name_collision.generated.elisa
clang -Wl,-dead_strip -o build/name_collision.generated build/name_collision.generated.o
clang -std=c11 testdata/fixtures/name_collision.c -o build/name_collision.native
set +e
./build/name_collision.native
name_collision_native_rc=$?
./build/name_collision.generated
name_collision_generated_rc=$?
set -e
[ "$name_collision_native_rc" -eq 0 ] && [ "$name_collision_generated_rc" -eq 0 ]

./build/elisa-c-transpiler testdata/fixtures/backward_goto.c > build/backward_goto.generated.elisa
rg -q 'control_state: mutable i32 = 0' build/backward_goto.generated.elisa
clang -std=c11 testdata/fixtures/backward_goto.c -o build/backward_goto.native
"$elisa_bin" -emit obj -O0 -o build/backward_goto.generated.o build/backward_goto.generated.elisa
clang -Wl,-dead_strip -o build/backward_goto.generated build/backward_goto.generated.o
set +e
./build/backward_goto.native
backward_native_rc=$?
./build/backward_goto.generated
backward_generated_rc=$?
set -e
[ "$backward_native_rc" -eq 0 ] && [ "$backward_generated_rc" -eq 0 ]

./build/elisa-c-transpiler testdata/fixtures/structured_loop_goto.c > build/structured_loop_goto.generated.elisa
! rg -q 'control_state|goto_state|flow_state' build/structured_loop_goto.generated.elisa
rg -q 'break' build/structured_loop_goto.generated.elisa
clang -std=c11 testdata/fixtures/structured_loop_goto.c -o build/structured_loop_goto.native
"$elisa_bin" -emit obj -O0 -o build/structured_loop_goto.generated.o build/structured_loop_goto.generated.elisa
clang -Wl,-dead_strip -o build/structured_loop_goto.generated build/structured_loop_goto.generated.o
set +e
./build/structured_loop_goto.native
structured_native_rc=$?
./build/structured_loop_goto.generated
structured_generated_rc=$?
set -e
[ "$structured_native_rc" -eq 0 ] && [ "$structured_generated_rc" -eq 0 ]

./build/elisa-c-transpiler testdata/fixtures/switch.c > build/switch.generated.elisa
rg -q 'match value:' build/switch.generated.elisa
rg -q '^[[:space:]]+0:' build/switch.generated.elisa
rg -q '^[[:space:]]+5:' build/switch.generated.elisa
clang -std=c11 testdata/fixtures/switch.c -o build/switch.native
"$elisa_bin" -emit obj -O0 -o build/switch.generated.o build/switch.generated.elisa
clang -Wl,-dead_strip -o build/switch.generated build/switch.generated.o
set +e
./build/switch.native
switch_native_rc=$?
./build/switch.generated
switch_generated_rc=$?
set -e
[ "$switch_native_rc" -eq 0 ] && [ "$switch_generated_rc" -eq 0 ]

mkdir -p build/project-db
./build/elisa-c-transpiler --compile-commands testdata/fixtures/compile_commands.json \
    --output-dir build/project-db
rg -q 'include "module_a.elisa"' build/project-db/elisa_project.elisa
rg -q 'include "module_a_2.elisa"' build/project-db/elisa_project.elisa
rg -q 'include "module_b.elisa"' build/project-db/elisa_project.elisa
rg -q 'return \(value \+ 1\)' build/project-db/module_a.elisa
"$elisa_bin" -emit obj -O0 -o build/project-db/project.o build/project-db/elisa_project.elisa
clang -Wl,-dead_strip -o build/project-db/project build/project-db/project.o
set +e
./build/project-db/project
project_generated_rc=$?
set -e
[ "$project_generated_rc" -eq 0 ]

./build/elisa-c-transpiler testdata/fixtures/nested_loop_goto.c > build/nested_loop_goto.generated.elisa
rg -q 'control_state: mutable i32 = 0|goto_state: mutable i32 = 0' build/nested_loop_goto.generated.elisa
clang -std=c11 testdata/fixtures/nested_loop_goto.c -o build/nested_loop_goto.native
"$elisa_bin" -emit obj -O0 -o build/nested_loop_goto.generated.o build/nested_loop_goto.generated.elisa
clang -Wl,-dead_strip -o build/nested_loop_goto.generated build/nested_loop_goto.generated.o
set +e
./build/nested_loop_goto.native
nested_native_rc=$?
./build/nested_loop_goto.generated
nested_generated_rc=$?
set -e
[ "$nested_native_rc" -eq 0 ] && [ "$nested_generated_rc" -eq 0 ]

set +e
./build/elisa-c-transpiler testdata/fixtures/unsupported_for.c \
    > build/unsupported_for.out 2> build/unsupported_for.err
unsupported_for_rc=$?
set -e
[ "$unsupported_for_rc" -ne 0 ]
[ ! -s build/unsupported_for.out ]
rg -q "elisa-c-transpiler: unsupported statement GotoStmt at" build/unsupported_for.err

ini_root=testdata/upstream/inih
clang -std=c11 -DINI_USE_STACK=1 -I "$ini_root" -c "$ini_root/ini.c" -o build/ini.o
clang -std=c11 -DINI_USE_STACK=1 -I "$ini_root" -I "$ini_root/examples" \
    "$ini_root/examples/ini_dump.c" "$ini_root/ini.c" -o build/ini_dump.native

./build/elisa-c-transpiler "$ini_root/examples/ini_dump.c" > build/ini_dump.generated.elisa
# C library bindings must come from Clang declarations. Their source spellings
# are retained; no target function gets a translator-owned ABI entry just
# because its spelling is printf, strncpy, strcmp, or something similar.
rg -q '^extern (printf|strncpy|strcmp|ini_parse)\b' build/ini_dump.generated.elisa
rg -q '^@link_name\("printf"\)$' build/ini_dump.generated.elisa
! rg -q '^extern __c_ext_[0-9]+\(' build/ini_dump.generated.elisa
"$elisa_bin" -emit obj -O0 -o build/ini_dump.generated.o build/ini_dump.generated.elisa
clang -Wl,-dead_strip -o build/ini_dump.generated build/ini_dump.generated.o build/ini.o -lm

./build/ini_dump.native "$ini_root/examples/test.ini" > build/ini_dump.native.output.txt
./build/ini_dump.generated "$ini_root/examples/test.ini" > build/ini_dump.output.txt
cmp build/ini_dump.native.output.txt build/ini_dump.output.txt

set +e
./build/ini_dump.native > build/ini_dump.noarg.native.out 2> build/ini_dump.noarg.native.err
native_noarg_rc=$?
./build/ini_dump.generated > build/ini_dump.noarg.generated.out 2> build/ini_dump.noarg.generated.err
generated_noarg_rc=$?
./build/ini_dump.native /definitely/missing.ini > build/ini_dump.missing.native.out 2> build/ini_dump.missing.native.err
native_missing_rc=$?
./build/ini_dump.generated /definitely/missing.ini > build/ini_dump.missing.generated.out 2> build/ini_dump.missing.generated.err
generated_missing_rc=$?
set -e

[ "$native_noarg_rc" -eq 1 ] && [ "$generated_noarg_rc" -eq 1 ]
cmp build/ini_dump.noarg.native.out build/ini_dump.noarg.generated.out
cmp build/ini_dump.noarg.native.err build/ini_dump.noarg.generated.err
[ "$native_missing_rc" -eq 2 ] && [ "$generated_missing_rc" -eq 2 ]
cmp build/ini_dump.missing.native.out build/ini_dump.missing.generated.out
cmp build/ini_dump.missing.native.err build/ini_dump.missing.generated.err

cjson_root=testdata/upstream/cJSON
clang -std=c11 -I "$cjson_root" \
    "$cjson_root/cjson_smoke.c" -lm -o build/cjson.native

./build/elisa-c-transpiler "$cjson_root/cjson_smoke.c" > build/cjson.generated.elisa
rg -q '^def cJSON_Parse\(' build/cjson.generated.elisa
rg -q '^def cJSON_PrintUnformatted\(' build/cjson.generated.elisa
rg -q '^def cJSON_Delete\(' build/cjson.generated.elisa
rg -q '^def cJSON_Delete\(item: mutable CJSON&\?\)' build/cjson.generated.elisa
rg -q 'item_cursor: mutable CJSON&\? = item' build/cjson.generated.elisa
! rg -q '_param|__c_ext_|__c_global_' build/cjson.generated.elisa
rg -q 'size_of\[CJSON\]' build/cjson.generated.elisa
rg -q 'size_of\[Printbuffer\] \* 1' build/cjson.generated.elisa
! rg -q '^extern (printf|cJSON_Parse|cJSON_Delete)\b' build/cjson.generated.elisa
rg -q '^@link_name\("printf"\)$' build/cjson.generated.elisa
"$elisa_bin" -emit obj -O0 -o build/cjson.generated.o build/cjson.generated.elisa
clang -Wl,-dead_strip -o build/cjson.generated build/cjson.generated.o -lm

./build/cjson.native > build/cjson.native.output.txt
./build/cjson.generated > build/cjson.output.txt
cmp build/cjson.native.output.txt build/cjson.output.txt

kilo_root=testdata/upstream/kilo
clang -std=c11 "$kilo_root/kilo.c" -o build/kilo.native
./build/elisa-c-transpiler "$kilo_root/kilo.c" > build/kilo.generated.elisa
rg -q '^def editorSetStatusMessage\(fmt: mutable u8&\?, \.\.\.\) -> void' build/kilo.generated.elisa
rg -q '^extern c_memset\(' build/kilo.generated.elisa
rg -q '^@link_name\("memset"\)$' build/kilo.generated.elisa
! rg -q '^extern memset\(' build/kilo.generated.elisa
rg -q 'llvm_va_start\(\(&ap\)\.cast\[mutable void&\]\)' build/kilo.generated.elisa
rg -q 'llvm_va_end\(\(&ap\)\.cast\[mutable void&\]\)' build/kilo.generated.elisa
! rg -q 'bridge required|kilo_varargs' build/kilo.generated.elisa
"$elisa_bin" -emit obj -O0 -o build/kilo.generated.o build/kilo.generated.elisa
clang -Wl,-dead_strip -o build/kilo.generated build/kilo.generated.o -lm

set +e
./build/kilo.native > build/kilo.noarg.native.out 2> build/kilo.noarg.native.err
kilo_native_rc=$?
./build/kilo.generated > build/kilo.noarg.generated.out 2> build/kilo.noarg.generated.err
kilo_generated_rc=$?
set -e
[ "$kilo_native_rc" -eq 1 ] && [ "$kilo_generated_rc" -eq 1 ]
cmp build/kilo.noarg.native.out build/kilo.noarg.generated.out
cmp build/kilo.noarg.native.err build/kilo.noarg.generated.err

echo "translator acceptance tests passed"
