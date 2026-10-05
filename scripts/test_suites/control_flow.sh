# Integrated loop, goto and switch-control-flow fixtures.
mkdir -p build/target-abi-test
test_translator_bounded --compile-commands testdata/fixtures/target_abi_compile_commands.json --output-dir build/target-abi-test
rg -q '^def target_long\(value: i32\) -> i32' build/target-abi-test/target_abi.elisa
rg -q '^def target_unsigned_long\(value: u32\) -> u32' build/target-abi-test/target_abi.elisa
rg -q '^def target_size\(value: u64\) -> u64' build/target-abi-test/target_abi.elisa
rg -q '^def target_char\(value: i8\) -> i8' build/target-abi-test/target_abi.elisa
rg -q '^global mutable target_long_global: i32' build/target-abi-test/target_abi.elisa
rg -q 'signed_member: mutable i32' build/target-abi-test/target_abi.elisa
rg -q 'unsigned_member: mutable u32' build/target-abi-test/target_abi.elisa

# A C DeclStmt can contain several VarDecls but does not introduce a lexical
# scope. Mutability analysis and emission must carry each binding into following
# statements, including a grouped declaration in a for-loop initializer.
test_translator_bounded testdata/fixtures/multi_declarator_mutability.c \
    > build/multi_declarator_mutability.generated.elisa
rg -q '^    value: mutable i32 = 1$' \
    build/multi_declarator_mutability.generated.elisa
rg -q '^    stable: i32 = 8$' \
    build/multi_declarator_mutability.generated.elisa
rg -q 'shadow(_[0-9]+)?: mutable i32 = 20' \
    build/multi_declarator_mutability.generated.elisa
rg -q '^    index: mutable i32 = 0$' \
    build/multi_declarator_mutability.generated.elisa
rg -q '^    steps: mutable i32 = 0$' \
    build/multi_declarator_mutability.generated.elisa
clang -std=c11 testdata/fixtures/multi_declarator_mutability.c \
    -o build/multi_declarator_mutability.native
"$elisa_bin" -emit obj -O0 \
    -o build/multi_declarator_mutability.generated.o \
    build/multi_declarator_mutability.generated.elisa
clang -Wl,-dead_strip -o build/multi_declarator_mutability.generated \
    build/multi_declarator_mutability.generated.o
set +e
./build/multi_declarator_mutability.native
multi_declarator_mutability_native_rc=$?
./build/multi_declarator_mutability.generated
multi_declarator_mutability_generated_rc=$?
set -e
[ "$multi_declarator_mutability_native_rc" -eq 0 ] && \
    [ "$multi_declarator_mutability_generated_rc" -eq 0 ]

test_translator_bounded testdata/fixtures/nested_loop_goto.c > build/nested_loop_goto.generated.elisa
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

# A goto that exits a loop from inside a nested switch cannot become `break`:
# that would target the switch rather than the loop. Keep it as a CFG edge.
test_translator_bounded testdata/fixtures/goto_out_of_loop_from_switch.c \
    > build/goto_out_of_loop_from_switch.generated.elisa
rg -q 'control_state: mutable i32 = 0|flow_state: mutable i32 = 0|elisa_control_state: mutable i32 = 0|state_machine: mutable i32 = 0' \
    build/goto_out_of_loop_from_switch.generated.elisa
clang -std=c11 testdata/fixtures/goto_out_of_loop_from_switch.c \
    -o build/goto_out_of_loop_from_switch.native
"$elisa_bin" -emit obj -O0 -o build/goto_out_of_loop_from_switch.generated.o \
    build/goto_out_of_loop_from_switch.generated.elisa
clang -Wl,-dead_strip -o build/goto_out_of_loop_from_switch.generated \
    build/goto_out_of_loop_from_switch.generated.o
set +e
./build/goto_out_of_loop_from_switch.native
goto_out_of_loop_from_switch_native_rc=$?
./build/goto_out_of_loop_from_switch.generated
goto_out_of_loop_from_switch_generated_rc=$?
set -e
[ "$goto_out_of_loop_from_switch_native_rc" -eq 0 ] && \
    [ "$goto_out_of_loop_from_switch_generated_rc" -eq 0 ]

