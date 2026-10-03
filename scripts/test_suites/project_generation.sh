# Multi-translation-unit and compile-database project checks.
# This project deliberately translates module_a before module_b; module_b
# calls add_one, so it exercises project function state after the first
# translation-unit region has been reclaimed.
mkdir -p build/project-db
./build/elisa-c-transpiler --compile-commands testdata/fixtures/compile_commands.json \
    --output-dir build/project-db
rg -q 'include "module_a.elisa"' build/project-db/elisa_project.elisa
rg -q 'include "other.module_a.elisa"' build/project-db/elisa_project.elisa
rg -q 'include "module_b.elisa"' build/project-db/elisa_project.elisa
rg -q 'return \(value \+ 1\)' build/project-db/module_a.elisa
ELISA_STAGE1_MAX_RSS_KB=4194304 bash "$stage1_worktree/scripts/elisac_stage1.sh" \
    -emit exe -O0 -o build/project-db/project \
    "$root_dir/build/project-db/elisa_project.elisa"
set +e
./build/project-db/project
project_generated_rc=$?
set -e
[ "$project_generated_rc" -eq 0 ]

# A later generation may contain fewer source units. Remove only modules listed
# by the previous translator manifest; an unrelated file in the same directory
# must survive unchanged.
mkdir -p build/project-obsolete
./build/elisa-c-transpiler --compile-commands testdata/fixtures/compile_commands.json \
    --output-dir build/project-obsolete
test -e build/project-obsolete/module_a.elisa
test -e build/project-obsolete/module_b.elisa
touch build/project-obsolete/user-owned.elisa
./build/elisa-c-transpiler --output-dir build/project-obsolete testdata/fixtures/simple.c
test -e build/project-obsolete/simple.elisa
test ! -e build/project-obsolete/module_a.elisa
test ! -e build/project-obsolete/module_b.elisa
test ! -e build/project-obsolete/other.module_a.elisa
test -e build/project-obsolete/user-owned.elisa

# C++20's unordered_map::contains is supplied by the translator-owned cpp
# adapter; keep the language standard from the compilation database intact.
./build/elisa-c-transpiler \
    --max-frontend-output-bytes 268435456 \
    --compile-commands testdata/fixtures/cpp_unordered_map_contains_compile_commands.json \
    --output-dir build
rg -q '^include "../cpp_lib/unordered_map.elisa"$' build/elisa_project.elisa
! rg -q '^include "../cpp_lib/unordered_map.elisa"$' build/cpp_unordered_map_contains.elisa
rg -q 'values\.contains\(7\)' build/cpp_unordered_map_contains.elisa
rg -q 'values\.contains\(8\)' build/cpp_unordered_map_contains.elisa
! rg -q '^def elisa_nonnull' build/elisa_project.elisa
! rg -q '^def elisa_nonnull_readonly' build/elisa_project.elisa
! rg -q '^extern va_list' build/elisa_project.elisa
clang++ -std=c++20 testdata/fixtures/cpp_unordered_map_contains.cpp \
    -o build/cpp_unordered_map_contains.native
ELISA_STAGE1_MAX_RSS_KB=4194304 bash "$stage1_worktree/scripts/elisac_stage1.sh" \
    -emit exe -O0 -o build/cpp_unordered_map_contains.generated \
    build/elisa_project.elisa
set +e
./build/cpp_unordered_map_contains.native
cpp_map_contains_native_rc=$?
./build/cpp_unordered_map_contains.generated
cpp_map_contains_generated_rc=$?
set -e
[ "$cpp_map_contains_native_rc" -eq 0 ] && [ "$cpp_map_contains_generated_rc" -eq 0 ]

# Explicit compatibility/runtime roots make the generated project independent
# of the translator's repository-relative cpp_lib wrapper. Copy the generated
# Elisa project away from the translator output directory and compile it there.
mkdir -p build/cpp-relocatable-support build/cpp-relocatable-moved
./build/elisa-c-transpiler \
    --max-frontend-output-bytes 268435456 \
    --cpp-lib-dir "$root_dir/cpp_lib" \
    --elisa-std-dir "$stage1_worktree/elisacore_std" \
    --compile-commands testdata/fixtures/cpp_unordered_map_contains_compile_commands.json \
    --output-dir build/cpp-relocatable-support
