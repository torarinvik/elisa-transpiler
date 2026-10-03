# Fidelity output remains a dedicated structural assertion; idiomatic mode,
# compiler/link checks and differential execution use the manifest runner.
link_core_fixture_harness() {
    harness_name=$1
    harness_object=$2
    if [ -n "$elisa_runtime" ]; then
        clang -Wl,-dead_strip -o "$harness_name" "$harness_object" "$elisa_runtime"
    elif [ -n "$profile_hooks" ]; then
        clang -Wl,-dead_strip -o "$harness_name" "$harness_object" "$profile_hooks"
    else
        clang -Wl,-dead_strip -o "$harness_name" "$harness_object"
    fi
}

"$elisa_bin" -emit obj -O0 -o build/ast_projection_schema_test.o testdata/ast_projection_schema_test.elisa
link_core_fixture_harness build/ast_projection_schema_test build/ast_projection_schema_test.o
./build/ast_projection_schema_test

"$elisa_bin" -emit obj -O0 -o build/clang_type_view_test.o testdata/clang_type_view_test.elisa
link_core_fixture_harness build/clang_type_view_test build/clang_type_view_test.o
./build/clang_type_view_test

"$elisa_bin" -emit obj -O0 -o build/clang_diagnostic_categories_test.o testdata/clang_diagnostic_categories_test.elisa
link_core_fixture_harness build/clang_diagnostic_categories_test build/clang_diagnostic_categories_test.o
./build/clang_diagnostic_categories_test

"$elisa_bin" -emit obj -O0 -o build/clang_diagnostic_origins_test.o testdata/clang_diagnostic_origins_test.elisa
link_core_fixture_harness build/clang_diagnostic_origins_test build/clang_diagnostic_origins_test.o
./build/clang_diagnostic_origins_test

"$elisa_bin" -emit obj -O0 -o build/emit_format_origins_test.o testdata/emit_format_origins_test.elisa
link_core_fixture_harness build/emit_format_origins_test build/emit_format_origins_test.o
./build/emit_format_origins_test

"$elisa_bin" -emit obj -O0 -o build/clang_type_shape_test.o testdata/clang_type_shape_test.elisa
link_core_fixture_harness build/clang_type_shape_test build/clang_type_shape_test.o
./build/clang_type_shape_test

"$elisa_bin" -emit obj -O0 -o build/typed_ir_verifier_test.o testdata/typed_ir_verifier_test.elisa
link_core_fixture_harness build/typed_ir_verifier_test build/typed_ir_verifier_test.o
./build/typed_ir_verifier_test

./build/elisa-c-transpiler --fidelity testdata/fixtures/simple.c > build/simple.fidelity.elisa
rg -q '^def add\(left: mutable i32, right: mutable i32\) -> i32' build/simple.fidelity.elisa

./build/elisa-c-transpiler testdata/fixtures/simple.c > build/simple.idiomatic.elisa
if clang++ -std=gnu++11 -fsyntax-only testdata/fixtures/cpp_scoped_enum_implicit_conversion_unsupported.cpp \
    > build/cpp_scoped_enum_implicit_conversion.clang.stdout \
    2> build/cpp_scoped_enum_implicit_conversion.clang.stderr; then
    echo "expected Clang to reject implicit conversion from a scoped enum to int" >&2
    exit 1
fi
if ./build/elisa-c-transpiler testdata/fixtures/cpp_scoped_enum_implicit_conversion_unsupported.cpp \
    > build/cpp_scoped_enum_implicit_conversion.translator.stdout \
    2> build/cpp_scoped_enum_implicit_conversion.translator.stderr; then
    echo "expected the translator's Clang frontend to reject scoped-enum implicit conversion" >&2
    exit 1
fi
[ ! -s build/cpp_scoped_enum_implicit_conversion.translator.stdout ]
[ "$(rg -c 'cannot initialize return object of type' build/cpp_scoped_enum_implicit_conversion.translator.stderr)" -eq 2 ]
python3 scripts/test_diagnostics_json.py
python3 scripts/test_source_map.py
python3 scripts/test_rewrite_explanations.py
./build/elisa-c-transpiler testdata/fixtures/external_abi_recovery.c > build/external_abi_recovery.generated.elisa
rg -q '^extern (strcpy|__builtin___strcpy_chk)\([^)]' build/external_abi_recovery.generated.elisa
rg -q '^extern (snprintf|__builtin___snprintf_chk)\([^)]' build/external_abi_recovery.generated.elisa
! rg -q 'size_of\[i8\] \* 32\)\[0\]' build/external_abi_recovery.generated.elisa
clang -std=c11 testdata/fixtures/external_abi_recovery.c -o build/external_abi_recovery.native
"$elisa_bin" -emit obj -O0 -o build/external_abi_recovery.generated.o build/external_abi_recovery.generated.elisa
clang -Wl,-dead_strip -o build/external_abi_recovery.generated build/external_abi_recovery.generated.o
set +e
./build/external_abi_recovery.native
external_abi_native_rc=$?
./build/external_abi_recovery.generated
external_abi_generated_rc=$?
set -e
[ "$external_abi_native_rc" -eq "$external_abi_generated_rc" ]

if ./build/elisa-c-transpiler testdata/fixtures/pointer_difference_unknown_layout.c \
    > build/pointer_difference_unknown_layout.stdout.elisa \
    2> build/pointer_difference_unknown_layout.diagnostics; then
    echo "expected pointer subtraction with unknown record layout to fail closed" >&2
    exit 1
fi
[ ! -s build/pointer_difference_unknown_layout.stdout.elisa ]
rg -q 'pointer subtraction element layout' build/pointer_difference_unknown_layout.diagnostics

if ./build/elisa-c-transpiler testdata/fixtures/pointer_difference_packed_layout.c \
    > build/pointer_difference_packed_layout.stdout.elisa \
    2> build/pointer_difference_packed_layout.diagnostics; then
    echo "expected packed-record pointer subtraction to fail closed" >&2
    exit 1
fi
[ ! -s build/pointer_difference_packed_layout.stdout.elisa ]
rg -q 'pointer subtraction element layout' build/pointer_difference_packed_layout.diagnostics

if ./build/elisa-c-transpiler testdata/fixtures/record_sizeof_unknown_union.c \
    > build/record_sizeof_unknown_union.stdout.elisa \
    2> build/record_sizeof_unknown_union.diagnostics; then
    echo "expected sizeof of a union without a verified layout to fail closed" >&2
    exit 1
fi
[ ! -s build/record_sizeof_unknown_union.stdout.elisa ]
rg -q 'record size layout' build/record_sizeof_unknown_union.diagnostics

if ./build/elisa-c-transpiler testdata/fixtures/record_alignof_packed.c \
    > build/record_alignof_packed.stdout.elisa \
    2> build/record_alignof_packed.diagnostics; then
    echo "expected alignof of a packed record to fail closed" >&2
    exit 1
fi
[ ! -s build/record_alignof_packed.stdout.elisa ]
rg -q 'record alignment layout' build/record_alignof_packed.diagnostics

if ./build/elisa-c-transpiler testdata/fixtures/flexible_array_member_probe.c \
    > build/flexible_array_member_probe.stdout.elisa \
    2> build/flexible_array_member_probe.diagnostics; then
    echo "expected flexible-array member translation to fail closed" >&2
    exit 1
fi
[ ! -s build/flexible_array_member_probe.stdout.elisa ]
rg -q 'flexible array member layout/lifetime' build/flexible_array_member_probe.diagnostics

if ./build/elisa-c-transpiler testdata/fixtures/zero_length_array_member_probe.c \
    > build/zero_length_array_member_probe.stdout.elisa \
    2> build/zero_length_array_member_probe.diagnostics; then
    echo "expected zero-length array member translation to fail closed" >&2
    exit 1
fi
[ ! -s build/zero_length_array_member_probe.stdout.elisa ]
rg -q 'zero-length array member layout/lifetime' build/zero_length_array_member_probe.diagnostics

if ./build/elisa-c-transpiler testdata/fixtures/zero_length_local_array_probe.c \
    > build/zero_length_local_array_probe.stdout.elisa \
    2> build/zero_length_local_array_probe.diagnostics; then
    echo "expected zero-length local array translation to fail closed" >&2
    exit 1
fi
[ ! -s build/zero_length_local_array_probe.stdout.elisa ]
rg -q 'zero-length array bound/lifetime' build/zero_length_local_array_probe.diagnostics

if ./build/elisa-c-transpiler testdata/fixtures/variable_length_array_probe.c \
    > build/variable_length_array_probe.stdout.elisa \
    2> build/variable_length_array_probe.diagnostics; then
    echo "expected variable-length array translation to fail closed" >&2
    exit 1
fi
[ ! -s build/variable_length_array_probe.stdout.elisa ]
rg -q 'variable-length array bound/lifetime' build/variable_length_array_probe.diagnostics

if ./build/elisa-c-transpiler testdata/fixtures/vla_sizeof_type_probe.c \
    > build/vla_sizeof_type_probe.stdout.elisa \
    2> build/vla_sizeof_type_probe.diagnostics; then
    echo "expected sizeof(VLA type-name) translation to fail closed" >&2
    exit 1
