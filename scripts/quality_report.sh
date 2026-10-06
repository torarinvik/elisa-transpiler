#!/bin/sh
set -eu

if [ "$#" -lt 1 ] || [ "$#" -gt 4 ]; then
    echo "usage: $0 SOURCE [OUTPUT] [ACCEPTANCE_SUMMARY_JSON [FIXTURE_MANIFEST_JSON]]" >&2
    exit 2
fi

source_path=$1
output_path=${2:-build/quality.generated.elisa}
coverage_summary=${3:-}
coverage_manifest=${4:-}
translator_bin=${ELISA_TRANSLATOR_BIN:-./build/elisa-c-transpiler}
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_dir=$(CDPATH= cd -- "$script_dir/.." && pwd)
source_report_path=$(python3 "$script_dir/quality_provenance.py" --json-string "$source_path")
output_report_path=$(python3 "$script_dir/quality_provenance.py" --json-string "$output_path")
compiler_manifest=${ELISA_COMPILER_COMPATIBILITY_MANIFEST:-$repo_dir/docs/compiler_compatibility.json}
case "$translator_bin" in
    */*) ;;
    *)
        resolved_translator=$(command -v "$translator_bin" || true)
        if [ -z "$resolved_translator" ]; then
            printf 'quality report: translator executable not found: %s\n' "$translator_bin" >&2
            exit 2
        fi
        translator_bin=$resolved_translator
        ;;
esac
if [ ! -f "$translator_bin" ] || [ ! -x "$translator_bin" ]; then
    printf 'quality report: translator is not an executable file: %s\n' "$translator_bin" >&2
    exit 2
fi
if ! python3 "$script_dir/quality_provenance.py" --check-output \
    "$output_path" "$source_path" "$translator_bin" "$compiler_manifest" \
    "$coverage_summary" "$coverage_manifest"; then
    exit 2
fi
mkdir -p "$(dirname -- "$output_path")"
quality_tmp_dir=$(mktemp -d "${TMPDIR:-/tmp}/elisa-quality.XXXXXX")
trap 'rm -rf "$quality_tmp_dir"' EXIT HUP INT TERM
quality_ir_path=$quality_tmp_dir/typed-ir.dump
source_sha256_before=$(python3 "$script_dir/quality_provenance.py" --hash-file "$source_path")
translator_sha256_before=$(python3 "$script_dir/quality_provenance.py" --hash-file "$translator_bin")
if ! "$translator_bin" --dump-typed-ir --explain-rewrites \
    "$source_path" > "$output_path" 2> "$quality_ir_path"; then
    cat "$quality_ir_path" >&2
    exit 1
fi

ir_header_count=$(rg -c '^typed-ir-v[0-9]+$' "$quality_ir_path" 2>/dev/null || true)
if [ "$ir_header_count" != 1 ]; then
    printf 'quality report: expected exactly one typed-IR version header, found %s\n' \
        "${ir_header_count:-0}" >&2
    exit 2
fi
ir_version=$(rg -m 1 '^typed-ir-v[0-9]+$' "$quality_ir_path" || true)
if [ "$ir_version" != "typed-ir-v16" ]; then
    printf 'quality report: unsupported typed-IR dump version %s (expected typed-ir-v16)\n' \
        "${ir_version:-<missing>}" >&2
    exit 2
fi

counts_record_count=$(rg -c '^counts ' "$quality_ir_path" 2>/dev/null || true)
if [ "$counts_record_count" != 1 ]; then
    printf 'quality report: expected exactly one typed-IR counts record, found %s\n' \
        "${counts_record_count:-0}" >&2
    exit 2
fi

counts_line=$(rg '^counts ' "$quality_ir_path" | head -1 || true)
ir_count() {
    field=$1
    value=$(printf '%s\n' "$counts_line" | sed -n "s/.* ${field}=\\([0-9][0-9]*\\).*/\\1/p")
    printf '%s\n' "${value:-0}"
}