rg -q '^include ".*/elisacore_std/elisacore_runtime\.elisa"$' build/cpp-relocatable-support/elisa_project.elisa
rg -q '^include ".*/elisacore_std/collections\.elisa"$' build/cpp-relocatable-support/elisa_project.elisa
rg -q '^include ".*/cpp_lib/unordered_map_core\.elisa"$' build/cpp-relocatable-support/elisa_project.elisa
! rg -q 'include "\.\./cpp_lib/unordered_map\.elisa"' build/cpp-relocatable-support/elisa_project.elisa
cp -f build/cpp-relocatable-support/*.elisa build/cpp-relocatable-moved/
ELISA_STAGE1_MAX_RSS_KB=4194304 bash "$stage1_worktree/scripts/elisac_stage1.sh" \
    -emit exe -O0 -o build/cpp-relocatable-moved/generated \
    build/cpp-relocatable-moved/elisa_project.elisa
./build/cpp-relocatable-moved/generated

mkdir -p build/project-identity build/project-identity-reversed
./build/elisa-c-transpiler \
    --compile-commands testdata/fixtures/project_identity_compile_commands.json \
    --output-dir build/project-identity
./build/elisa-c-transpiler \
    --compile-commands testdata/fixtures/project_identity_compile_commands_reversed.json \
    --output-dir build/project-identity-reversed
rg -o --no-filename '^include "(part|symbol-unit|symbol_unit)_[0-9]+\.elisa"$' \
    build/project-identity/elisa_project.elisa \
    | sed -E 's/^include "(.*)"$/\1/' | LC_ALL=C sort \
    > build/project-identity/modules.sorted
rg -o --no-filename '^include "(part|symbol-unit|symbol_unit)_[0-9]+\.elisa"$' \
    build/project-identity-reversed/elisa_project.elisa \
    | sed -E 's/^include "(.*)"$/\1/' | LC_ALL=C sort \
    > build/project-identity-reversed/modules.sorted
cmp build/project-identity/modules.sorted build/project-identity-reversed/modules.sorted
cmp build/project-identity/elisa_project.elisa build/project-identity-reversed/elisa_project.elisa
[ "$(wc -l < build/project-identity/modules.sorted | tr -d ' ')" -eq 4 ]
for generated_module in $(cat build/project-identity/modules.sorted); do
    module_stem=${generated_module%.elisa}
    module_hash=${module_stem##*_}
    module_base=${module_stem%_$module_hash}
    initializer_base=$(printf '%s' "$module_base" | sed -E 's/[^[:alnum:]_]/_/g')
    initializer_name="elisa_init_${initializer_base}_${module_hash}"
    rg -q "^def ${initializer_name}\\(" "build/project-identity/${generated_module}"
    rg -q "^def ${initializer_name}\\(" "build/project-identity-reversed/${generated_module}"
    rg -q "^        ${initializer_name}\\(\\)$" build/project-identity/elisa_project.elisa
    rg -q "^        ${initializer_name}\\(\\)$" build/project-identity-reversed/elisa_project.elisa
    cmp "build/project-identity/${generated_module}" "build/project-identity-reversed/${generated_module}"
done
clang -std=c11 \
    testdata/fixtures/project_identity/a/part.c \
    testdata/fixtures/project_identity/b/part.c \
    testdata/fixtures/project_identity/sanitized_a/symbol-unit.c \
    testdata/fixtures/project_identity/sanitized_b/symbol_unit.c \
    testdata/fixtures/project_identity/main.c \
    -o build/project-identity/native
./build/project-identity/native
ELISA_STAGE1_MAX_RSS_KB=4194304 bash "$stage1_worktree/scripts/elisac_stage1.sh" \
    -emit exe -O0 -o build/project-identity/generated \
    "$root_dir/build/project-identity/elisa_project.elisa"
./build/project-identity/generated
ELISA_STAGE1_MAX_RSS_KB=4194304 bash "$stage1_worktree/scripts/elisac_stage1.sh" \
    -emit exe -O0 -o build/project-identity-reversed/generated \
    "$root_dir/build/project-identity-reversed/elisa_project.elisa"
./build/project-identity-reversed/generated

mkdir -p build/project-internal-linkage build/project-internal-linkage-reversed
./build/elisa-c-transpiler \
    --compile-commands testdata/fixtures/project_internal_linkage_compile_commands.json \
    --output-dir build/project-internal-linkage
./build/elisa-c-transpiler \
    --compile-commands testdata/fixtures/project_internal_linkage_compile_commands_reversed.json \
    --output-dir build/project-internal-linkage-reversed
internal_symbols=$(rg -o --no-filename '__elisa_internal_[0-9]+_helper__arity_1__type_[0-9]+' \
    build/project-internal-linkage/*.elisa | LC_ALL=C sort -u | wc -l | tr -d ' ')
[ "$internal_symbols" -eq 2 ]
reversed_internal_symbols=$(rg -o --no-filename '__elisa_internal_[0-9]+_helper__arity_1__type_[0-9]+' \
    build/project-internal-linkage-reversed/*.elisa | LC_ALL=C sort -u | wc -l | tr -d ' ')
[ "$reversed_internal_symbols" -eq 2 ]
header_internal_symbols=$(rg -o --no-filename '__elisa_internal_[0-9]+_shared_helper__arity_1__type_[0-9]+' \
    build/project-internal-linkage/*.elisa | LC_ALL=C sort -u | wc -l | tr -d ' ')
[ "$header_internal_symbols" -eq 2 ]
rg -o --no-filename '__elisa_internal_[0-9]+_[[:alnum:]_]+__arity_[0-9]+__type_[0-9]+' \
    build/project-internal-linkage/*.elisa | LC_ALL=C sort -u \
    > build/project-internal-linkage/internal-symbols.sorted
rg -o --no-filename '__elisa_internal_[0-9]+_[[:alnum:]_]+__arity_[0-9]+__type_[0-9]+' \
    build/project-internal-linkage-reversed/*.elisa | LC_ALL=C sort -u \
    > build/project-internal-linkage-reversed/internal-symbols.sorted
[ "$(wc -l < build/project-internal-linkage/internal-symbols.sorted | tr -d ' ')" -eq 4 ]
cmp build/project-internal-linkage/internal-symbols.sorted \
    build/project-internal-linkage-reversed/internal-symbols.sorted
rg -o --no-filename '^global mutable __elisa_internal_[0-9]+_[[:alnum:]_]+__global_[0-9]+' \
    build/project-internal-linkage/*.elisa | LC_ALL=C sort -u \
    > build/project-internal-linkage/internal-globals.sorted
rg -o --no-filename '^global mutable __elisa_internal_[0-9]+_[[:alnum:]_]+__global_[0-9]+' \
    build/project-internal-linkage-reversed/*.elisa | LC_ALL=C sort -u \
    > build/project-internal-linkage-reversed/internal-globals.sorted
[ "$(wc -l < build/project-internal-linkage/internal-globals.sorted | tr -d ' ')" -eq 6 ]
cmp build/project-internal-linkage/internal-globals.sorted \
    build/project-internal-linkage-reversed/internal-globals.sorted
clang -std=c11 \
    -Itestdata/fixtures/project_internal_linkage \
    testdata/fixtures/project_internal_linkage/alpha.c \
    testdata/fixtures/project_internal_linkage/beta.c \
    testdata/fixtures/project_internal_linkage/main.c \
    -o build/project-internal-linkage/native
./build/project-internal-linkage/native
ELISA_STAGE1_MAX_RSS_KB=4194304 bash "$stage1_worktree/scripts/elisac_stage1.sh" \
    -emit exe -O0 -o build/project-internal-linkage/generated \
    "$root_dir/build/project-internal-linkage/elisa_project.elisa"
./build/project-internal-linkage/generated
ELISA_STAGE1_MAX_RSS_KB=4194304 bash "$stage1_worktree/scripts/elisac_stage1.sh" \
    -emit exe -O0 -o build/project-internal-linkage-reversed/generated \
    "$root_dir/build/project-internal-linkage-reversed/elisa_project.elisa"
./build/project-internal-linkage-reversed/generated

mkdir -p build/project-anonymous-namespace build/project-anonymous-namespace-reversed
./build/elisa-c-transpiler \
    --compile-commands testdata/fixtures/project_anonymous_namespace_compile_commands.json \
    --output-dir build/project-anonymous-namespace
./build/elisa-c-transpiler \
    --compile-commands testdata/fixtures/project_anonymous_namespace_compile_commands_reversed.json \
    --output-dir build/project-anonymous-namespace-reversed
anonymous_function_symbols=$(rg -o --no-filename '__elisa_internal_[0-9]+_helper__arity_1__type_[0-9]+' \
    build/project-anonymous-namespace/*.elisa | LC_ALL=C sort -u | wc -l | tr -d ' ')
[ "$anonymous_function_symbols" -eq 2 ]
rg -o --no-filename '__elisa_internal_[0-9]+_helper__arity_1__type_[0-9]+' \
    build/project-anonymous-namespace/*.elisa | LC_ALL=C sort -u \
    > build/project-anonymous-namespace/internal-symbols.sorted
rg -o --no-filename '__elisa_internal_[0-9]+_helper__arity_1__type_[0-9]+' \
    build/project-anonymous-namespace-reversed/*.elisa | LC_ALL=C sort -u \
    > build/project-anonymous-namespace-reversed/internal-symbols.sorted
cmp build/project-anonymous-namespace/internal-symbols.sorted \
    build/project-anonymous-namespace-reversed/internal-symbols.sorted
rg -o --no-filename '^global mutable __elisa_internal_[0-9]+_project_anonymous_state__global_[0-9]+' \
    build/project-anonymous-namespace/*.elisa | LC_ALL=C sort -u \
    > build/project-anonymous-namespace/internal-globals.sorted
rg -o --no-filename '^global mutable __elisa_internal_[0-9]+_project_anonymous_state__global_[0-9]+' \
    build/project-anonymous-namespace-reversed/*.elisa | LC_ALL=C sort -u \
    > build/project-anonymous-namespace-reversed/internal-globals.sorted
[ "$(wc -l < build/project-anonymous-namespace/internal-globals.sorted | tr -d ' ')" -eq 2 ]
cmp build/project-anonymous-namespace/internal-globals.sorted \
    build/project-anonymous-namespace-reversed/internal-globals.sorted
clang++ -std=c++17 \
    testdata/fixtures/project_anonymous_namespace/alpha.cpp \
    testdata/fixtures/project_anonymous_namespace/beta.cpp \
    testdata/fixtures/project_anonymous_namespace/main.cpp \
    -o build/project-anonymous-namespace/native
./build/project-anonymous-namespace/native
ELISA_STAGE1_MAX_RSS_KB=4194304 bash "$stage1_worktree/scripts/elisac_stage1.sh" \
    -emit exe -O0 -o build/project-anonymous-namespace/generated \
    "$root_dir/build/project-anonymous-namespace/elisa_project.elisa"
./build/project-anonymous-namespace/generated
ELISA_STAGE1_MAX_RSS_KB=4194304 bash "$stage1_worktree/scripts/elisac_stage1.sh" \
    -emit exe -O0 -o build/project-anonymous-namespace-reversed/generated \
    "$root_dir/build/project-anonymous-namespace-reversed/elisa_project.elisa"
./build/project-anonymous-namespace-reversed/generated

mkdir -p build/project-cpp-overloads build/project-cpp-overloads-reversed
./build/elisa-c-transpiler \
    --compile-commands testdata/fixtures/project_cpp_overloads_compile_commands.json \
    --output-dir build/project-cpp-overloads
./build/elisa-c-transpiler \
    --compile-commands testdata/fixtures/project_cpp_overloads_compile_commands_reversed.json \
    --output-dir build/project-cpp-overloads-reversed
cmp build/project-cpp-overloads/elisa_project.elisa build/project-cpp-overloads-reversed/elisa_project.elisa
rg -q '^def project_choose\(value: i32\) -> i32' build/project-cpp-overloads/alpha.elisa
rg -q '^def project_choose\(value: f32\) -> i32' build/project-cpp-overloads/alpha.elisa
rg -q '^def project_choose\(value: f64\) -> i32' build/project-cpp-overloads/alpha.elisa
rg -q '^def project_choose\(value: i64\) -> i32' build/project-cpp-overloads/alpha.elisa
[ "$(rg -o --no-filename '^export fn __c_abi_project_choose__1__abi_[0-9]+' build/project-cpp-overloads/alpha.elisa | LC_ALL=C sort -u | wc -l | tr -d ' ')" -eq 4 ]
[ "$(rg -c '^def __elisa_c_abi_adapter_project_choose__1__' build/project-cpp-overloads/alpha.elisa)" -eq 4 ]
[ "$(rg -c '^export fn .* = __elisa_c_abi_adapter_' build/project-cpp-overloads/alpha.elisa)" -eq 4 ]
! rg -q '^export fn .* = project_choose$' build/project-cpp-overloads/alpha.elisa
[ "$(rg -o --no-filename '^extern __c_external_project_choose__abi_[0-9]+' build/project-cpp-overloads/main.elisa | wc -l | tr -d ' ')" -eq 3 ]
rg -q '__c_external_project_choose__abi_[0-9]+\(\(small\)\.i32\(\)\)' build/project-cpp-overloads/main.elisa
clang++ -std=c++17 \
    testdata/fixtures/project_cpp_overloads/alpha.cpp \
    testdata/fixtures/project_cpp_overloads/main.cpp \
    -o build/project-cpp-overloads/native
./build/project-cpp-overloads/native
ELISA_STAGE1_MAX_RSS_KB=4194304 bash "$stage1_worktree/scripts/elisac_stage1.sh" \
    -emit exe -O0 -o build/project-cpp-overloads/generated \
    "$root_dir/build/project-cpp-overloads/elisa_project.elisa"
./build/project-cpp-overloads/generated
ELISA_STAGE1_MAX_RSS_KB=4194304 bash "$stage1_worktree/scripts/elisac_stage1.sh" \
    -emit exe -O0 -o build/project-cpp-overloads-reversed/generated \
    "$root_dir/build/project-cpp-overloads-reversed/elisa_project.elisa"
./build/project-cpp-overloads-reversed/generated

mkdir -p build/project-cpp-internal-const build/project-cpp-internal-const-reversed
./build/elisa-c-transpiler \
    --compile-commands testdata/fixtures/project_cpp_internal_const_compile_commands.json \
    --output-dir build/project-cpp-internal-const
./build/elisa-c-transpiler \
    --compile-commands testdata/fixtures/project_cpp_internal_const_compile_commands_reversed.json \
    --output-dir build/project-cpp-internal-const-reversed
cmp build/project-cpp-internal-const/elisa_project.elisa build/project-cpp-internal-const-reversed/elisa_project.elisa
rg -q '^global __elisa_internal_[0-9]+_project_configuration__global_[0-9]+: i32 = 17$' build/project-cpp-internal-const/alpha.elisa
rg -q '^global __elisa_internal_[0-9]+_project_configuration__global_[0-9]+: i32 = 29$' build/project-cpp-internal-const/beta.elisa
rg '^global __elisa_internal_[0-9]+_project_configuration__global_[0-9]+:' \
    build/project-cpp-internal-const/alpha.elisa > build/project-cpp-internal-const/alpha.global
rg '^global __elisa_internal_[0-9]+_project_configuration__global_[0-9]+:' \
    build/project-cpp-internal-const/beta.elisa > build/project-cpp-internal-const/beta.global
if cmp -s build/project-cpp-internal-const/alpha.global build/project-cpp-internal-const/beta.global; then
    printf '%s\n' 'C++ namespace-scope const objects unexpectedly share an Elisa global identity' >&2
    exit 1
fi
clang -x c++ -std=c++17 \
    testdata/fixtures/project_cpp_internal_const/alpha.c \
    testdata/fixtures/project_cpp_internal_const/beta.c \
    testdata/fixtures/project_cpp_internal_const/main.c \
    -o build/project-cpp-internal-const/native
./build/project-cpp-internal-const/native
ELISA_STAGE1_MAX_RSS_KB=4194304 bash "$stage1_worktree/scripts/elisac_stage1.sh" \
    -emit exe -O0 -o build/project-cpp-internal-const/generated \
    "$root_dir/build/project-cpp-internal-const/elisa_project.elisa"
./build/project-cpp-internal-const/generated
ELISA_STAGE1_MAX_RSS_KB=4194304 bash "$stage1_worktree/scripts/elisac_stage1.sh" \
    -emit exe -O0 -o build/project-cpp-internal-const-reversed/generated \
    "$root_dir/build/project-cpp-internal-const-reversed/elisa_project.elisa"
./build/project-cpp-internal-const-reversed/generated

mkdir -p build/project-external-declarations build/project-external-declarations-reversed
./build/elisa-c-transpiler \
    --compile-commands testdata/fixtures/project_external_declarations_compile_commands.json \
    --output-dir build/project-external-declarations
./build/elisa-c-transpiler \
    --compile-commands testdata/fixtures/project_external_declarations_compile_commands_reversed.json \
    --output-dir build/project-external-declarations-reversed
cmp build/project-external-declarations/elisa_project.elisa build/project-external-declarations-reversed/elisa_project.elisa
rg -q '^def elisa_nonnull\[T\]' build/project-external-declarations/elisa_project.elisa
! rg -q '^def elisa_nonnull_readonly\[T\]' build/project-external-declarations/elisa_project.elisa
! rg -q '^extern va_list' build/project-external-declarations/elisa_project.elisa
for external_module in build/project-external-declarations/*.elisa; do
    external_name=${external_module##*/}
    cmp "$external_module" "build/project-external-declarations-reversed/$external_name"