fi
[ ! -s build/vla_sizeof_type_probe.stdout.elisa ]
rg -q 'variable-length sizeof/alignment bound evaluation' build/vla_sizeof_type_probe.diagnostics

if ./build/elisa-c-transpiler testdata/fixtures/variable_length_array_parameter_probe.c \
    > build/variable_length_array_parameter_probe.stdout.elisa \
    2> build/variable_length_array_parameter_probe.diagnostics; then
    echo "expected pointer-to-VLA parameter translation to fail closed" >&2
    exit 1
fi
[ ! -s build/variable_length_array_parameter_probe.stdout.elisa ]
rg -q 'variable or zero-length array parameter bound/lifetime' build/variable_length_array_parameter_probe.diagnostics

./build/elisa-c-transpiler testdata/fixtures/static_same_name.c > build/static_same_name.generated.elisa
[ "$(rg -c '^global mutable __elisa_internal_.*_value__global_' build/static_same_name.generated.elisa)" -eq 2 ]
! rg -q '^global mutable value:' build/static_same_name.generated.elisa
clang -std=c11 testdata/fixtures/static_same_name.c -o build/static_same_name.native
"$elisa_bin" -emit obj -O0 -o build/static_same_name.generated.o build/static_same_name.generated.elisa
clang -Wl,-dead_strip -o build/static_same_name.generated build/static_same_name.generated.o
set +e
./build/static_same_name.native
static_same_name_native_rc=$?
./build/static_same_name.generated
static_same_name_generated_rc=$?
set -e
[ "$static_same_name_native_rc" -eq "$static_same_name_generated_rc" ]

# An anonymous typedef record declared by a same-directory implementation file
# included into the translation unit must keep its public typedef identity and
# full field layout through the Clang dependency projection.
./build/elisa-c-transpiler testdata/fixtures/anonymous_typedef_include.c > build/anonymous_typedef_include.generated.elisa
rg -q '^struct Parse_buffer:$' build/anonymous_typedef_include.generated.elisa
rg -q '^    content: u8&\?$' build/anonymous_typedef_include.generated.elisa
rg -q '^    length: u64$' build/anonymous_typedef_include.generated.elisa
rg -q '^    offset: u64$' build/anonymous_typedef_include.generated.elisa
rg -q '^    hooks: Internal_hooks$' build/anonymous_typedef_include.generated.elisa
rg -q '^struct Parse_error:$' build/anonymous_typedef_include.generated.elisa
rg -q '^    json: u8&\?$' build/anonymous_typedef_include.generated.elisa
rg -q '^    position: u64$' build/anonymous_typedef_include.generated.elisa
rg -q '^def anonymous_forward_caller\(' build/anonymous_typedef_include.generated.elisa
rg -q '^def anonymous_forward_target\(' build/anonymous_typedef_include.generated.elisa
! rg -q '^def anonymous_unused_dependency\(' build/anonymous_typedef_include.generated.elisa
clang -std=c11 testdata/fixtures/anonymous_typedef_include.c -o build/anonymous_typedef_include.native
"$elisa_bin" -emit obj -O0 -o build/anonymous_typedef_include.generated.o build/anonymous_typedef_include.generated.elisa
clang -Wl,-dead_strip -o build/anonymous_typedef_include.generated build/anonymous_typedef_include.generated.o
set +e
./build/anonymous_typedef_include.native
anonymous_typedef_include_native_rc=$?
./build/anonymous_typedef_include.generated
anonymous_typedef_include_generated_rc=$?
set -e
[ "$anonymous_typedef_include_native_rc" -eq 0 ] && [ "$anonymous_typedef_include_generated_rc" -eq 0 ]

./build/elisa-c-transpiler testdata/fixtures/compound_widths.c > build/compound_widths.generated.elisa
rg -q '\+= .*\.i32\(\)|\+= .*\.u8\(\)' build/compound_widths.generated.elisa
clang -std=c11 testdata/fixtures/compound_widths.c -o build/compound_widths.native
"$elisa_bin" -emit obj -O0 -o build/compound_widths.generated.o build/compound_widths.generated.elisa
clang -Wl,-dead_strip -o build/compound_widths.generated build/compound_widths.generated.o
set +e
./build/compound_widths.native
compound_widths_native_rc=$?
./build/compound_widths.generated
compound_widths_generated_rc=$?
set -e
[ "$compound_widths_native_rc" -eq 0 ] && [ "$compound_widths_generated_rc" -eq 0 ]

escaped_ast_path_dir='build/frontend-json-path-"quoted"-back\slash-café'
mkdir -p "$escaped_ast_path_dir"
cp testdata/fixtures/simple.c "$escaped_ast_path_dir/source.c"
./build/elisa-c-transpiler "$escaped_ast_path_dir/source.c" > build/escaped_ast_path.generated.elisa
rg -q '^def main\(\) -> i32([[:space:]]|:)' build/escaped_ast_path.generated.elisa
clang -std=c11 "$escaped_ast_path_dir/source.c" -o build/escaped_ast_path.native
"$elisa_bin" -emit obj -O0 -o build/escaped_ast_path.generated.o build/escaped_ast_path.generated.elisa
clang -Wl,-dead_strip -o build/escaped_ast_path.generated build/escaped_ast_path.generated.o
set +e
./build/escaped_ast_path.native
escaped_ast_path_native_rc=$?
./build/escaped_ast_path.generated
escaped_ast_path_generated_rc=$?
set -e
[ "$escaped_ast_path_native_rc" -eq "$escaped_ast_path_generated_rc" ]

./build/elisa-c-transpiler --dump-typed-ir testdata/fixtures/simple.c > build/simple.dump.stdout.elisa 2> build/simple.typed-ir.dump
cmp build/simple.idiomatic.elisa build/simple.dump.stdout.elisa
rg -q '^typed-ir-v13$' build/simple.typed-ir.dump
rg -q '^counts ' build/simple.typed-ir.dump
./build/elisa-c-transpiler --dump-typed-ir testdata/fixtures/simple.c > build/simple.dump.stdout.second.elisa 2> build/simple.typed-ir.dump.second
cmp build/simple.idiomatic.elisa build/simple.dump.stdout.second.elisa
cmp build/simple.typed-ir.dump build/simple.typed-ir.dump.second

./build/elisa-c-transpiler --dump-typed-ir testdata/fixtures/backward_goto.c > build/backward_goto.dump.stdout.elisa 2> build/backward_goto.typed-ir.dump
./build/elisa-c-transpiler --dump-typed-ir testdata/fixtures/backward_goto.c > build/backward_goto.dump.stdout.second.elisa 2> build/backward_goto.typed-ir.dump.second
cmp build/backward_goto.dump.stdout.elisa build/backward_goto.dump.stdout.second.elisa
cmp build/backward_goto.typed-ir.dump build/backward_goto.typed-ir.dump.second
rg -q ' kind=Goto ' build/backward_goto.typed-ir.dump
rg -q ' kind=Label ' build/backward_goto.typed-ir.dump

./build/elisa-c-transpiler testdata/fixtures/generic_nonnull.c > build/generic_nonnull.generated.elisa
rg -Fq 'def elisa_nonnull[T](value: mutable T&?) -> mutable T&:' build/generic_nonnull.generated.elisa
[ "$(rg -c '^def elisa_nonnull\[' build/generic_nonnull.generated.elisa)" -eq 1 ]
rg -Fq 'elisa_nonnull(byte)' build/generic_nonnull.generated.elisa
rg -Fq 'elisa_nonnull(number)' build/generic_nonnull.generated.elisa
rg -Fq 'elisa_nonnull(sample)' build/generic_nonnull.generated.elisa
rg -Fq 'elisa_nonnull(text)' build/generic_nonnull.generated.elisa
rg -Fq 'elisa_nonnull(elisa_nonnull(text)[0])[0]' build/generic_nonnull.generated.elisa
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

./build/elisa-c-transpiler testdata/fixtures/opaque_typedef.c > build/opaque_typedef.generated.elisa
rg -q '^extern create_context\(\) -> mutable Opaque_context&\?$' build/opaque_typedef.generated.elisa
rg -q '^extern use_context\(context: mutable Opaque_context&\?\) -> void$' build/opaque_typedef.generated.elisa
! rg -q '^extern create_context\(\) -> i32$' build/opaque_typedef.generated.elisa

./build/elisa-c-transpiler testdata/fixtures/pointer_depth.c > build/pointer_depth.generated.elisa
rg -q '^def store_pointer\(slot: mutable \(mutable void&\?\) &\?\) -> i32' build/pointer_depth.generated.elisa
clang -std=c11 testdata/fixtures/pointer_depth.c -o build/pointer_depth.native
"$elisa_bin" -emit obj -O0 -o build/pointer_depth.generated.o build/pointer_depth.generated.elisa
clang -Wl,-dead_strip -o build/pointer_depth.generated build/pointer_depth.generated.o
set +e
./build/pointer_depth.native
pointer_depth_native_rc=$?
./build/pointer_depth.generated
pointer_depth_generated_rc=$?
set -e
[ "$pointer_depth_native_rc" -eq 0 ] && [ "$pointer_depth_generated_rc" -eq 0 ]