for required_ir_count in exprs stmts switch_cases functions globals; do
    count_field_occurrences=$(printf '%s\n' "$counts_line" \
        | rg -o "(^| )${required_ir_count}=[^ ]+" | wc -l | tr -d ' ')
    if [ "$count_field_occurrences" != 1 ]; then
        printf 'quality report: typed-IR v16 counts record has %s %s fields; expected exactly one\n' \
            "${count_field_occurrences:-0}" "$required_ir_count" >&2
        exit 2
    fi
    count_value=$(printf '%s\n' "$counts_line" \
        | sed -n "s/.* ${required_ir_count}=\\([0-9][0-9]*\\).*/\\1/p")
    case "$count_value" in
        ''|*[!0-9]*)
            printf 'quality report: typed-IR v16 counts record has no unique non-negative %s field\n' \
                "$required_ir_count" >&2
            exit 2
            ;;
    esac
done

expected_ir_exprs=$(ir_count exprs)
expected_ir_statements=$(ir_count stmts)
if ! awk -v expected_exprs="$expected_ir_exprs" -v expected_statements="$expected_ir_statements" '
    $1 == "expr" {
        if ($2 !~ /^[0-9]+$/ || $2 != expr_records || $3 !~ /^kind=/) invalid = 1
        expr_records++
    }
    $1 == "stmt" {
        if ($2 !~ /^[0-9]+$/ || $2 != stmt_records || $3 !~ /^kind=/) invalid = 1
        stmt_records++
    }
    END {
        if (invalid || expr_records != expected_exprs || stmt_records != expected_statements) exit 1
    }
' "$quality_ir_path"; then
    printf 'quality report: typed-IR node records are malformed, unordered, or incomplete (expected %s expressions and %s statements)\n' \
        "$expected_ir_exprs" "$expected_ir_statements" >&2
    exit 2
fi

ir_function_metrics=$(python3 scripts/quality_ir_metrics.py "$quality_ir_path")
ir_provenance=$(python3 "$script_dir/quality_provenance.py" \
    "$source_path" "$output_path" "$translator_bin" "$compiler_manifest" \
    "$source_sha256_before" "$translator_sha256_before")

ir_expr_kind_count() {
    kind=$1
    value=$(rg -c "^expr .* kind=${kind} " "$quality_ir_path" 2>/dev/null || true)
    printf '%s\n' "${value:-0}"
}