done
clang -std=c11 \
    testdata/fixtures/project_external_declarations/alpha.c \
    testdata/fixtures/project_external_declarations/beta.c \
    testdata/fixtures/project_external_declarations/implementation.c \
    testdata/fixtures/project_external_declarations/main.c \
    -o build/project-external-declarations/native
./build/project-external-declarations/native
ELISA_STAGE1_MAX_RSS_KB=4194304 bash "$stage1_worktree/scripts/elisac_stage1.sh" \
    -emit exe -O0 -o build/project-external-declarations/generated \
    "$root_dir/build/project-external-declarations/elisa_project.elisa"
./build/project-external-declarations/generated
ELISA_STAGE1_MAX_RSS_KB=4194304 bash "$stage1_worktree/scripts/elisac_stage1.sh" \
    -emit exe -O0 -o build/project-external-declarations-reversed/generated \
    "$root_dir/build/project-external-declarations-reversed/elisa_project.elisa"
./build/project-external-declarations-reversed/generated

mkdir -p build/project-external-objects build/project-external-objects-reversed
./build/elisa-c-transpiler \
    --compile-commands testdata/fixtures/project_external_objects_compile_commands.json \
    --output-dir build/project-external-objects
./build/elisa-c-transpiler \
    --compile-commands testdata/fixtures/project_external_objects_compile_commands_reversed.json \
    --output-dir build/project-external-objects-reversed