./build/elisa-c-transpiler testdata/fixtures/pointer_qualifier_layers.c > build/pointer_qualifier_layers.generated.elisa
rg -q '^def read_only_chain\(slot: \(i32&\?\) &\?\) -> i32' build/pointer_qualifier_layers.generated.elisa
rg -q '^def replace_const_pointee_pointer\(slot: mutable \(i32&\?\) &\?\)' build/pointer_qualifier_layers.generated.elisa
rg -Fq 'writable_slot: mutable (mutable i32&?) &?' build/pointer_qualifier_layers.generated.elisa
rg -Fq 'volatile_slot: mutable (mutable i32&?) &?' build/pointer_qualifier_layers.generated.elisa
rg -Fq '(source_slot).cast[(mutable i32&?) &?]' build/pointer_qualifier_layers.generated.elisa
rg -Fq 'cast[mutable (mutable i32&?) &?]' build/pointer_qualifier_layers.generated.elisa
rg -Fq 'mutable readonly_pointee: i32&? = &first' build/pointer_qualifier_layers.generated.elisa
rg -Fq 'immutable_slot: mutable i32&? = &first' build/pointer_qualifier_layers.generated.elisa
! rg -q '\bconst\b' build/pointer_qualifier_layers.generated.elisa
clang -std=c11 testdata/fixtures/pointer_qualifier_layers.c -o build/pointer_qualifier_layers.native
"$elisa_bin" -emit obj -O0 -o build/pointer_qualifier_layers.generated.o build/pointer_qualifier_layers.generated.elisa
clang -Wl,-dead_strip -o build/pointer_qualifier_layers.generated build/pointer_qualifier_layers.generated.o
set +e
./build/pointer_qualifier_layers.native
pointer_qualifier_layers_native_rc=$?
./build/pointer_qualifier_layers.generated
pointer_qualifier_layers_generated_rc=$?
set -e
[ "$pointer_qualifier_layers_native_rc" -eq 0 ] && [ "$pointer_qualifier_layers_generated_rc" -eq 0 ]

./build/elisa-c-transpiler testdata/fixtures/nested_arrays.c > build/nested_arrays.generated.elisa
rg -q '^global mutable matrix: array\[array\[i32, 2\], 4\] = \[\[0, -1\], \[1, 0\], \[0, 1\], \[-1, 0\]\]$' build/nested_arrays.generated.elisa
! rg -q '^matrix <- ' build/nested_arrays.generated.elisa
clang -std=c11 testdata/fixtures/nested_arrays.c -o build/nested_arrays.native
"$elisa_bin" -emit obj -O0 -o build/nested_arrays.generated.o build/nested_arrays.generated.elisa
clang -Wl,-dead_strip -o build/nested_arrays.generated build/nested_arrays.generated.o "$stage1_runtime"
set +e
./build/nested_arrays.native
nested_arrays_native_rc=$?
./build/nested_arrays.generated
nested_arrays_generated_rc=$?
set -e
[ "$nested_arrays_native_rc" -eq 0 ] && [ "$nested_arrays_generated_rc" -eq 0 ]

./build/elisa-c-transpiler testdata/fixtures/local_array_initializer.c > build/local_array_initializer.generated.elisa
rg -q '^        value: array\[i8, 8\] = \[102, 111, 111, 0, 0, 0, 0, 0\]$' build/local_array_initializer.generated.elisa
clang -std=c11 testdata/fixtures/local_array_initializer.c -o build/local_array_initializer.native
"$elisa_bin" -emit obj -O0 -o build/local_array_initializer.generated.o build/local_array_initializer.generated.elisa
clang -Wl,-dead_strip -o build/local_array_initializer.generated build/local_array_initializer.generated.o
set +e
./build/local_array_initializer.native
local_array_initializer_native_rc=$?
./build/local_array_initializer.generated
local_array_initializer_generated_rc=$?
set -e
[ "$local_array_initializer_native_rc" -eq 0 ] && [ "$local_array_initializer_generated_rc" -eq 0 ]

./build/elisa-c-transpiler testdata/fixtures/local_array_aggregate.c > build/local_array_aggregate.generated.elisa
rg -q '^        record: array\[i32, 6\] = \[7, 11, 13, 17, 19, 23\]$' build/local_array_aggregate.generated.elisa
clang -std=c11 testdata/fixtures/local_array_aggregate.c -o build/local_array_aggregate.native
"$elisa_bin" -emit obj -O0 -o build/local_array_aggregate.generated.o build/local_array_aggregate.generated.elisa
clang -Wl,-dead_strip -o build/local_array_aggregate.generated build/local_array_aggregate.generated.o
set +e
./build/local_array_aggregate.native
local_array_aggregate_native_rc=$?
./build/local_array_aggregate.generated
local_array_aggregate_generated_rc=$?
set -e
[ "$local_array_aggregate_native_rc" -eq 0 ] && [ "$local_array_aggregate_generated_rc" -eq 0 ]

./build/elisa-c-transpiler testdata/fixtures/sizeof_typedef_array.c > build/sizeof_typedef_array.generated.elisa
rg -q 'return \(0 if size_of\[u8\] \* 450 == 450 else 1\)' build/sizeof_typedef_array.generated.elisa
clang -std=c11 testdata/fixtures/sizeof_typedef_array.c -o build/sizeof_typedef_array.native
"$elisa_bin" -emit obj -O0 -o build/sizeof_typedef_array.generated.o build/sizeof_typedef_array.generated.elisa
clang -Wl,-dead_strip -o build/sizeof_typedef_array.generated build/sizeof_typedef_array.generated.o
set +e
./build/sizeof_typedef_array.native
sizeof_typedef_array_native_rc=$?
./build/sizeof_typedef_array.generated
sizeof_typedef_array_generated_rc=$?
set -e
[ "$sizeof_typedef_array_native_rc" -eq 0 ] && [ "$sizeof_typedef_array_generated_rc" -eq 0 ]

./build/elisa-c-transpiler testdata/fixtures/integer_conversions.c > build/integer_conversions.generated.elisa
rg -q '^    return \(\(left\)\.i32\(\) \+ \(right\)\.i32\(\)\)$' build/integer_conversions.generated.elisa
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

./build/elisa-c-transpiler testdata/fixtures/compiler_builtins.c > build/compiler_builtins.generated.elisa
rg -q '@link_name\("sinf"\)' build/compiler_builtins.generated.elisa
rg -q '@link_name\("powf"\)' build/compiler_builtins.generated.elisa
! rg -q '@link_name\("__builtin_' build/compiler_builtins.generated.elisa
! rg -q '@link_name\("object_size"\)|extern __builtin_object_size\(' build/compiler_builtins.generated.elisa
rg -q 'size_of\[i8\] \* 50' build/compiler_builtins.generated.elisa
rg -q '18446744073709551615' build/compiler_builtins.generated.elisa
! rg -q '__builtin_expect' build/compiler_builtins.generated.elisa
clang -std=c11 testdata/fixtures/compiler_builtins.c -o build/compiler_builtins.native
if "$elisa_bin" -emit obj -O0 -o build/compiler_builtins.generated.o build/compiler_builtins.generated.elisa \
    >build/compiler_builtins.probe.out 2>build/compiler_builtins.probe.err; then
    clang -Wl,-dead_strip -o build/compiler_builtins.generated build/compiler_builtins.generated.o -lm
    set +e
    ./build/compiler_builtins.native
    compiler_builtins_native_rc=$?
    ./build/compiler_builtins.generated
    compiler_builtins_generated_rc=$?
    set -e
    [ "$compiler_builtins_native_rc" -eq 0 ] && [ "$compiler_builtins_generated_rc" -eq 0 ]
else
    if [ -n "${elisa_runtime:-}" ] && rg -q '^error: backend could not produce a linkable unit; declined ' build/compiler_builtins.probe.err; then
        echo "SKIP compiler_builtins executable parity: selected stage1 backend declines offset-of call expression" >&2
    else
        cat build/compiler_builtins.probe.out >&2
        cat build/compiler_builtins.probe.err >&2
        exit 1
    fi
fi

./build/elisa-c-transpiler testdata/fixtures/extern_c_scope.cpp > build/extern_c_scope.generated.elisa
rg -q '^def linkage_helper\(value: i32\) -> i32' build/extern_c_scope.generated.elisa
rg -q '^def main\(\) -> i32' build/extern_c_scope.generated.elisa
clang++ -std=gnu++11 testdata/fixtures/extern_c_scope.cpp -o build/extern_c_scope.native
"$elisa_bin" -emit obj -O0 -o build/extern_c_scope.generated.o build/extern_c_scope.generated.elisa
clang -Wl,-dead_strip -o build/extern_c_scope.generated build/extern_c_scope.generated.o
./build/extern_c_scope.native
./build/extern_c_scope.generated