ir_stmt_kind_count() {
    kind=$1
    value=$(rg -c "^stmt .* kind=${kind} " "$quality_ir_path" 2>/dev/null || true)
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

per_unit_rate() {
    numerator=$1
    denominator=$2
    scale=$3
    awk -v numerator="$numerator" -v denominator="$denominator" -v scale="$scale" \
        'BEGIN { if (denominator > 0) printf "%.3f", numerator * scale / denominator; else printf "n/a" }'
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
ir_cast_node_count=$(ir_expr_kind_count Cast)
ir_sequence_node_count=$(ir_expr_kind_count Sequence)
ir_if_node_count=$(ir_stmt_kind_count If)
ir_for_node_count=$(ir_stmt_kind_count For)
ir_while_node_count=$(ir_stmt_kind_count While)
ir_do_while_node_count=$(ir_stmt_kind_count DoWhile)
ir_switch_node_count=$(ir_stmt_kind_count Switch)
ir_loop_node_count=$((${ir_for_node_count:-0} + ${ir_while_node_count:-0} + ${ir_do_while_node_count:-0}))
ir_control_node_count=$((${ir_if_node_count:-0} + ${ir_loop_node_count:-0} + ${ir_switch_node_count:-0}))
ir_goto_count=$(rg -c '^stmt .* kind=Goto ' "$quality_ir_path" || true)
ir_label_count=$(rg -c '^stmt .* kind=Label ' "$quality_ir_path" || true)
rewrite_redundant_casts=$(rewrite_count redundant_casts)
rewrite_identity_binaries=$(rewrite_count identity_binaries)
rewrite_integer_folds=$(rewrite_count integer_folds)
rewrite_constant_conditions=$(rewrite_count constant_conditions)
rewrite_boolean_predicates=$(rewrite_count boolean_predicates)
rewrite_conditional_prunes=$(rewrite_count conditional_prunes)
casts_per_1000_ir_exprs=$(per_unit_rate "$cast_count" "$ir_expr_count" 1000)
nonnull_per_1000_ir_exprs=$(per_unit_rate "$nonnull_count" "$ir_expr_count" 1000)
unsafe_per_100_ir_statements=$(per_unit_rate "$unsafe_count" "$ir_statement_count" 100)
synthetic_names_per_function=$(per_unit_rate "$synthetic_count" "$ir_function_count" 1)
fallback_names_per_function=$(per_unit_rate "$fallback_name_count" "$ir_function_count" 1)
lines_per_ir_function=$(per_unit_rate "$line_count" "$ir_function_count" 1)
dispatch_node_count=$((${ir_goto_count:-0} + ${ir_label_count:-0}))
dispatch_nodes_per_100_functions=$(per_unit_rate "$dispatch_node_count" "$ir_function_count" 100)
ir_cast_nodes_per_1000_exprs=$(per_unit_rate "$ir_cast_node_count" "$ir_expr_count" 1000)
ir_sequence_nodes_per_1000_exprs=$(per_unit_rate "$ir_sequence_node_count" "$ir_expr_count" 1000)
ir_control_nodes_per_function=$(per_unit_rate "$ir_control_node_count" "$ir_function_count" 1)
ir_loop_nodes_per_function=$(per_unit_rate "$ir_loop_node_count" "$ir_function_count" 1)

printf 'source: %s\n' "$source_report_path"
printf 'output: %s\n' "$output_report_path"
printf '%s\n' "$ir_provenance"
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
printf 'ir_cast_nodes: %s\n' "$ir_cast_node_count"
printf 'ir_sequence_nodes: %s\n' "$ir_sequence_node_count"
printf 'ir_if_nodes: %s\n' "$ir_if_node_count"
printf 'ir_for_nodes: %s\n' "$ir_for_node_count"
printf 'ir_while_nodes: %s\n' "$ir_while_node_count"
printf 'ir_do_while_nodes: %s\n' "$ir_do_while_node_count"
printf 'ir_switch_nodes: %s\n' "$ir_switch_node_count"
printf 'ir_loop_nodes: %s\n' "$ir_loop_node_count"
printf 'ir_control_nodes: %s\n' "$ir_control_node_count"
printf 'ir_gotos: %s\n' "${ir_goto_count:-0}"
printf 'ir_labels: %s\n' "${ir_label_count:-0}"
printf '%s\n' "$ir_function_metrics" | sed -n '/^ir_rewrite_/p'
printf 'rewrite_redundant_casts: %s\n' "$rewrite_redundant_casts"
printf 'rewrite_identity_binaries: %s\n' "$rewrite_identity_binaries"
printf 'rewrite_integer_folds: %s\n' "$rewrite_integer_folds"
printf 'rewrite_constant_conditions: %s\n' "$rewrite_constant_conditions"
printf 'rewrite_boolean_predicates: %s\n' "$rewrite_boolean_predicates"
printf 'rewrite_conditional_prunes: %s\n' "$rewrite_conditional_prunes"
printf 'rendered_text_pressure_metrics: heuristic (string literals may contribute)\n'
printf 'rendered_casts_per_1000_ir_exprs: %s\n' "$casts_per_1000_ir_exprs"
printf 'rendered_nonnull_per_1000_ir_exprs: %s\n' "$nonnull_per_1000_ir_exprs"
printf 'rendered_unsafe_markers_per_100_ir_statements: %s\n' "$unsafe_per_100_ir_statements"
printf 'rendered_synthetic_names_per_ir_function: %s\n' "$synthetic_names_per_function"
printf 'rendered_fallback_names_per_ir_function: %s\n' "$fallback_names_per_function"
printf 'rendered_lines_per_ir_function: %s\n' "$lines_per_ir_function"
printf 'ir_goto_label_nodes_per_100_ir_functions: %s\n' "$dispatch_nodes_per_100_functions"
printf 'ir_cast_nodes_per_1000_ir_exprs: %s\n' "$ir_cast_nodes_per_1000_exprs"
printf 'ir_sequence_nodes_per_1000_ir_exprs: %s\n' "$ir_sequence_nodes_per_1000_exprs"
printf 'ir_control_nodes_per_function: %s\n' "$ir_control_nodes_per_function"
printf 'ir_loop_nodes_per_function: %s\n' "$ir_loop_nodes_per_function"
printf '%s\n' "$ir_function_metrics" | sed -n '/^ir_functions_with_bodies:/,$p'
if [ -n "$coverage_summary" ]; then
    if [ -n "$coverage_manifest" ]; then
        python3 scripts/quality_coverage.py "$coverage_summary" "$coverage_manifest"
    else
        python3 scripts/quality_coverage.py "$coverage_summary"
    fi
else
    printf 'acceptance_coverage: not_supplied\n'
fi