cmp build/project-external-objects/elisa_project.elisa build/project-external-objects-reversed/elisa_project.elisa
clang -std=c11 \
    testdata/fixtures/project_external_objects/alpha.c \
    testdata/fixtures/project_external_objects/beta.c \
    testdata/fixtures/project_external_objects/implementation.c \
    testdata/fixtures/project_external_objects/main.c \
    -o build/project-external-objects/native
./build/project-external-objects/native
ELISA_STAGE1_MAX_RSS_KB=4194304 bash "$stage1_worktree/scripts/elisac_stage1.sh" \
    -emit exe -O0 -o build/project-external-objects/generated \
    "$root_dir/build/project-external-objects/elisa_project.elisa"
./build/project-external-objects/generated
ELISA_STAGE1_MAX_RSS_KB=4194304 bash "$stage1_worktree/scripts/elisac_stage1.sh" \
    -emit exe -O0 -o build/project-external-objects-reversed/generated \
    "$root_dir/build/project-external-objects-reversed/elisa_project.elisa"
./build/project-external-objects-reversed/generated

mkdir -p build/project-extern-initializer build/project-extern-initializer-reversed
./build/elisa-c-transpiler \
    --compile-commands testdata/fixtures/project_extern_initializer_compile_commands.json \
    --output-dir build/project-extern-initializer