./build/elisa-c-transpiler testdata/fixtures/header_inline.cpp > build/header_inline.generated.elisa
rg -q '^def triple_value\(value: i32\) -> i32' build/header_inline.generated.elisa
rg -q '^def add_one_value\(value: i32\) -> i32' build/header_inline.generated.elisa
! rg -q '^extern (triple_value|add_one_value)\(' build/header_inline.generated.elisa
clang++ -std=gnu++11 testdata/fixtures/header_inline.cpp -o build/header_inline.native
"$elisa_bin" -emit obj -O0 -o build/header_inline.generated.o build/header_inline.generated.elisa
clang -Wl,-dead_strip -o build/header_inline.generated build/header_inline.generated.o
./build/header_inline.native
./build/header_inline.generated

./build/elisa-c-transpiler testdata/fixtures/pointer_array_decay.cpp > build/pointer_array_decay.generated.elisa
! rg -q '&&array' build/pointer_array_decay.generated.elisa
rg -Fq 'def take_rows(rows: mutable array[mutable Objstruct&?, 4]&?)' build/pointer_array_decay.generated.elisa
clang++ -std=gnu++11 testdata/fixtures/pointer_array_decay.cpp -o build/pointer_array_decay.native
"$elisa_bin" -emit obj -O0 -o build/pointer_array_decay.generated.o build/pointer_array_decay.generated.elisa
clang -Wl,-dead_strip -o build/pointer_array_decay.generated build/pointer_array_decay.generated.o
./build/pointer_array_decay.native
./build/pointer_array_decay.generated

./build/elisa-c-transpiler testdata/fixtures/array_of_pointers.c > build/array_of_pointers.generated.elisa
rg -q 'elisa_nonnull\(planes\[1\]\)\[2\]' build/array_of_pointers.generated.elisa
rg -q 'elisa_nonnull\(planes\[0\]\)\[3\]' build/array_of_pointers.generated.elisa
clang -std=c11 testdata/fixtures/array_of_pointers.c -o build/array_of_pointers.native
"$elisa_bin" -emit obj -O0 -o build/array_of_pointers.generated.o build/array_of_pointers.generated.elisa
clang -Wl,-dead_strip -o build/array_of_pointers.generated build/array_of_pointers.generated.o
set +e
./build/array_of_pointers.native
array_of_pointers_native_rc=$?
./build/array_of_pointers.generated
array_of_pointers_generated_rc=$?
set -e
[ "$array_of_pointers_native_rc" -eq 0 ] && [ "$array_of_pointers_generated_rc" -eq 0 ]

./build/elisa-c-transpiler testdata/fixtures/inline_macro.cpp > build/inline_macro.generated.elisa
rg -q '^def increment\(value: i32\) -> i32' build/inline_macro.generated.elisa
! rg -q '^extern increment\(' build/inline_macro.generated.elisa
clang++ -std=gnu++11 testdata/fixtures/inline_macro.cpp -o build/inline_macro.native
"$elisa_bin" -emit obj -O0 -o build/inline_macro.generated.o build/inline_macro.generated.elisa
clang -Wl,-dead_strip -o build/inline_macro.generated build/inline_macro.generated.o
./build/inline_macro.native
./build/inline_macro.generated

./build/elisa-c-transpiler testdata/fixtures/cpp_reference_cursor.cpp > build/cpp_reference_cursor.generated.elisa
rg -Fq 'def readword(ptr: mutable mutable u8&?&) -> u16' build/cpp_reference_cursor.generated.elisa
rg -Fq 'ptr: mutable u8&? = (&(bytes)[0]).cast[mutable u8&?]' build/cpp_reference_cursor.generated.elisa
rg -q 'ptr\[0\] <- \(&elisa_nonnull\(ptr\[0\]\)\[2\]\)' build/cpp_reference_cursor.generated.elisa
rg -Fq 'readword((&(ptr)).cast[mutable mutable u8&?&])' build/cpp_reference_cursor.generated.elisa
clang++ -std=gnu++11 testdata/fixtures/cpp_reference_cursor.cpp -o build/cpp_reference_cursor.native
"$elisa_bin" -emit obj -O0 -o build/cpp_reference_cursor.generated.o build/cpp_reference_cursor.generated.elisa
clang -Wl,-dead_strip -o build/cpp_reference_cursor.generated build/cpp_reference_cursor.generated.o
set +e
./build/cpp_reference_cursor.native
cpp_reference_native_rc=$?
./build/cpp_reference_cursor.generated
cpp_reference_generated_rc=$?
set -e
[ "$cpp_reference_native_rc" -eq 0 ] && [ "$cpp_reference_generated_rc" -eq 0 ]

./build/elisa-c-transpiler testdata/fixtures/cpp_unordered_map.cpp > build/cpp_unordered_map.generated.elisa
rg -q '^include "../cpp_lib/unordered_map.elisa"$' build/cpp_unordered_map.generated.elisa
rg -q '^global mutable values: cpp::unordered_map\[i32, i32\] = zeroed$' build/cpp_unordered_map.generated.elisa
rg -q 'values\[7\]\.value <- 42' build/cpp_unordered_map.generated.elisa
rg -q 'values\.count\(7\)' build/cpp_unordered_map.generated.elisa
rg -q 'values\.empty\(\)' build/cpp_unordered_map.generated.elisa
rg -q 'values\.erase\(7\)' build/cpp_unordered_map.generated.elisa
clang++ -std=gnu++11 testdata/fixtures/cpp_unordered_map.cpp -o build/cpp_unordered_map.native
if [ -x "$stage1_bin" ] && [ -f "$stage1_runtime" ]; then
    (
        cd "$stage1_worktree"
        ELISA_STAGE1_BIN="$stage1_bin" ELISA_RUNTIME_OBJ="$stage1_runtime" \
            bash scripts/elisac_stage1.sh -emit exe -O0 -o /tmp/elisa-transpiler-cpp-unordered-map "$root_dir/build/cpp_unordered_map.generated.elisa"
    )
    set +e
    ./build/cpp_unordered_map.native
    cpp_map_native_rc=$?
    /tmp/elisa-transpiler-cpp-unordered-map
    cpp_map_generated_rc=$?
    set -e
[ "$cpp_map_native_rc" -eq 45 ] && [ "$cpp_map_generated_rc" -eq 45 ]
else
    echo "skipping stage1 C++ adapter check; local stage1 compiler/runtime is not built" >&2
fi

