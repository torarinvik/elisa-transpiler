# Small upstream smoke programs: inih, cJSON and Kilo.
translator_bin=${ELISA_TRANSLATOR_BIN:-./build/elisa-c-transpiler}
ini_root=testdata/upstream/inih
clang -std=c11 -DINI_USE_STACK=1 -I "$ini_root" -c "$ini_root/ini.c" -o build/ini.o
clang -std=c11 -DINI_USE_STACK=1 -I "$ini_root" -I "$ini_root/examples" \
    "$ini_root/examples/ini_dump.c" "$ini_root/ini.c" -o build/ini_dump.native

test_translator_bounded "$ini_root/examples/ini_dump.c" > build/ini_dump.generated.elisa
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
cjson_smoke=testdata/fixtures/cjson_smoke.c
clang -std=c11 -I "$cjson_root" \
    "$cjson_smoke" -lm -o build/cjson.native

test_translator_bounded "$cjson_smoke" > build/cjson.generated.elisa
rg -q '^struct Parse_buffer:$' build/cjson.generated.elisa
# These C fields are `const unsigned char *`: their POINTER SLOTS and the other
# parser-state fields are assigned during parsing. Elisa's field-level
# `mutable` preserves those assignments; the expression-level readonly helper
# below checks that C's pointee constness was not discarded.
rg -q '^    content: mutable u8&\?$' build/cjson.generated.elisa
rg -q '^    length: mutable u64$' build/cjson.generated.elisa
rg -q '^    offset: mutable u64$' build/cjson.generated.elisa
rg -q '^    depth: mutable u64$' build/cjson.generated.elisa
rg -q '^    hooks: mutable Internal_hooks$' build/cjson.generated.elisa
rg -q '^struct C_error:$' build/cjson.generated.elisa
# Error details are populated when parsing fails; `json`'s pointee is still
# const even though its pointer slot is mutable.
rg -q '^    json: mutable u8&\?$' build/cjson.generated.elisa
rg -q '^    position: mutable u64$' build/cjson.generated.elisa
rg -Fq 'elisa_nonnull_readonly(elisa_nonnull(input_buffer).content)' build/cjson.generated.elisa
rg -q 'elisa_nonnull_readonly\(\(local_error\.json\)\.cast' build/cjson.generated.elisa
rg -q '^def cJSON_Parse\(' build/cjson.generated.elisa
rg -q '^def cJSON_PrintUnformatted\(' build/cjson.generated.elisa
rg -q '^def cJSON_Delete\(' build/cjson.generated.elisa
rg -q '^def cJSON_Delete\(item: mutable CJSON&\?\)' build/cjson.generated.elisa
rg -q 'item_cursor: mutable mutable CJSON&\? = item' build/cjson.generated.elisa
! rg -q '_param|__c_ext_|__c_global_' build/cjson.generated.elisa
rg -q 'size_of\[CJSON\]' build/cjson.generated.elisa
! rg -q 'size_of\[Printbuffer\] \* 1' build/cjson.generated.elisa
! rg -q '\(null\)\.i32|\.i32\(\) == \(null\)' build/cjson.generated.elisa
! rg -q '^extern (printf|cJSON_Parse|cJSON_Delete)\b' build/cjson.generated.elisa
rg -q '^@link_name\("printf"\)$' build/cjson.generated.elisa
if [ "$optional_fn_supported" -eq 1 ]; then
    "$elisa_bin" -emit obj -O0 -o build/cjson.generated.o build/cjson.generated.elisa
    clang -Wl,-dead_strip -o build/cjson.generated build/cjson.generated.o -lm

    ./build/cjson.native > build/cjson.native.output.txt
    ./build/cjson.generated > build/cjson.output.txt
    cmp build/cjson.native.output.txt build/cjson.output.txt
fi

# Exercise the full recursive implementation as a bounded translation/resource
# regression. The translator rules remain generic; this corpus catches runaway
# recursive effect analysis without requiring backend acceptance of every body.
python3 scripts/run_bounded_process.py \
    --max-rss-kb "${ELISA_TRANSLATOR_FULL_CJSON_MAX_RSS_KB:-524288}" \
    --timeout-seconds "${ELISA_TRANSLATOR_FULL_CJSON_TIMEOUT_SECONDS:-180}" -- \
    sh -c 'exec "$1" "$2" > "$3"' sh \
    "$translator_bin" "$cjson_root/cJSON.c" build/cjson.full.generated.elisa
rg -q '^def cJSON_Compare\(' build/cjson.full.generated.elisa
rg -q '^def cJSON_Parse\(' build/cjson.full.generated.elisa
rg -q '^def cJSON_PrintUnformatted\(' build/cjson.full.generated.elisa
[ "$(wc -c < build/cjson.full.generated.elisa | tr -d ' ')" -gt 100000 ]

kilo_root=testdata/upstream/kilo
clang -std=c11 "$kilo_root/kilo.c" -o build/kilo.native
test_translator_bounded "$kilo_root/kilo.c" > build/kilo.generated.elisa
rg -q '^def editorSetStatusMessage\(fmt: (i8|u8)&\?, \.\.\.\) -> void' build/kilo.generated.elisa
rg -Fq 'atexit((editorAtExit).cast[void&])' build/kilo.generated.elisa
! rg -q '^extern memset\(' build/kilo.generated.elisa
# Depending on the Clang SDK's fortify defaults, memset is either exposed as
# the ordinary C binding (renamed to avoid the Elisa runtime collision) or as
# Clang's checked intrinsic wrapper. Both must retain Clang's actual link ABI.
if rg -q '^extern c_memset\(' build/kilo.generated.elisa; then
    rg -q '^@link_name\("memset"\)$' build/kilo.generated.elisa
else
    rg -q '^extern __builtin___memset_chk\(' build/kilo.generated.elisa
    rg -q '^@link_name\("__memset_chk"\)$' build/kilo.generated.elisa
fi
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