./build/elisa-c-transpiler \
    --compile-commands testdata/fixtures/project_extern_initializer_compile_commands_reversed.json \
    --output-dir build/project-extern-initializer-reversed
cmp build/project-extern-initializer/elisa_project.elisa build/project-extern-initializer-reversed/elisa_project.elisa
rg -q '^global mutable initialized_project_value: i32 = 37$' build/project-extern-initializer/definition.elisa
! rg -q 'initialized_project_value <- 37' build/project-extern-initializer/definition.elisa
clang -std=c11 -Wno-extern-initializer \
    testdata/fixtures/project_extern_initializer/definition.c \
    testdata/fixtures/project_extern_initializer/main.c \
    -o build/project-extern-initializer/native
./build/project-extern-initializer/native
ELISA_STAGE1_MAX_RSS_KB=4194304 bash "$stage1_worktree/scripts/elisac_stage1.sh" \
    -emit exe -O0 -o build/project-extern-initializer/generated \
    "$root_dir/build/project-extern-initializer/elisa_project.elisa"
./build/project-extern-initializer/generated
ELISA_STAGE1_MAX_RSS_KB=4194304 bash "$stage1_worktree/scripts/elisac_stage1.sh" \
    -emit exe -O0 -o build/project-extern-initializer-reversed/generated \
    "$root_dir/build/project-extern-initializer-reversed/elisa_project.elisa"
