#!/bin/sh
set -eu

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    echo "usage: $0 SOURCE [OUTPUT]" >&2
    exit 2
fi

source_path=$1
output_path=${2:-build/quality.generated.elisa}
mkdir -p "$(dirname -- "$output_path")"
quality_tmp_dir=$(mktemp -d "${TMPDIR:-/tmp}/elisa-quality.XXXXXX")
trap 'rm -rf "$quality_tmp_dir"' EXIT HUP INT TERM
quality_ir_path=$quality_tmp_dir/typed-ir.dump
if ! ./build/elisa-c-transpiler --dump-typed-ir --explain-rewrites \
    "$source_path" > "$output_path" 2> "$quality_ir_path"; then
    cat "$quality_ir_path" >&2
    exit 1
fi

counts_line=$(rg '^counts ' "$quality_ir_path" | head -1 || true)
ir_count() {
    field=$1
    value=$(printf '%s\n' "$counts_line" | sed -n "s/.* ${field}=\\([0-9][0-9]*\\).*/\\1/p")
    printf '%s\n' "${value:-0}"
}

rewrite_count() {
    field=$1
    value=$(sed -n "s/.* ${field}=\\([0-9][0-9]*\\).*/\\1/p" "$quality_ir_path" | tail -1)
    printf '%s\n' "${value:-0}"
}

count_matches() {
    pattern=$1
    rg -o "$pattern" "$output_path" 2>/dev/null | wc -l | tr -d ' '
}

cast_count=$(count_matches '\.cast\[')
nonnull_count=$(count_matches 'elisa_nonnull(_readonly)?\(')
readonly_nonnull_count=$(count_matches 'elisa_nonnull_readonly\(')
unsafe_count=$(count_matches 'trusted Unsafe\.StaleRef|Unsafe\.PointerCast')
synthetic_count=$(count_matches 'control_state|pointer_slot_|switch_done_')
invalid_count=$(count_matches '<invalid-ir>|<invalid-type>')
function_count=$(count_matches '^def ')
external_count=$(count_matches '^extern ')
fallback_name_count=$(count_matches '__c_(param|nonnull|ext|global)_')
line_count=$(wc -l < "$output_path" | tr -d ' ')
max_line_length=$(awk 'length > longest { longest = length } END { print longest + 0 }' "$output_path")
ir_expr_count=$(ir_count exprs)
ir_statement_count=$(ir_count stmts)
ir_switch_case_count=$(ir_count switch_cases)
ir_function_count=$(ir_count functions)
ir_global_count=$(ir_count globals)
ir_goto_count=$(rg -c '^stmt .* kind=Goto ' "$quality_ir_path" || true)
ir_label_count=$(rg -c '^stmt .* kind=Label ' "$quality_ir_path" || true)
rewrite_redundant_casts=$(rewrite_count redundant_casts)
rewrite_identity_binaries=$(rewrite_count identity_binaries)
rewrite_integer_folds=$(rewrite_count integer_folds)
rewrite_constant_conditions=$(rewrite_count constant_conditions)
rewrite_boolean_predicates=$(rewrite_count boolean_predicates)
rewrite_conditional_prunes=$(rewrite_count conditional_prunes)

printf 'source: %s\n' "$source_path"
printf 'output: %s\n' "$output_path"
printf 'lines: %s\n' "$line_count"
printf 'functions: %s\n' "$function_count"
printf 'externals: %s\n' "$external_count"
printf 'casts: %s\n' "$cast_count"
printf 'nonnull_assertions: %s\n' "$nonnull_count"
printf 'readonly_nonnull_assertions: %s\n' "$readonly_nonnull_count"
printf 'unsafe_markers: %s\n' "$unsafe_count"
printf 'synthetic_control_names: %s\n' "$synthetic_count"
printf 'fallback_name_markers: %s\n' "$fallback_name_count"
printf 'max_line_length: %s\n' "$max_line_length"
printf 'invalid_ir_markers: %s\n' "$invalid_count"
printf 'ir_exprs: %s\n' "$ir_expr_count"
printf 'ir_statements: %s\n' "$ir_statement_count"
printf 'ir_switch_cases: %s\n' "$ir_switch_case_count"
printf 'ir_functions: %s\n' "$ir_function_count"
printf 'ir_globals: %s\n' "$ir_global_count"
printf 'ir_gotos: %s\n' "${ir_goto_count:-0}"
printf 'ir_labels: %s\n' "${ir_label_count:-0}"
printf 'rewrite_redundant_casts: %s\n' "$rewrite_redundant_casts"
printf 'rewrite_identity_binaries: %s\n' "$rewrite_identity_binaries"
printf 'rewrite_integer_folds: %s\n' "$rewrite_integer_folds"
printf 'rewrite_constant_conditions: %s\n' "$rewrite_constant_conditions"
printf 'rewrite_boolean_predicates: %s\n' "$rewrite_boolean_predicates"
printf 'rewrite_conditional_prunes: %s\n' "$rewrite_conditional_prunes"