test_translator_bounded testdata/fixtures/switch_before_goto.c > build/switch_before_goto.generated.elisa
rg -q 'control_state: mutable i32 = 0|goto_state: mutable i32 = 0|flow_state: mutable i32 = 0' build/switch_before_goto.generated.elisa
if ! sed -n '/^def main/,/^def /p' build/switch_before_goto.generated.elisa | rg -q 'match '; then
    echo "switch embedded in CFG was dropped" >&2
    exit 1
fi
clang -std=c11 testdata/fixtures/switch_before_goto.c -o build/switch_before_goto.native
"$elisa_bin" -emit obj -O0 -o build/switch_before_goto.generated.o build/switch_before_goto.generated.elisa
clang -Wl,-dead_strip -o build/switch_before_goto.generated build/switch_before_goto.generated.o
set +e
./build/switch_before_goto.native
switch_before_goto_native_rc=$?
./build/switch_before_goto.generated
switch_before_goto_generated_rc=$?
set -e
[ "$switch_before_goto_native_rc" -eq 0 ] && [ "$switch_before_goto_generated_rc" -eq 0 ]

test_translator_bounded testdata/fixtures/switch_selector_once_goto.c \
    > build/switch_selector_once_goto.generated.elisa
rg -q '__elisa_transpiler_switch_selector_[0-9]+: i32 = select_value\(\)' \
    build/switch_selector_once_goto.generated.elisa
rg -q 'match __elisa_transpiler_switch_selector_[0-9]+:' \
    build/switch_selector_once_goto.generated.elisa
clang -std=c11 testdata/fixtures/switch_selector_once_goto.c \
    -o build/switch_selector_once_goto.native
"$elisa_bin" -emit obj -O0 \
    -o build/switch_selector_once_goto.generated.o \
    build/switch_selector_once_goto.generated.elisa
clang -Wl,-dead_strip -o build/switch_selector_once_goto.generated \
    build/switch_selector_once_goto.generated.o
set +e
./build/switch_selector_once_goto.native
switch_selector_once_goto_native_rc=$?
./build/switch_selector_once_goto.generated
switch_selector_once_goto_generated_rc=$?
set -e
[ "$switch_selector_once_goto_native_rc" -eq 0 ] && \
    [ "$switch_selector_once_goto_generated_rc" -eq 0 ]

test_translator_bounded testdata/fixtures/loop_condition_effects.c \
    > build/loop_condition_effects.generated.elisa
clang -std=c11 testdata/fixtures/loop_condition_effects.c -o build/loop_condition_effects.native
"$elisa_bin" -emit obj -O0 -o build/loop_condition_effects.generated.o \
    build/loop_condition_effects.generated.elisa
clang -Wl,-dead_strip -o build/loop_condition_effects.generated \
    build/loop_condition_effects.generated.o
set +e
./build/loop_condition_effects.native
loop_condition_effects_native_rc=$?
./build/loop_condition_effects.generated
loop_condition_effects_generated_rc=$?
set -e
[ "$loop_condition_effects_native_rc" -eq 0 ] && [ "$loop_condition_effects_generated_rc" -eq 0 ]
rg -q 'continue' build/loop_condition_effects.generated.elisa
rg -q 'while true:' build/loop_condition_effects.generated.elisa

test_translator_bounded testdata/fixtures/compound_assignment_conditional_place.c \
    > build/compound_assignment_conditional_place.generated.elisa
clang -std=c11 testdata/fixtures/compound_assignment_conditional_place.c \
    -o build/compound_assignment_conditional_place.native
"$elisa_bin" -emit obj -O0 \
    -o build/compound_assignment_conditional_place.generated.o \
    build/compound_assignment_conditional_place.generated.elisa
clang -Wl,-dead_strip -o build/compound_assignment_conditional_place.generated \
    build/compound_assignment_conditional_place.generated.o
set +e
./build/compound_assignment_conditional_place.native
compound_assignment_conditional_place_native_rc=$?
./build/compound_assignment_conditional_place.generated
compound_assignment_conditional_place_generated_rc=$?
set -e
[ "$compound_assignment_conditional_place_native_rc" -eq 0 ] && \
    [ "$compound_assignment_conditional_place_generated_rc" -eq 0 ]

test_translator_bounded testdata/fixtures/indirect_call_conditional_comma.c \
    > build/indirect_call_conditional_comma.generated.elisa