./build/project-extern-initializer-reversed/generated

mkdir -p build/project-duplicate-extern-definition build/project-duplicate-extern-definition-reversed
set +e
./build/elisa-c-transpiler \
    --compile-commands testdata/fixtures/project_duplicate_extern_definition_compile_commands.json \
    --output-dir build/project-duplicate-extern-definition \
    > build/project-duplicate-extern-definition.stdout 2> build/project-duplicate-extern-definition.stderr
duplicate_extern_definition_rc=$?
./build/elisa-c-transpiler \
    --compile-commands testdata/fixtures/project_duplicate_extern_definition_compile_commands_reversed.json \
    --output-dir build/project-duplicate-extern-definition-reversed \
    > build/project-duplicate-extern-definition-reversed.stdout 2> build/project-duplicate-extern-definition-reversed.stderr
duplicate_extern_definition_reversed_rc=$?
set -e
[ "$duplicate_extern_definition_rc" -eq 1 ]
[ "$duplicate_extern_definition_reversed_rc" -eq 1 ]
[ ! -s build/project-duplicate-extern-definition.stdout ]
[ ! -s build/project-duplicate-extern-definition-reversed.stdout ]
rg -q 'duplicate-external-object-definition' build/project-duplicate-extern-definition.stderr
rg -q 'duplicate-external-object-definition' build/project-duplicate-extern-definition-reversed.stderr
[ ! -e build/project-duplicate-extern-definition/elisa_project.elisa ]
[ ! -e build/project-duplicate-extern-definition-reversed/elisa_project.elisa ]

mkdir -p build/project-external-object-conflict build/project-external-object-conflict-reversed
set +e
./build/elisa-c-transpiler \
    --compile-commands testdata/fixtures/project_external_object_conflict_compile_commands.json \
    --output-dir build/project-external-object-conflict \
    > build/project-external-object-conflict.stdout 2> build/project-external-object-conflict.stderr
external_object_conflict_rc=$?
./build/elisa-c-transpiler \
    --compile-commands testdata/fixtures/project_external_object_conflict_compile_commands_reversed.json \
    --output-dir build/project-external-object-conflict-reversed \
    > build/project-external-object-conflict-reversed.stdout 2> build/project-external-object-conflict-reversed.stderr