clang++ -std=gnu++11 testdata/fixtures/cpp_template_direct.cpp -o build/cpp_template_direct.native
./build/elisa-c-transpiler testdata/fixtures/cpp_template_direct.cpp > build/cpp_template_direct.generated.elisa
rg -q '^struct ElisaTemplate_[0-9]+:$' build/cpp_template_direct.generated.elisa
rg -q 'cell: mutable ElisaTemplate_[0-9]+ = zeroed' build/cpp_template_direct.generated.elisa
rg -q 'floating_cell: mutable ElisaTemplate_[0-9]+ = zeroed' build/cpp_template_direct.generated.elisa
rg -q 'alpha_cell: mutable ElisaTemplate_[0-9]+ = zeroed' build/cpp_template_direct.generated.elisa
rg -q 'beta_cell: mutable ElisaTemplate_[0-9]+ = zeroed' build/cpp_template_direct.generated.elisa
rg -q 'small_buffer: mutable ElisaTemplate_[0-9]+ = zeroed' build/cpp_template_direct.generated.elisa
rg -q 'large_buffer: mutable ElisaTemplate_[0-9]+ = zeroed' build/cpp_template_direct.generated.elisa
rg -q 'enabled_flag: mutable ElisaTemplate_[0-9]+ = zeroed' build/cpp_template_direct.generated.elisa
rg -q 'disabled_flag: mutable ElisaTemplate_[0-9]+ = zeroed' build/cpp_template_direct.generated.elisa
rg -q 'negative_tag: mutable ElisaTemplate_[0-9]+ = zeroed' build/cpp_template_direct.generated.elisa
rg -q 'default_buffer: mutable ElisaTemplate_[0-9]+ = zeroed' build/cpp_template_direct.generated.elisa
rg -q 'explicit_default_buffer: mutable ElisaTemplate_[0-9]+ = zeroed' build/cpp_template_direct.generated.elisa
rg -q 'differently_sized_buffer: mutable ElisaTemplate_[0-9]+ = zeroed' build/cpp_template_direct.generated.elisa
rg -q 'default_type: mutable ElisaTemplate_[0-9]+ = zeroed' build/cpp_template_direct.generated.elisa
rg -q 'explicit_default_type: mutable ElisaTemplate_[0-9]+ = zeroed' build/cpp_template_direct.generated.elisa
rg -q 'alternate_default_type: mutable ElisaTemplate_[0-9]+ = zeroed' build/cpp_template_direct.generated.elisa
rg -q 'value: mutable i32' build/cpp_template_direct.generated.elisa
rg -q 'value: mutable f64' build/cpp_template_direct.generated.elisa
rg -q 'values: array\[i32, 2\]' build/cpp_template_direct.generated.elisa
rg -q 'values: array\[i32, 3\]' build/cpp_template_direct.generated.elisa
rg -q 'values: array\[i32, 4\]' build/cpp_template_direct.generated.elisa
rg -q 'values: array\[i32, 5\]' build/cpp_template_direct.generated.elisa
! rg -q '^struct ExternalCell:$' build/cpp_template_direct.generated.elisa
! rg -q '^struct Cell:$' build/cpp_template_direct.generated.elisa
! rg -q '^struct FixedBuffer:$|^struct FeatureFlag:$|^struct IntegralTag:$|^struct DefaultBuffer:$|^struct DefaultType:$' build/cpp_template_direct.generated.elisa
specialization_count=$(rg -c '^struct ElisaTemplate_[0-9]+:$' build/cpp_template_direct.generated.elisa)
[ "$specialization_count" -eq 13 ]
alpha_type=$(sed -n 's/^        alpha_cell: mutable \(ElisaTemplate_[0-9]*\) = zeroed$/\1/p' build/cpp_template_direct.generated.elisa)
beta_type=$(sed -n 's/^        beta_cell: mutable \(ElisaTemplate_[0-9]*\) = zeroed$/\1/p' build/cpp_template_direct.generated.elisa)
[ -n "$alpha_type" ] && [ -n "$beta_type" ] && [ "$alpha_type" != "$beta_type" ]
small_buffer_type=$(sed -n 's/^        small_buffer: mutable \(ElisaTemplate_[0-9]*\) = zeroed$/\1/p' build/cpp_template_direct.generated.elisa)
large_buffer_type=$(sed -n 's/^        large_buffer: mutable \(ElisaTemplate_[0-9]*\) = zeroed$/\1/p' build/cpp_template_direct.generated.elisa)
[ -n "$small_buffer_type" ] && [ -n "$large_buffer_type" ] && [ "$small_buffer_type" != "$large_buffer_type" ]
enabled_flag_type=$(sed -n 's/^        enabled_flag: mutable \(ElisaTemplate_[0-9]*\) = zeroed$/\1/p' build/cpp_template_direct.generated.elisa)
disabled_flag_type=$(sed -n 's/^        disabled_flag: mutable \(ElisaTemplate_[0-9]*\) = zeroed$/\1/p' build/cpp_template_direct.generated.elisa)
[ -n "$enabled_flag_type" ] && [ -n "$disabled_flag_type" ] && [ "$enabled_flag_type" != "$disabled_flag_type" ]
default_buffer_type=$(sed -n 's/^        default_buffer: mutable \(ElisaTemplate_[0-9]*\) = zeroed$/\1/p' build/cpp_template_direct.generated.elisa)
explicit_default_buffer_type=$(sed -n 's/^        explicit_default_buffer: mutable \(ElisaTemplate_[0-9]*\) = zeroed$/\1/p' build/cpp_template_direct.generated.elisa)
[ -n "$default_buffer_type" ] && [ "$default_buffer_type" = "$explicit_default_buffer_type" ]
differently_sized_buffer_type=$(sed -n 's/^        differently_sized_buffer: mutable \(ElisaTemplate_[0-9]*\) = zeroed$/\1/p' build/cpp_template_direct.generated.elisa)
[ -n "$differently_sized_buffer_type" ] && [ "$default_buffer_type" != "$differently_sized_buffer_type" ]
default_type=$(sed -n 's/^        default_type: mutable \(ElisaTemplate_[0-9]*\) = zeroed$/\1/p' build/cpp_template_direct.generated.elisa)
explicit_default_type=$(sed -n 's/^        explicit_default_type: mutable \(ElisaTemplate_[0-9]*\) = zeroed$/\1/p' build/cpp_template_direct.generated.elisa)
[ -n "$default_type" ] && [ "$default_type" = "$explicit_default_type" ]
alternate_default_type=$(sed -n 's/^        alternate_default_type: mutable \(ElisaTemplate_[0-9]*\) = zeroed$/\1/p' build/cpp_template_direct.generated.elisa)
[ -n "$alternate_default_type" ] && [ "$default_type" != "$alternate_default_type" ]
"$elisa_bin" -emit obj -O0 -o build/cpp_template_direct.generated.o build/cpp_template_direct.generated.elisa
clang -Wl,-dead_strip -o build/cpp_template_direct.generated build/cpp_template_direct.generated.o
./build/cpp_template_direct.native
./build/cpp_template_direct.generated

if ./build/elisa-c-transpiler testdata/fixtures/cpp_template_default_expression_unsupported.cpp > build/cpp_template_default_expression_unsupported.stdout.elisa 2> build/cpp_template_default_expression_unsupported.diagnostics; then
    echo "expected a compound non-type template default without a projected constant value to fail closed" >&2
    exit 1
fi
[ ! -s build/cpp_template_default_expression_unsupported.stdout.elisa ]
rg -q 'unsupported C\+\+ class-template value type outside supported adapters' build/cpp_template_default_expression_unsupported.diagnostics

if ./build/elisa-c-transpiler testdata/fixtures/cpp_unordered_map_unsupported.cpp > build/cpp_unordered_map_unsupported.stdout.elisa 2> build/cpp_unordered_map_unsupported.diagnostics; then
    echo "expected unsupported unordered_map policies/value initialization to fail closed" >&2
    exit 1
fi
[ ! -s build/cpp_unordered_map_unsupported.stdout.elisa ]
rg -q 'unsupported C\+\+ unordered_map custom template policies' build/cpp_unordered_map_unsupported.diagnostics
unordered_map_policy_diagnostic_count=$(rg -c 'unsupported C\+\+ unordered_map custom template policies' build/cpp_unordered_map_unsupported.diagnostics || true)
[ "$unordered_map_policy_diagnostic_count" -ge 3 ]
rg -q 'unsupported C\+\+ unordered_map mapped-value initialization' build/cpp_unordered_map_unsupported.diagnostics
rg -q 'unsupported C\+\+ unordered_map key hashing' build/cpp_unordered_map_unsupported.diagnostics

./build/elisa-c-transpiler --max-frontend-output-bytes 268435456 testdata/fixtures/cpp_unordered_map_find.cpp > build/cpp_unordered_map_find.generated.elisa
rg -q '^[[:space:]]*found: mutable cpp::unordered_map_iterator\[i32, i32\] =' build/cpp_unordered_map_find.generated.elisa
rg -q '^[[:space:]]*missing: mutable cpp::unordered_map_iterator\[i32, i32\] =' build/cpp_unordered_map_find.generated.elisa
rg -q 'found == values.end\(\)' build/cpp_unordered_map_find.generated.elisa
rg -q 'found.first\(\)' build/cpp_unordered_map_find.generated.elisa
rg -q 'found.second\(\)' build/cpp_unordered_map_find.generated.elisa
rg -q 'found.set_second\(43\)' build/cpp_unordered_map_find.generated.elisa
clang++ -std=gnu++17 testdata/fixtures/cpp_unordered_map_find.cpp -o build/cpp_unordered_map_find.native
if [ -x "$stage1_bin" ] && [ -f "$stage1_runtime" ]; then
    (
        cd "$stage1_worktree"
        ELISA_STAGE1_BIN="$stage1_bin" ELISA_RUNTIME_OBJ="$stage1_runtime" \
            bash scripts/elisac_stage1.sh -emit exe -O0 -o /tmp/elisa-transpiler-cpp-unordered-map-find "$root_dir/build/cpp_unordered_map_find.generated.elisa"
    )
    set +e
    ./build/cpp_unordered_map_find.native
    cpp_map_find_native_rc=$?
    /tmp/elisa-transpiler-cpp-unordered-map-find
    cpp_map_find_generated_rc=$?
    set -e
    [ "$cpp_map_find_native_rc" -eq 0 ] && [ "$cpp_map_find_generated_rc" -eq 0 ]
else
    echo "skipping stage1 C++ unordered_map iterator check; local stage1 compiler/runtime is not built" >&2
fi

if ./build/elisa-c-transpiler --max-frontend-output-bytes 268435456 \
    testdata/fixtures/cpp_unordered_map_reference_escape.cpp \
    > build/cpp_unordered_map_reference_escape.stdout.elisa \
    2> build/cpp_unordered_map_reference_escape.diagnostics; then
    echo "expected unordered_map iterator reference escapes to fail closed" >&2
    exit 1
fi
[ ! -s build/cpp_unordered_map_reference_escape.stdout.elisa ]
rg -q 'unsupported unordered_map iterator element address-taking' build/cpp_unordered_map_reference_escape.diagnostics
rg -q 'unsupported unordered_map iterator element reference binding' build/cpp_unordered_map_reference_escape.diagnostics