rg -q '^        __elisa_transpiler_indirect_callee_[0-9]+ <- operation$' \
    build/indirect_call_conditional_comma.generated.elisa
awk '
    /^        __elisa_transpiler_indirect_callee_[0-9]+ <- operation$/ && !capture { capture = NR }
    /^            mark_true\(\)$/ && !effect { effect = NR }
    /^        __elisa_transpiler_call_argument_[0-9]+ <- \(mark_second_argument\(\) \+ 2\)$/ && !residual { residual = NR }
    /^        true_result: i32 = __elisa_transpiler_indirect_callee_[0-9]+\(/ && !call { call = NR }
    END { if (!(capture > 0 && effect > capture && residual > effect && call > residual)) exit 1 }
' build/indirect_call_conditional_comma.generated.elisa
clang -std=c11 testdata/fixtures/indirect_call_conditional_comma.c \
    -o build/indirect_call_conditional_comma.native
"$elisa_bin" -emit obj -O0 -o build/indirect_call_conditional_comma.generated.o \
    build/indirect_call_conditional_comma.generated.elisa
clang -Wl,-dead_strip -o build/indirect_call_conditional_comma.generated \
    build/indirect_call_conditional_comma.generated.o
set +e
./build/indirect_call_conditional_comma.native
indirect_call_conditional_comma_native_rc=$?
./build/indirect_call_conditional_comma.generated
indirect_call_conditional_comma_generated_rc=$?
set -e
[ "$indirect_call_conditional_comma_native_rc" -eq 0 ] && \
    [ "$indirect_call_conditional_comma_generated_rc" -eq 0 ]

# The function designator may itself be computed. Capture the factory result
# before beginning effectful argument evaluation, then invoke that exact value.
test_translator_bounded testdata/fixtures/computed_function_pointer_call.c \
    > build/computed_function_pointer_call.generated.elisa
awk '
    /__elisa_transpiler_indirect_callee_[0-9]+ <- .*select_table\(\).*operation/ && !capture { capture = NR }
    /__elisa_transpiler_call_argument_[0-9]+ <- next_argument\(\)/ && !argument { argument = NR }
    /__elisa_transpiler_indirect_callee_[0-9]+\(/ && !call { call = NR }
    /__elisa_transpiler_indirect_callee_[0-9]+ <- \(combine if selector != 0 else combine\)/ && !conditional_capture { conditional_capture = NR }
    /^[[:space:]]+next_argument\(\)$/ && conditional_capture && NR > conditional_capture && !conditional_argument { conditional_argument = NR }
    /conditional_result: i32 = __elisa_transpiler_indirect_callee_[0-9]+\(/ && !conditional_call { conditional_call = NR }
    END {
        if (!(capture > 0 && argument > capture && call > argument)) exit 1
        if (!(conditional_capture > 0 && conditional_argument > conditional_capture && conditional_call > conditional_argument)) exit 1
    }
' build/computed_function_pointer_call.generated.elisa
clang -std=c11 testdata/fixtures/computed_function_pointer_call.c \
    -o build/computed_function_pointer_call.native
"$elisa_bin" -emit obj -O0 -o build/computed_function_pointer_call.generated.o \
    build/computed_function_pointer_call.generated.elisa
clang -Wl,-dead_strip -o build/computed_function_pointer_call.generated \
    build/computed_function_pointer_call.generated.o
set +e
./build/computed_function_pointer_call.native
computed_function_pointer_call_native_rc=$?
./build/computed_function_pointer_call.generated
computed_function_pointer_call_generated_rc=$?
set -e
[ "$computed_function_pointer_call_native_rc" -eq 0 ] && \
    [ "$computed_function_pointer_call_generated_rc" -eq 0 ]

# A typedef'd callback may also be returned by a C function and immediately
# called. Preserve the callback result type and capture it before arg effects.
test_translator_bounded testdata/fixtures/function_pointer_return.c \
    > build/function_pointer_return.generated.elisa
rg -q '^def select_operation\(should_return_operation: i32\) -> \(fn\(i32, i32\) -> i32\)\?' \
    build/function_pointer_return.generated.elisa
awk '
    /__elisa_transpiler_indirect_callee_[0-9]+ <- select_operation\(1\)/ && !capture { capture = NR }
    /__elisa_transpiler_call_argument_[0-9]+ <- next_argument\(\)/ && !argument { argument = NR }
    /result: i32 = __elisa_transpiler_indirect_callee_[0-9]+\(/ && !call { call = NR }
    END { if (!(capture > 0 && argument > capture && call > argument)) exit 1 }
' build/function_pointer_return.generated.elisa
clang -std=c11 testdata/fixtures/function_pointer_return.c \
    -o build/function_pointer_return.native
"$elisa_bin" -emit obj -O0 -o build/function_pointer_return.generated.o \
    build/function_pointer_return.generated.elisa
clang -Wl,-dead_strip -o build/function_pointer_return.generated \
    build/function_pointer_return.generated.o
set +e
./build/function_pointer_return.native
function_pointer_return_native_rc=$?
./build/function_pointer_return.generated
function_pointer_return_generated_rc=$?
set -e
[ "$function_pointer_return_native_rc" -eq 0 ] && \
    [ "$function_pointer_return_generated_rc" -eq 0 ]

# C++17 guarantees that argument evaluations are indeterminately sequenced:
# each side-effecting argument must complete before another begins. Either
# argument order is valid, but interleaving the two traces is not.
mkdir -p build/call_argument_groups_project
test_translator_bounded \
    --compile-commands testdata/fixtures/call_argument_groups_compile_commands.json \
    --output-dir build/call_argument_groups_project
test_clangxx_bounded -std=c++17 testdata/fixtures/call_argument_groups.cpp \
    -o build/call_argument_groups.native
"$elisa_bin" -emit obj -O0 -o build/call_argument_groups.generated.o \
    build/call_argument_groups_project/elisa_project.elisa
clang -Wl,-dead_strip -o build/call_argument_groups.generated \
    build/call_argument_groups.generated.o
set +e
./build/call_argument_groups.native
call_argument_groups_native_rc=$?
./build/call_argument_groups.generated
call_argument_groups_generated_rc=$?
set -e
[ "$call_argument_groups_native_rc" -eq 0 ] && \
    [ "$call_argument_groups_generated_rc" -eq 0 ]
call_argument_groups_main=$(sed -n '/^def main/,/^def /p' \
    build/call_argument_groups_project/call_argument_groups.elisa)
call_argument_groups_first=$(printf '%s\n' "$call_argument_groups_main" | \
    rg -n 'first_argument\(' | head -1 | cut -d: -f1)
call_argument_groups_second=$(printf '%s\n' "$call_argument_groups_main" | \
    rg -n 'second_argument\(' | head -1 | cut -d: -f1)
[ -n "$call_argument_groups_first" ] && \
    [ -n "$call_argument_groups_second" ] && \
    [ "$call_argument_groups_first" -lt "$call_argument_groups_second" ]
call_argument_groups_volatile_read=$(printf '%s\n' "$call_argument_groups_main" | \
    rg -n '__elisa_transpiler_call_argument_[0-9]+ <- volatile_value$' | \
    head -1 | cut -d: -f1)
call_argument_groups_volatile_write=$(printf '%s\n' "$call_argument_groups_main" | \
    rg -n '__elisa_transpiler_call_argument_[0-9]+ <- set_volatile\(\)$' | \
    head -1 | cut -d: -f1)
[ -n "$call_argument_groups_volatile_read" ] && \
    [ -n "$call_argument_groups_volatile_write" ] && \
    [ "$call_argument_groups_volatile_read" -lt "$call_argument_groups_volatile_write" ]

set +e
test_translator_bounded testdata/fixtures/unsupported_for.c \
    > build/unsupported_for.out 2> build/unsupported_for.err
unsupported_for_rc=$?
set -e
[ "$unsupported_for_rc" -ne 0 ]
[ ! -s build/unsupported_for.out ]
rg -q "elisa-c-transpiler: unsupported expression AddrLabelExpr at" build/unsupported_for.err

set +e
test_translator_bounded testdata/fixtures/conditional_comma_unsupported.c \
    > build/conditional_comma_unsupported.out 2> build/conditional_comma_unsupported.err
conditional_comma_unsupported_rc=$?
set -e
[ "$conditional_comma_unsupported_rc" -ne 0 ]
[ ! -s build/conditional_comma_unsupported.out ]
rg -q 'unsupported expression BinaryOperator at testdata/fixtures/conditional_comma_unsupported.c:' build/conditional_comma_unsupported.err
rg -q 'unsupported expression ConditionalOperator at testdata/fixtures/conditional_comma_unsupported.c:' build/conditional_comma_unsupported.err
rg -q 'unsupported expression CallExpr at testdata/fixtures/conditional_comma_unsupported.c:' build/conditional_comma_unsupported.err
rg -Fq '[missing translator capability: volatile comma operand sequencing]' build/conditional_comma_unsupported.err
rg -Fq '[missing translator capability: comma effects in record-valued conditional]' build/conditional_comma_unsupported.err
rg -Fq '[missing translator capability: sequencing effectful aggregate call argument]' build/conditional_comma_unsupported.err

set +e
test_translator_bounded testdata/fixtures/const_volatile_comma.c \
    > build/const_volatile_comma.out 2> build/const_volatile_comma.err
const_volatile_comma_rc=$?
set -e
[ "$const_volatile_comma_rc" -ne 0 ]
[ ! -s build/const_volatile_comma.out ]
rg -q 'unsupported expression BinaryOperator at testdata/fixtures/const_volatile_comma.c:' \
    build/const_volatile_comma.err
rg -Fq '[missing translator capability: volatile comma operand sequencing]' build/const_volatile_comma.err

set +e
test_translator_bounded testdata/fixtures/conditional_comma_lvalue_unsupported.cpp \
    > build/conditional_comma_lvalue_unsupported.out 2> build/conditional_comma_lvalue_unsupported.err
conditional_comma_lvalue_unsupported_rc=$?
set -e
[ "$conditional_comma_lvalue_unsupported_rc" -ne 0 ]
[ ! -s build/conditional_comma_lvalue_unsupported.out ]
rg -q 'unsupported expression ConditionalOperator at testdata/fixtures/conditional_comma_lvalue_unsupported.cpp:' build/conditional_comma_lvalue_unsupported.err
rg -Fq '[missing translator capability: comma effects in non-prvalue conditional]' build/conditional_comma_lvalue_unsupported.err

# Rewrite accounting is opt-in and diagnostic-only: the generated Elisa bytes
# must remain identical while the report records only proven applied rules.
test_translator_bounded testdata/fixtures/integer_constant_semantics.c \
    > build/integer_constant_semantics.normal.elisa
test_translator_bounded --explain-rewrites \
    testdata/fixtures/integer_constant_semantics.c \
    > build/integer_constant_semantics.explained.elisa \
    2> build/integer_constant_semantics.explained.err
cmp build/integer_constant_semantics.normal.elisa \
    build/integer_constant_semantics.explained.elisa
rg -q '^rewrite-stats source=testdata/fixtures/integer_constant_semantics.c redundant_casts=[0-9]+ identity_binaries=[0-9]+ integer_folds=[1-9][0-9]* constant_conditions=[0-9]+ boolean_predicates=[0-9]+ conditional_prunes=[0-9]+$' \
    build/integer_constant_semantics.explained.err

set +e
test_translator_bounded testdata/fixtures/macro_unsupported.c \
    > build/macro_unsupported.out 2> build/macro_unsupported.err
macro_unsupported_rc=$?
set -e
[ "$macro_unsupported_rc" -ne 0 ]
[ ! -s build/macro_unsupported.out ]
rg -q 'unsupported expression AddrLabelExpr at testdata/fixtures/macro_unsupported.c:5:[0-9]+ \(macro spelling at testdata/fixtures/macro_unsupported.c:1:[0-9]+; expansion at testdata/fixtures/macro_unsupported.c:5:[0-9]+\)' build/macro_unsupported.err

repo_root=$(pwd -P)
macro_source_physical_hex=$(printf '%s' "$repo_root/testdata/fixtures/macro_origin_header.c" | od -An -tx1 | tr -d ' \n')
macro_header_physical_hex=$(printf '%s' "$repo_root/testdata/fixtures/macro_origin.h" | od -An -tx1 | tr -d ' \n')
set +e
test_translator_bounded --dump-typed-ir testdata/fixtures/macro_origin_header.c \
    > build/macro_origin_header.out 2> build/macro_origin_header.err
macro_origin_header_rc=$?
set -e
[ "$macro_origin_header_rc" -ne 0 ]
[ ! -s build/macro_origin_header.out ]
rg -q 'unsupported expression AddrLabelExpr at testdata/fixtures/macro_origin_header.c:5:[0-9]+ \(macro spelling at testdata/fixtures/macro_origin.h:1:[0-9]+; expansion at testdata/fixtures/macro_origin_header.c:5:[0-9]+\)' build/macro_origin_header.err
rg -q 'unsupported expression AddrLabelExpr at testdata/fixtures/macro_origin_header.c:13:[0-9]+ \(macro spelling at testdata/fixtures/macro_origin.h:1:[0-9]+; expansion at testdata/fixtures/macro_origin_header.c:13:[0-9]+\)' build/macro_origin_header.err
rg -q 'range_start_offset=[0-9]+ range_end_offset=[0-9]+' build/macro_origin_header.err
rg -q "physical_source_hex=${macro_source_physical_hex}" build/macro_origin_header.err
rg -q "spelling_physical_hex=${macro_header_physical_hex}" build/macro_origin_header.err
rg -q "expansion_physical_hex=${macro_source_physical_hex}" build/macro_origin_header.err
set +e
test_translator_bounded --dump-typed-ir \
    --compile-commands testdata/fixtures/macro_origin_compile_commands.json \
    > build/macro_origin_compile_commands.out 2> build/macro_origin_compile_commands.err
macro_origin_compile_commands_rc=$?
set -e
[ "$macro_origin_compile_commands_rc" -ne 0 ]
[ ! -s build/macro_origin_compile_commands.out ]
rg -q "physical_source_hex=${macro_source_physical_hex}" build/macro_origin_compile_commands.err
rg -q "spelling_physical_hex=${macro_header_physical_hex}" build/macro_origin_compile_commands.err

macro_nested_source_physical_hex=$(printf '%s' "$repo_root/testdata/fixtures/macro_origin_nested.c" | od -An -tx1 | tr -d ' \n')
macro_include_relative_hex=$(printf '%s' 'testdata/fixtures/macro_origin_include.h' | od -An -tx1 | tr -d ' \n')
macro_include_physical_hex=$(printf '%s' "$repo_root/testdata/fixtures/macro_origin_include.h" | od -An -tx1 | tr -d ' \n')
set +e
test_translator_bounded --dump-typed-ir testdata/fixtures/macro_origin_nested.c \
    > build/macro_origin_nested.out 2> build/macro_origin_nested.err
macro_origin_nested_rc=$?
set -e
[ "$macro_origin_nested_rc" -ne 0 ]
[ ! -s build/macro_origin_nested.out ]
rg -q "spelling_included_from_hex=${macro_include_relative_hex}" build/macro_origin_nested.err
rg -q "spelling_included_from_physical_hex=${macro_include_physical_hex}" build/macro_origin_nested.err
rg -q "physical_source_hex=${macro_nested_source_physical_hex}" build/macro_origin_nested.err

macro_alias_dir=$(mktemp -d build/macro-origin-alias.XXXXXX)
ln -s "$repo_root/testdata/fixtures/macro_unsupported.c" "$macro_alias_dir/macro_unsupported_alias.c"
macro_alias_source_hex=$(printf '%s' "$macro_alias_dir/macro_unsupported_alias.c" | od -An -tx1 | tr -d ' \n')
macro_unsupported_physical_hex=$(printf '%s' "$repo_root/testdata/fixtures/macro_unsupported.c" | od -An -tx1 | tr -d ' \n')
set +e
test_translator_bounded --dump-typed-ir "$macro_alias_dir/macro_unsupported_alias.c" \
    > build/macro_unsupported_alias.out 2> build/macro_unsupported_alias.err
macro_unsupported_alias_rc=$?
set -e
[ "$macro_unsupported_alias_rc" -ne 0 ]
[ ! -s build/macro_unsupported_alias.out ]
rg -q "source_hex=${macro_alias_source_hex}" build/macro_unsupported_alias.err
rg -q "physical_source_hex=${macro_unsupported_physical_hex}" build/macro_unsupported_alias.err
rg -q "expansion_physical_hex=${macro_unsupported_physical_hex}" build/macro_unsupported_alias.err

# More than 32 declarations force the per-translation-unit ID table through a
# resize. The forward declaration also checks that the redeclaration link is
# still usable after table growth.
test_translator_bounded testdata/fixtures/declaration_index.c > build/declaration_index.generated.elisa
rg -q '^global mutable declaration_index_global_35: i32 = zeroed$' build/declaration_index.generated.elisa
clang -std=c11 testdata/fixtures/declaration_index.c -o build/declaration_index.native
"$elisa_bin" -emit obj -O0 -o build/declaration_index.generated.o build/declaration_index.generated.elisa
clang -Wl,-dead_strip -o build/declaration_index.generated build/declaration_index.generated.o
set +e
./build/declaration_index.native
declaration_index_native_rc=$?
./build/declaration_index.generated
declaration_index_generated_rc=$?
set -e
[ "$declaration_index_native_rc" -eq 0 ] && [ "$declaration_index_generated_rc" -eq 0 ]
test_translator_bounded --dump-typed-ir testdata/fixtures/declaration_index.c \
    > build/declaration_index.dump.stdout.elisa 2> build/declaration_index.dump.typed-ir
rg -q '^typed-ir-v13$' build/declaration_index.dump.typed-ir
rg -q '^declaration-info [0-9]+ canonical=false has_previous=true user=true extern=false cpp_iterator_map_type_hex= cpp_iterator_name_hex= cpp_iterator_line=0$' \
    build/declaration_index.dump.typed-ir

# Same-spelled typedefs from separate C++ scopes must not collapse to one type.
test_translator_bounded testdata/fixtures/typedef_identity.cpp > build/typedef_identity.generated.elisa
rg -q '^def first_word\(.*\) -> u32:' build/typedef_identity.generated.elisa
rg -q '^def second_word\(.*\) -> u64:' build/typedef_identity.generated.elisa
test_clangxx_bounded -std=gnu++11 testdata/fixtures/typedef_identity.cpp -o build/typedef_identity.native
"$elisa_bin" -emit obj -O0 -o build/typedef_identity.generated.o build/typedef_identity.generated.elisa
clang -Wl,-dead_strip -o build/typedef_identity.generated build/typedef_identity.generated.o
set +e
./build/typedef_identity.native
typedef_identity_native_rc=$?
./build/typedef_identity.generated
typedef_identity_generated_rc=$?
set -e
[ "$typedef_identity_native_rc" -eq 0 ] && [ "$typedef_identity_generated_rc" -eq 0 ]

# Rewriting loop tests into statement preludes must not change the number,
# ordering or atomicity of observable reads. Until the IR models these accesses
# explicitly, reject volatile and atomic conditions before emitting output.
# Keep one unsupported loop per source file because translation intentionally
# fails at the first unsupported function. The first file also proves that a
# pointer-to-volatile-pointee read is not confused with reading a volatile
# pointer object. Expression ranges survive AST projection so diagnostics name
# the actual loop-test line rather than the unknown 0:0 coordinate.
assert_loop_test_rejected() {
    loop_fixture=$1
    loop_line=$2
    loop_case=$3
    set +e
    test_translator_bounded "$loop_fixture" \
        > "build/$loop_case.out" \
        2> "build/$loop_case.err"
    loop_rc=$?
    set -e
    [ "$loop_rc" -ne 0 ]
    [ ! -s "build/$loop_case.out" ]
    rg -Fq "unsupported expression BinaryOperator at $loop_fixture:$loop_line:" \
        "build/$loop_case.err"
    loop_diag_count=$(rg -Fc 'unsupported volatile or atomic loop-test access' \
        "build/$loop_case.err")
    [ "$loop_diag_count" -eq 1 ]
}

assert_loop_test_rejected \
    testdata/fixtures/volatile_atomic_loop_conditions.c 15 \
    volatile_atomic_loop_conditions
assert_loop_test_rejected \
    testdata/fixtures/atomic_for_loop_condition.c 7 \
    atomic_for_loop_condition
assert_loop_test_rejected \
    testdata/fixtures/atomic_builtin_do_loop_condition.c 7 \
    atomic_builtin_do_loop_condition
assert_loop_test_rejected \
    testdata/fixtures/volatile_pointer_slot_loop_condition.c 5 \
    volatile_pointer_slot_loop_condition
