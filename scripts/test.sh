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
rg -q '^def add\(left: mutable i32, right: mutable i32\) -> i32' build/simple.generated.elisa
rg -q 'return \(left \+ right\)' build/simple.generated.elisa
rg -q '^def main\(\) -> i32' build/simple.generated.elisa
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
# C library bindings must come from Clang declarations. The generated Elisa
# names are opaque aliases; no target function gets a translator-owned ABI
# entry just because its spelling is printf, strncpy, or something similar.
! rg -q '^extern (printf|strncpy|strcmp|ini_parse)\b' build/ini_dump.generated.elisa
rg -q '^@link_name\("printf"\)$' build/ini_dump.generated.elisa
rg -q '^extern __c_ext_[0-9]+\(' build/ini_dump.generated.elisa
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

kilo_root=testdata/upstream/kilo
clang -std=c11 "$kilo_root/kilo.c" -o build/kilo.native
./build/elisa-c-transpiler "$kilo_root/kilo.c" > build/kilo.generated.elisa
rg -q '^def editorSetStatusMessage\(fmt: cstr, \.\.\.\) -> void' build/kilo.generated.elisa
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