./build/elisa-c-transpiler testdata/fixtures/cpp_unordered_map_pointer_values.cpp > build/cpp_unordered_map_pointer_values.generated.elisa
rg -q '^global mutable names: cpp::unordered_map\[i32, u8&\?\] = zeroed$' build/cpp_unordered_map_pointer_values.generated.elisa
rg -q 'names\[7\]\.value' build/cpp_unordered_map_pointer_values.generated.elisa
rg -q 'if names\[8\]\.value != null:' build/cpp_unordered_map_pointer_values.generated.elisa
clang++ -std=gnu++11 testdata/fixtures/cpp_unordered_map_pointer_values.cpp -o build/cpp_unordered_map_pointer_values.native
if [ -x "$stage1_bin" ] && [ -f "$stage1_runtime" ]; then
    (
        cd "$stage1_worktree"
        ELISA_STAGE1_BIN="$stage1_bin" ELISA_RUNTIME_OBJ="$stage1_runtime" \
            bash scripts/elisac_stage1.sh -emit exe -O0 -o /tmp/elisa-transpiler-cpp-unordered-map-pointer-values "$root_dir/build/cpp_unordered_map_pointer_values.generated.elisa"
    )
    set +e
    ./build/cpp_unordered_map_pointer_values.native
    cpp_map_pointer_native_rc=$?
    /tmp/elisa-transpiler-cpp-unordered-map-pointer-values
    cpp_map_pointer_generated_rc=$?
    set -e
    [ "$cpp_map_pointer_native_rc" -eq 0 ] && [ "$cpp_map_pointer_generated_rc" -eq 0 ]
else
    echo "skipping stage1 C++ pointer-mapped adapter check; local stage1 compiler/runtime is not built" >&2
fi

./build/elisa-c-transpiler testdata/fixtures/unqualified_unordered_map.cpp > build/unqualified_unordered_map.generated.elisa
[ -s build/unqualified_unordered_map.generated.elisa ]
! rg -Fq 'include "../cpp_lib/unordered_map.elisa"' build/unqualified_unordered_map.generated.elisa
rg -q '^struct ElisaTemplate_[0-9]+:' build/unqualified_unordered_map.generated.elisa
rg -q '^global mutable values: ElisaTemplate_[0-9]+ = zeroed$' build/unqualified_unordered_map.generated.elisa
clang++ -std=gnu++11 testdata/fixtures/unqualified_unordered_map.cpp -o build/unqualified_unordered_map.native
"$elisa_bin" -emit obj -O0 -o build/unqualified_unordered_map.generated.o build/unqualified_unordered_map.generated.elisa
clang -Wl,-dead_strip -o build/unqualified_unordered_map.generated build/unqualified_unordered_map.generated.o
set +e
./build/unqualified_unordered_map.native
unqualified_map_native_rc=$?
./build/unqualified_unordered_map.generated
unqualified_map_generated_rc=$?
set -e
[ "$unqualified_map_native_rc" -eq "$unqualified_map_generated_rc" ]

./build/elisa-c-transpiler testdata/fixtures/constant_fold.c > build/constant_fold.generated.elisa
rg -q '^def folded_value\(\) -> i32:' build/constant_fold.generated.elisa
rg -q 'return 20' build/constant_fold.generated.elisa
rg -q 'return 1' build/constant_fold.generated.elisa
clang -std=c11 testdata/fixtures/constant_fold.c -o build/constant_fold.native
"$elisa_bin" -emit obj -O0 -o build/constant_fold.generated.o build/constant_fold.generated.elisa
clang -Wl,-dead_strip -o build/constant_fold.generated build/constant_fold.generated.o
./build/constant_fold.native
./build/constant_fold.generated

./build/elisa-c-transpiler --fidelity testdata/fixtures/constant_fold.c > build/constant_fold.fidelity.elisa
rg -q '^    return \(\(2 \+ 3\) \* 4\)$' build/constant_fold.fidelity.elisa
! rg -q '^    return 20$' build/constant_fold.fidelity.elisa
"$elisa_bin" -emit obj -O0 -o build/constant_fold.fidelity.o build/constant_fold.fidelity.elisa
clang -Wl,-dead_strip -o build/constant_fold.fidelity build/constant_fold.fidelity.o
./build/constant_fold.fidelity

./build/elisa-c-transpiler testdata/fixtures/wide_switch_constant.c > build/wide_switch_constant.generated.elisa
rg -q 'match value:' build/wide_switch_constant.generated.elisa
clang -std=c11 testdata/fixtures/wide_switch_constant.c -o build/wide_switch_constant.native
"$elisa_bin" -emit obj -O0 -o build/wide_switch_constant.generated.o build/wide_switch_constant.generated.elisa
clang -Wl,-dead_strip -o build/wide_switch_constant.generated build/wide_switch_constant.generated.o
./build/wide_switch_constant.native
./build/wide_switch_constant.generated

./build/elisa-c-transpiler testdata/fixtures/idiomatic_patterns.c > build/idiomatic_patterns.generated.elisa
rg -q 'result: i32 = value' build/idiomatic_patterns.generated.elisa
! rg -q 'if true:' build/idiomatic_patterns.generated.elisa
rg -q '^    return result$' build/idiomatic_patterns.generated.elisa
# Pointer reads emitted inside the generated trusted block must keep an
# explicit null-to-reference check: Elisa does not preserve the C branch-local
# non-null proof across that trust boundary. After an intervening call, the
# mutable pointer's fact is conservatively invalidated as well.
rg -q '^def elisa_nonnull_readonly\[T\]' build/idiomatic_patterns.generated.elisa
rg -q 'return elisa_nonnull_readonly\(value\)\[0\]' build/idiomatic_patterns.generated.elisa
rg -q 'return elisa_nonnull\(value\)\[0\]' build/idiomatic_patterns.generated.elisa
! rg -q '^\s*return value\[0\]$' build/idiomatic_patterns.generated.elisa
rg -A3 'inspect_readonly\(value\)' build/idiomatic_patterns.generated.elisa | rg -q 'return elisa_nonnull\(value\)\[0\]'
clang -std=c11 testdata/fixtures/idiomatic_patterns.c -o build/idiomatic_patterns.native
"$elisa_bin" -emit obj -O0 -o build/idiomatic_patterns.generated.o build/idiomatic_patterns.generated.elisa
clang -Wl,-dead_strip -o build/idiomatic_patterns.generated build/idiomatic_patterns.generated.o
./build/idiomatic_patterns.native
./build/idiomatic_patterns.generated

./build/elisa-c-transpiler testdata/fixtures/const_cast.c > build/const_cast.generated.elisa
rg -q 'return elisa_nonnull\(\(value\)\.cast\[mutable i32&\?\]\)\[0\]' build/const_cast.generated.elisa
clang -std=c11 testdata/fixtures/const_cast.c -o build/const_cast.native
"$elisa_bin" -emit obj -O0 -o build/const_cast.generated.o build/const_cast.generated.elisa
clang -Wl,-dead_strip -o build/const_cast.generated build/const_cast.generated.o
./build/const_cast.native
./build/const_cast.generated

./build/elisa-c-transpiler testdata/fixtures/const_bindings.c > build/const_bindings.generated.elisa
rg -q '^def read_const_bindings\(scalar: i32, fixed: mutable i32&\?, readonly: i32&\?\)' build/const_bindings.generated.elisa
! rg -q '^    mutable scalar:' build/const_bindings.generated.elisa
rg -q '^[[:space:]]+scalar: i32 = 3$' build/const_bindings.generated.elisa
! rg -q '^    mutable fixed:' build/const_bindings.generated.elisa
rg -q '^[[:space:]]+fixed: mutable i32&\? = ' build/const_bindings.generated.elisa
! rg -q '^    mutable readonly:' build/const_bindings.generated.elisa
rg -q '^[[:space:]]+readonly: i32&\? = ' build/const_bindings.generated.elisa
! rg -q '\bconst\b' build/const_bindings.generated.elisa
clang -std=c11 testdata/fixtures/const_bindings.c -o build/const_bindings.native
"$elisa_bin" -emit obj -O0 -o build/const_bindings.generated.o build/const_bindings.generated.elisa
clang -Wl,-dead_strip -o build/const_bindings.generated build/const_bindings.generated.o
./build/const_bindings.native
./build/const_bindings.generated

./build/elisa-c-transpiler testdata/fixtures/static_local.c > build/static_local.generated.elisa
rg -q '^global mutable value: i32 = 4$' build/static_local.generated.elisa
! rg -q 'static' build/static_local.generated.elisa
clang -std=c11 testdata/fixtures/static_local.c -o build/static_local.native
"$elisa_bin" -emit obj -O0 -o build/static_local.generated.o build/static_local.generated.elisa
clang -Wl,-dead_strip -o build/static_local.generated build/static_local.generated.o
./build/static_local.native
./build/static_local.generated

# Dynamic global initialization is emitted as a guarded initializer. Calling
# that generated entry point twice must not repeat the source initialization;
# the guard name is derived from the translation-unit identity and is not a
# source-library special case.
./build/elisa-c-transpiler testdata/fixtures/dynamic_global_init.cpp \
    > build/dynamic_global_init.generated.elisa
rg -q '^global mutable __elisa_transpiler_init_guard_[0-9]+: bool = false$' \
    build/dynamic_global_init.generated.elisa
rg -q '^def initialize_globals\(\)' build/dynamic_global_init.generated.elisa
ELISA_STAGE1_MAX_RSS_KB=4194304 bash "$stage1_worktree/scripts/elisac_stage1.sh" \
    -emit exe -O0 -o build/initializer-idempotence \
    "$root_dir/testdata/backend_initializer_idempotence.elisa"