external_object_conflict_reversed_rc=$?
set -e
[ "$external_object_conflict_rc" -eq 1 ]
[ "$external_object_conflict_reversed_rc" -eq 1 ]
[ ! -s build/project-external-object-conflict.stdout ]
[ ! -s build/project-external-object-conflict-reversed.stdout ]
rg -q 'incompatible-external-object-declaration' build/project-external-object-conflict.stderr
rg -q 'incompatible-external-object-declaration' build/project-external-object-conflict-reversed.stderr
[ ! -e build/project-external-object-conflict/elisa_project.elisa ]
[ ! -e build/project-external-object-conflict-reversed/elisa_project.elisa ]

mkdir -p build/project-external-object-array-conflict build/project-external-object-array-conflict-reversed
set +e
./build/elisa-c-transpiler \
    --compile-commands testdata/fixtures/project_external_object_array_conflict_compile_commands.json \
    --output-dir build/project-external-object-array-conflict \
    > build/project-external-object-array-conflict.stdout 2> build/project-external-object-array-conflict.stderr
external_object_array_conflict_rc=$?
./build/elisa-c-transpiler \
    --compile-commands testdata/fixtures/project_external_object_array_conflict_compile_commands_reversed.json \
    --output-dir build/project-external-object-array-conflict-reversed \
    > build/project-external-object-array-conflict-reversed.stdout 2> build/project-external-object-array-conflict-reversed.stderr
external_object_array_conflict_reversed_rc=$?
set -e
[ "$external_object_array_conflict_rc" -eq 1 ]
[ "$external_object_array_conflict_reversed_rc" -eq 1 ]
[ ! -s build/project-external-object-array-conflict.stdout ]
[ ! -s build/project-external-object-array-conflict-reversed.stdout ]
rg -q 'incompatible-external-object-declaration' build/project-external-object-array-conflict.stderr
rg -q 'incompatible-external-object-declaration' build/project-external-object-array-conflict-reversed.stderr
[ ! -e build/project-external-object-array-conflict/elisa_project.elisa ]
[ ! -e build/project-external-object-array-conflict-reversed/elisa_project.elisa ]

mkdir -p build/project-external-conflict build/project-external-conflict-reversed
set +e
./build/elisa-c-transpiler \
    --compile-commands testdata/fixtures/project_external_conflict_compile_commands.json \
    --output-dir build/project-external-conflict \
    > build/project-external-conflict.stdout 2> build/project-external-conflict.stderr
external_conflict_rc=$?
./build/elisa-c-transpiler \
    --compile-commands testdata/fixtures/project_external_conflict_compile_commands_reversed.json \
    --output-dir build/project-external-conflict-reversed \
    > build/project-external-conflict-reversed.stdout 2> build/project-external-conflict-reversed.stderr
external_conflict_reversed_rc=$?
set -e
[ "$external_conflict_rc" -eq 1 ]
[ "$external_conflict_reversed_rc" -eq 1 ]
[ ! -s build/project-external-conflict.stdout ]
[ ! -s build/project-external-conflict-reversed.stdout ]
rg -q 'incompatible-external-function-declaration' build/project-external-conflict.stderr
rg -q 'incompatible-external-function-declaration' build/project-external-conflict-reversed.stderr
[ ! -e build/project-external-conflict/elisa_project.elisa ]
[ ! -e build/project-external-conflict-reversed/elisa_project.elisa ]

mkdir -p build/project-external-pointee-conflict build/project-external-pointee-conflict-reversed
set +e
./build/elisa-c-transpiler \
    --compile-commands testdata/fixtures/project_external_declaration_qualifiers_compile_commands.json \
    --output-dir build/project-external-pointee-conflict \
    > build/project-external-pointee-conflict.stdout 2> build/project-external-pointee-conflict.stderr
external_pointee_conflict_rc=$?
./build/elisa-c-transpiler \
    --compile-commands testdata/fixtures/project_external_declaration_qualifiers_compile_commands_reversed.json \
    --output-dir build/project-external-pointee-conflict-reversed \
    > build/project-external-pointee-conflict-reversed.stdout 2> build/project-external-pointee-conflict-reversed.stderr
external_pointee_conflict_reversed_rc=$?
set -e
[ "$external_pointee_conflict_rc" -eq 1 ]
[ "$external_pointee_conflict_reversed_rc" -eq 1 ]
[ ! -s build/project-external-pointee-conflict.stdout ]
[ ! -s build/project-external-pointee-conflict-reversed.stdout ]
rg -q 'incompatible-external-function-declaration' build/project-external-pointee-conflict.stderr
rg -q 'incompatible-external-function-declaration' build/project-external-pointee-conflict-reversed.stderr
[ ! -e build/project-external-pointee-conflict/elisa_project.elisa ]
[ ! -e build/project-external-pointee-conflict-reversed/elisa_project.elisa ]