./build/initializer-idempotence

./build/elisa-c-transpiler testdata/fixtures/const_aggregates.c > build/const_aggregates.generated.elisa
rg -q '^global const_numbers: array\[i32, 3\] = \[1, 0, 3\]$' build/const_aggregates.generated.elisa
rg -q '^global const_configuration: Const_configuration = ' build/const_aggregates.generated.elisa
rg -q '^global mutable const_names: array\[i8&\?, 2\] = zeroed$' build/const_aggregates.generated.elisa
! rg -q '\bconst\b' build/const_aggregates.generated.elisa
clang -std=c11 testdata/fixtures/const_aggregates.c -o build/const_aggregates.native
"$elisa_bin" -emit obj -O0 -o build/const_aggregates.generated.o build/const_aggregates.generated.elisa
clang -Wl,-dead_strip -o build/const_aggregates.generated build/const_aggregates.generated.o "$stage1_runtime"
./build/const_aggregates.native
./build/const_aggregates.generated

./scripts/quality_report.sh testdata/upstream/cJSON/cjson_smoke.c build/cjson.quality.elisa > build/cjson.quality.txt
rg -q '^invalid_ir_markers: 0$' build/cjson.quality.txt
rg -q '^casts: [0-9]+$' build/cjson.quality.txt
rg -q '^nonnull_assertions: [0-9]+$' build/cjson.quality.txt
rg -q '^ir_exprs: [1-9][0-9]*$' build/cjson.quality.txt
rg -q '^ir_statements: [1-9][0-9]*$' build/cjson.quality.txt
rg -q '^rewrite_integer_folds: [0-9]+$' build/cjson.quality.txt
awk 'length($0) > 320 { found = 1 } END { exit found }' build/cjson.quality.elisa
! sed '/^[[:space:]]*#/d' build/cjson.quality.elisa | rg -q '\bconst\b'

./build/elisa-c-transpiler testdata/fixtures/for_loop.c > build/for_loop.generated.elisa
rg -q 'while index < 5:' build/for_loop.generated.elisa
rg -q '__elisa_transpiler_inc_[0-9]+_post_increment_i32\(&\(index\)\)' build/for_loop.generated.elisa
rg -q 'while true:' build/for_loop.generated.elisa
clang -std=c11 testdata/fixtures/for_loop.c -o build/for_loop.native
"$elisa_bin" -emit obj -O0 -o build/for_loop.generated.o build/for_loop.generated.elisa
clang -Wl,-dead_strip -o build/for_loop.generated build/for_loop.generated.o
./build/for_loop.native
./build/for_loop.generated

./build/elisa-c-transpiler testdata/fixtures/do_while_continue.c > build/do_while_continue.generated.elisa
rg -q 'control_state: mutable i32 = 0' build/do_while_continue.generated.elisa
clang -std=c11 testdata/fixtures/do_while_continue.c -o build/do_while_continue.native
"$elisa_bin" -emit obj -O0 -o build/do_while_continue.generated.o build/do_while_continue.generated.elisa
clang -Wl,-dead_strip -o build/do_while_continue.generated build/do_while_continue.generated.o
./build/do_while_continue.native
./build/do_while_continue.generated

./build/elisa-c-transpiler testdata/fixtures/designated_init.c > build/designated_init.generated.elisa
rg -q 'Pair\{first: 3, second: 7, third: zeroed\}' build/designated_init.generated.elisa
rg -q '^global mutable values: array\[i32, 5\] = \[zeroed, zeroed, 7, zeroed, 9\]$' build/designated_init.generated.elisa
clang -std=c11 testdata/fixtures/designated_init.c -o build/designated_init.native
"$elisa_bin" -emit obj -O0 -o build/designated_init.generated.o build/designated_init.generated.elisa
clang -Wl,-dead_strip -o build/designated_init.generated build/designated_init.generated.o
./build/designated_init.native
./build/designated_init.generated

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
rg -q 'MODE_READ = 1' build/enum_flags.generated.elisa
rg -q 'MODE_WRITE = 4' build/enum_flags.generated.elisa
rg -q 'MODE_BOTH = 5' build/enum_flags.generated.elisa
rg -q 'Mode\.MODE_BOTH' build/enum_flags.generated.elisa
clang -std=c11 testdata/fixtures/enum_flags.c -o build/enum_flags.native
"$elisa_bin" -emit obj -O0 -o build/enum_flags.generated.o build/enum_flags.generated.elisa
clang -Wl,-dead_strip -o build/enum_flags.generated build/enum_flags.generated.o
./build/enum_flags.native
./build/enum_flags.generated

./build/elisa-c-transpiler testdata/fixtures/enum_unsigned.c > build/enum_unsigned.generated.elisa
rg -q 'const enum WideMode of u32:' build/enum_unsigned.generated.elisa
rg -q '\(mode\)\.u32\(\)' build/enum_unsigned.generated.elisa
clang -std=c11 testdata/fixtures/enum_unsigned.c -o build/enum_unsigned.native
"$elisa_bin" -emit obj -O0 -o build/enum_unsigned.generated.o build/enum_unsigned.generated.elisa
clang -Wl,-dead_strip -o build/enum_unsigned.generated build/enum_unsigned.generated.o
set +e
./build/enum_unsigned.native
enum_unsigned_native_rc=$?
./build/enum_unsigned.generated
enum_unsigned_generated_rc=$?
set -e
[ "$enum_unsigned_native_rc" -eq 0 ] && [ "$enum_unsigned_generated_rc" -eq 0 ]

./build/elisa-c-transpiler testdata/fixtures/unsigned_shift_wrap.c > build/unsigned_shift_wrap.generated.elisa
rg -q '^    return 0$' build/unsigned_shift_wrap.generated.elisa
clang -std=c11 testdata/fixtures/unsigned_shift_wrap.c -o build/unsigned_shift_wrap.native
"$elisa_bin" -emit obj -O0 -o build/unsigned_shift_wrap.generated.o build/unsigned_shift_wrap.generated.elisa
clang -Wl,-dead_strip -o build/unsigned_shift_wrap.generated build/unsigned_shift_wrap.generated.o
set +e
./build/unsigned_shift_wrap.native
unsigned_shift_wrap_native_rc=$?
./build/unsigned_shift_wrap.generated
unsigned_shift_wrap_generated_rc=$?
set -e
[ "$unsigned_shift_wrap_native_rc" -eq 0 ] && [ "$unsigned_shift_wrap_generated_rc" -eq 0 ]

./build/elisa-c-transpiler testdata/fixtures/integer_constant_semantics.c > build/integer_constant_semantics.generated.elisa
rg -q 'return 4294967295' build/integer_constant_semantics.generated.elisa
rg -q 'and true' build/integer_constant_semantics.generated.elisa
rg -q '\(-1\)\.u64\(\)' build/integer_constant_semantics.generated.elisa
! rg -Fq '(-1).u32()' build/integer_constant_semantics.generated.elisa
rg -Uq '^def u64_to_i32_target_conversion\(\) -> i32:\n\s+return .*\.i32\(\)' build/integer_constant_semantics.generated.elisa
! rg -Uq '^def u64_to_i32_target_conversion\(\) -> i32:\n\s+return -1$' build/integer_constant_semantics.generated.elisa
rg -Uq '^def u64_to_i64_target_conversion\(\) -> i64:\n\s+return .*\.i64\(\)' build/integer_constant_semantics.generated.elisa
! rg -Uq '^def u64_to_i64_target_conversion\(\) -> i64:\n\s+return -1$' build/integer_constant_semantics.generated.elisa
rg -Uq '^def u64_to_i32_above_signed_max\(\) -> i32:\n\s+return .*\.i32\(\)' build/integer_constant_semantics.generated.elisa
rg -Uq '^def u64_to_i16_target_conversion\(\) -> i32:\n\s+return .*\.i16\(\)' build/integer_constant_semantics.generated.elisa
rg -Uq '^def u64_to_i32_representable_conversion\(\) -> i32:\n\s+return 2147483647$' build/integer_constant_semantics.generated.elisa
rg -Uq '^def i64_min_divide_by_negative_one\(\) -> i64:\n\s+return .*/.*$' build/integer_constant_semantics.generated.elisa
rg -Uq '^def i64_min_remainder_by_negative_one\(\) -> i64:\n\s+return .*%.*$' build/integer_constant_semantics.generated.elisa
rg -Uq '^def i32_min_divide_by_negative_one\(\) -> i32:\n\s+return .*/.*$' build/integer_constant_semantics.generated.elisa
rg -Uq '^def i32_min_remainder_by_negative_one\(\) -> i32:\n\s+return .*%.*$' build/integer_constant_semantics.generated.elisa
rg -Uq '^def i64_signed_overflow_add\(\) -> i64:\n\s+return .*\+.*$' build/integer_constant_semantics.generated.elisa
rg -Uq '^def i64_signed_overflow_subtract\(\) -> i64:\n\s+return .* - .*?$' build/integer_constant_semantics.generated.elisa
rg -Uq '^def i64_signed_overflow_multiply\(\) -> i64:\n\s+return .*\*.*$' build/integer_constant_semantics.generated.elisa
clang -std=c11 -Wno-integer-overflow testdata/fixtures/integer_constant_semantics.c -o build/integer_constant_semantics.native
"$elisa_bin" -emit obj -O0 -o build/integer_constant_semantics.generated.o build/integer_constant_semantics.generated.elisa
clang -Wl,-dead_strip -o build/integer_constant_semantics.generated build/integer_constant_semantics.generated.o
set +e
./build/integer_constant_semantics.native
integer_constant_native_rc=$?
./build/integer_constant_semantics.generated
integer_constant_generated_rc=$?
set -e
[ "$integer_constant_native_rc" -eq 0 ] && [ "$integer_constant_generated_rc" -eq 0 ]