set +e
./build/elisa-c-transpiler \
    --output-dir build/project-duplicate-identity-guard \
    testdata/fixtures/project_identity/a/part.c \
    testdata/fixtures/project_identity/a/../a/part.c \
    > build/project-duplicate-identity.stdout \
    2> build/project-duplicate-identity.stderr
duplicate_identity_rc=$?
set -e
[ "$duplicate_identity_rc" -eq 1 ]
[ ! -s build/project-duplicate-identity.stdout ]
rg -q 'indistinguishable stable output identities' build/project-duplicate-identity.stderr
[ ! -e build/project-duplicate-identity-guard/elisa_project.elisa ]

mkdir -p build/project-global-init
./build/elisa-c-transpiler --compile-commands testdata/fixtures/project_global_init_compile_commands.json \
    --output-dir build/project-global-init
rg -q '^def elisa_init_project\(\)' build/project-global-init/elisa_project.elisa
rg -q 'elisa_init_project\(\)' build/project-global-init/project_global_init_main.elisa
rg -q 'elisa_init_project_global_init_main\(\)' build/project-global-init/elisa_project.elisa
rg -q 'elisa_init_project_global_init\(\)' build/project-global-init/elisa_project.elisa
ELISA_STAGE1_MAX_RSS_KB=4194304 bash "$stage1_worktree/scripts/elisac_stage1.sh" \
    -emit exe -O0 -o build/project-global-init/project \
    "$root_dir/build/project-global-init/elisa_project.elisa"
./build/project-global-init/project

mkdir -p build/project-forward
./build/elisa-c-transpiler --compile-commands testdata/fixtures/forward_compile_commands.json \
    --output-dir build/project-forward
rg -q 'include "forward_decl_main.elisa"' build/project-forward/elisa_project.elisa
rg -q 'include "forward_decl_impl.elisa"' build/project-forward/elisa_project.elisa
rg -q '^extern project_forward_value\(value: i32\) -> i32' build/project-forward/forward_decl_main.elisa
rg -q '^@link_name\("__elisa_c_impl_project_forward_value__1"\)$' build/project-forward/forward_decl_impl.elisa
rg -q '^def project_forward_value\(value: i32\) -> i32' build/project-forward/forward_decl_impl.elisa
rg -q '^export fn __c_abi_project_forward_value__1' build/project-forward/forward_decl_impl.elisa
ELISA_STAGE1_MAX_RSS_KB=4194304 bash "$stage1_worktree/scripts/elisac_stage1.sh" \
    -emit exe -O0 -o build/project-forward/project \
    "$root_dir/build/project-forward/elisa_project.elisa"
set +e
./build/project-forward/project
forward_project_generated_rc=$?
set -e
[ "$forward_project_generated_rc" -eq 0 ]

mkdir -p build/project-cpp-abi
./build/elisa-c-transpiler --compile-commands testdata/fixtures/cpp_abi_compile_commands.json \
    --output-dir build/project-cpp-abi
rg -q '^@link_name\("_Z7cpp_addii"\)$' build/project-cpp-abi/cpp_abi.elisa
rg -q '^export fn __c_abi_cpp_add__2' build/project-cpp-abi/cpp_abi.elisa
ELISA_STAGE1_MAX_RSS_KB=4194304 bash "$stage1_worktree/scripts/elisac_stage1.sh" \
    -emit exe -O0 -o build/project-cpp-abi/project \
    "$root_dir/build/project-cpp-abi/elisa_project.elisa"
set +e
./build/project-cpp-abi/project
cpp_abi_generated_rc=$?
set -e
[ "$cpp_abi_generated_rc" -eq 42 ]

mkdir -p build/project-language-override
./build/elisa-c-transpiler \
    --compile-commands testdata/fixtures/language_override_compile_commands.json \
    --output-dir build/project-language-override
rg -q '^def main\(\) -> i32' build/project-language-override/language_override.elisa
clang -x c++ -std=gnu++11 -DTRANSLATOR_LANGUAGE_MARKER=1 \
    testdata/fixtures/language_override.c -o build/project-language-override/native
ELISA_STAGE1_MAX_RSS_KB=4194304 bash "$stage1_worktree/scripts/elisac_stage1.sh" \
    -emit exe -O0 -o build/project-language-override/project \
    "$root_dir/build/project-language-override/elisa_project.elisa"
set +e
./build/project-language-override/native
language_override_native_rc=$?
./build/project-language-override/project
language_override_generated_rc=$?
set -e
[ "$language_override_native_rc" -eq 42 ] && [ "$language_override_generated_rc" -eq 42 ]