./build/elisa-c-transpiler testdata/fixtures/short_circuit_constant.c > build/short_circuit_constant.generated.elisa
rg -q '^        return calls$' build/short_circuit_constant.generated.elisa
! sed -n '/^def main()/,$p' build/short_circuit_constant.generated.elisa | rg -q 'if |side_effect\('
clang -std=c11 testdata/fixtures/short_circuit_constant.c -o build/short_circuit_constant.native
"$elisa_bin" -emit obj -O0 -o build/short_circuit_constant.generated.o build/short_circuit_constant.generated.elisa
clang -Wl,-dead_strip -o build/short_circuit_constant.generated build/short_circuit_constant.generated.o
set +e
./build/short_circuit_constant.native
short_circuit_constant_native_rc=$?
./build/short_circuit_constant.generated
short_circuit_constant_generated_rc=$?
set -e
[ "$short_circuit_constant_native_rc" -eq 0 ] && [ "$short_circuit_constant_generated_rc" -eq 0 ]

./build/elisa-c-transpiler testdata/fixtures/invalid_shift_count.c > build/invalid_shift_count.generated.elisa
rg -q 'return \(1 << \(32\)\.u32\(\)\)' build/invalid_shift_count.generated.elisa
rg -q '>>' build/invalid_shift_count.generated.elisa

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

./build/elisa-c-transpiler testdata/fixtures/nullable_function_field.c > build/nullable_function_field.generated.elisa
rg -q 'allocate: mutable \(fn\((usize|u64)\) -> mutable void&\?\)\?' build/nullable_function_field.generated.elisa
rg -Fq 'hooks.allocate(8)' build/nullable_function_field.generated.elisa
! rg -q '^    allocate: (mutable )?void&\?$' build/nullable_function_field.generated.elisa
clang -std=c11 testdata/fixtures/nullable_function_field.c -o build/nullable_function_field.native
# The canonical runner probes nullable function-field support before suite
# selection so the upstream suite can use the same capability result.
if [ "$optional_fn_supported" -eq 1 ]; then
    clang -Wl,-dead_strip -o build/nullable_function_field.generated build/nullable_function_field.generated.o
    ./build/nullable_function_field.native
    ./build/nullable_function_field.generated
else
    echo "SKIP nullable-function executable parity: unsupported by selected Elisa compiler" >&2
fi

./build/elisa-c-transpiler testdata/fixtures/name_collision.c > build/name_collision.generated.elisa
rg -q '^global mutable initialize_globals: i32 = 7$' build/name_collision.generated.elisa
! rg -q '^def initialize_globals\(' build/name_collision.generated.elisa
! rg -q '^def elisa_initialize_globals\(' build/name_collision.generated.elisa
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

./build/elisa-c-transpiler testdata/fixtures/keyword_identifiers.c > build/keyword_identifiers.generated.elisa
rg -q '^def c_match\(c_module: i32\) -> i32' build/keyword_identifiers.generated.elisa
rg -q 'c_match\(4\)' build/keyword_identifiers.generated.elisa
! rg -q '^def match\(' build/keyword_identifiers.generated.elisa
clang -std=c11 testdata/fixtures/keyword_identifiers.c -o build/keyword_identifiers.native
"$elisa_bin" -emit obj -O0 -o build/keyword_identifiers.generated.o build/keyword_identifiers.generated.elisa
clang -Wl,-dead_strip -o build/keyword_identifiers.generated build/keyword_identifiers.generated.o
./build/keyword_identifiers.native
./build/keyword_identifiers.generated

./build/elisa-c-transpiler testdata/fixtures/nested_shadowing.c > build/nested_shadowing.generated.elisa
shadow_value_count=$(rg -c 'value(_shadow_[0-9]+)?: i32 = ' build/nested_shadowing.generated.elisa)
[ "$shadow_value_count" -eq 2 ]
clang -std=c11 testdata/fixtures/nested_shadowing.c -o build/nested_shadowing.native
"$elisa_bin" -emit obj -O0 -o build/nested_shadowing.generated.o build/nested_shadowing.generated.elisa
clang -Wl,-dead_strip -o build/nested_shadowing.generated build/nested_shadowing.generated.o
./build/nested_shadowing.native
./build/nested_shadowing.generated

./build/elisa-c-transpiler testdata/fixtures/for_scope_shadowing.c > build/for_scope_shadowing.generated.elisa
rg -q '^    index: i32 = 7$' build/for_scope_shadowing.generated.elisa
rg -q '^    index_shadow_[0-9]+: mutable i32 = 0$' build/for_scope_shadowing.generated.elisa
! rg -q '^    index <- 0$' build/for_scope_shadowing.generated.elisa
clang -std=c11 testdata/fixtures/for_scope_shadowing.c -o build/for_scope_shadowing.native
"$elisa_bin" -emit obj -O0 -o build/for_scope_shadowing.generated.o build/for_scope_shadowing.generated.elisa
clang -Wl,-dead_strip -o build/for_scope_shadowing.generated build/for_scope_shadowing.generated.o
./build/for_scope_shadowing.native
./build/for_scope_shadowing.generated

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
rg -q '^[[:space:]]+0[[:space:]]+\|[[:space:]]+1:' build/switch.generated.elisa
rg -q '^[[:space:]]+5:' build/switch.generated.elisa
rg -q 'switch_done_' build/switch.generated.elisa
if sed -n '/^def nested_switch/,/^def conditional_break/p' build/switch.generated.elisa | rg -q 'switch_done_'; then
    echo "direct switch breaks should not require switch_done" >&2
    exit 1
fi
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

./build/elisa-c-transpiler testdata/fixtures/switch_patterns.c > build/switch_patterns.generated.elisa
rg -q '^[[:space:]]+10\.\.=12:' build/switch_patterns.generated.elisa
rg -q 'Token\.TOKEN_ZERO[[:space:]]+\|[[:space:]]+Token\.TOKEN_ONE:' build/switch_patterns.generated.elisa
clang -std=c11 testdata/fixtures/switch_patterns.c -o build/switch_patterns.native
"$elisa_bin" -emit obj -O0 -o build/switch_patterns.generated.o build/switch_patterns.generated.elisa
clang -Wl,-dead_strip -o build/switch_patterns.generated build/switch_patterns.generated.o
./build/switch_patterns.native
./build/switch_patterns.generated

./build/elisa-c-transpiler testdata/fixtures/switch_selector_once.c > build/switch_selector_once.generated.elisa
selector_temp_count=$(rg -c '__elisa_transpiler_switch_selector_[0-9]+: i32 = select_value\(\)' build/switch_selector_once.generated.elisa)
[ "$selector_temp_count" -eq 1 ]
rg -q 'match __elisa_transpiler_switch_selector_[0-9]+:' build/switch_selector_once.generated.elisa
! rg -q 'match select_value\(\):' build/switch_selector_once.generated.elisa
clang -std=c11 testdata/fixtures/switch_selector_once.c -o build/switch_selector_once.native
"$elisa_bin" -emit obj -O0 -o build/switch_selector_once.generated.o build/switch_selector_once.generated.elisa
clang -Wl,-dead_strip -o build/switch_selector_once.generated build/switch_selector_once.generated.o
./build/switch_selector_once.native
./build/switch_selector_once.generated

# Function-like export macros put a spelling location in the macro header and
# the usable expansion offset in the source definition. Preserve the otherwise
# unreferenced public function as an Elisa definition, not an unresolved extern.
./build/elisa-c-transpiler testdata/fixtures/macro_exported_api.c > build/macro_exported_api.generated.elisa
rg -q '^def exported_api_value\(\) -> i32' build/macro_exported_api.generated.elisa
! rg -q '^extern exported_api_value\(' build/macro_exported_api.generated.elisa
clang -std=c11 testdata/fixtures/macro_exported_api.c testdata/fixtures/macro_exported_api_harness.c -o build/macro_exported_api.native
clang -std=c11 -c testdata/fixtures/macro_exported_api_harness.c -o build/macro_exported_api.harness.o
"$elisa_bin" -emit obj -O0 -o build/macro_exported_api.generated.o build/macro_exported_api.generated.elisa
clang -Wl,-dead_strip -o build/macro_exported_api.generated build/macro_exported_api.harness.o build/macro_exported_api.generated.o
./build/macro_exported_api.native
./build/macro_exported_api.generated
