#!/bin/sh
set -eu

root_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
test_dir=$(mktemp -d "${TMPDIR:-/tmp}/elisa-quality-report-test.XXXXXX")
trap 'rm -rf "$test_dir"' EXIT HUP INT TERM
fake_translator="$test_dir/fake-translator"
source_file="$test_dir/input.c"
output_file="$test_dir/output.elisa"
report_file="$test_dir/report.txt"
coverage_file="$test_dir/coverage.json"
coverage_manifest="$test_dir/acceptance_manifest.json"
compiler_manifest="$test_dir/compiler_compatibility.json"

printf 'int main(void) { return 0; }\n' > "$source_file"
printf '%s\n' \
    '#!/bin/sh' \
    'printf "def main() -> i32:\\n    a <- value.cast[i32]()\\n    b <- other.cast[i32]()\\n    return 0\\n\\n"' \
    'printf "expr 99 kind=Cast stmt 99 kind=If .cast[i32]()\\n"' \
    'if [ "${QUALITY_BAD_IR_HEADER:-0}" = 1 ]; then printf "typed-ir-v99\\n" >&2; exit 0; fi' \
    'printf "rewrite-event source=/tmp/source dir/input.c range-start=1 range-end=2 expression=0 rule=constant-condition decision=applied proof=target-abi-integer-constant-condition\\n" >&2' \
    'printf "typed-ir-v16\\n" >&2' \
    'if [ "${QUALITY_MISSING_COUNTS:-0}" = 1 ]; then printf "expr 0 kind=Cast\\n" >&2; exit 0; fi' \
    'if [ "${QUALITY_MALFORMED_COUNTS:-0}" = 1 ]; then printf "counts exprs=ten stmts=4 switch_cases=0 functions=1 globals=0\\n" >&2; exit 0; fi' \
    'if [ "${QUALITY_DUPLICATE_COUNT:-0}" = 1 ]; then printf "counts exprs=10 exprs=11 stmts=4 switch_cases=0 functions=1 globals=0\\n" >&2; exit 0; fi' \
    'if [ "${QUALITY_TRUNCATED_IR:-0}" = 1 ]; then printf "counts exprs=2 expr_children=0 stmts=1 stmt_children=0 functions=0 params=0 externs=0 extern_params=0 extern_globals=0 records=0 record_layouts=0 fields=0 globals=0 enums=0 enum_consts=0 type_aliases=0 signatures=0 decl_infos=0 labels=0 switch_cases=0 mode=0 project_mode=false cpp_unordered_map=false\\nexpr 0 kind=Cast lhs=-1\\nstmt 0 kind=Expression expr=-1\\n" >&2; exit 0; fi' \
    'if [ "${QUALITY_EMPTY_IR:-0}" = 1 ]; then' \
    '    printf "counts exprs=0 stmts=0 switch_cases=0 functions=0 globals=0\\n" >&2' \
    'else' \
    '    printf "counts exprs=10 stmts=4 switch_cases=0 functions=1 globals=0 labels=1\\n" >&2' \
    '    printf "function 0 body=-1\\n" >&2' \
    '    printf "stmt 0 kind=Goto expr=-1 aux=0\\nstmt 1 kind=Label expr=3 aux=0 name=done\\nstmt 2 kind=If expr=7 aux=1 aux2=-1\\nstmt 3 kind=For expr=8 children_start=-1 aux=1 aux2=-1\\nexpr 0 kind=Cast lhs=3\\nexpr 1 kind=Cast lhs=4\\nexpr 2 kind=Sequence lhs=5 rhs=6\\nexpr 3 kind=Integer lhs=-1\\nexpr 4 kind=Integer lhs=-1\\nexpr 5 kind=Integer lhs=-1\\nexpr 6 kind=Integer lhs=-1\\nexpr 7 kind=Integer lhs=-1\\nexpr 8 kind=Integer lhs=-1\\nexpr 9 kind=Integer lhs=-1\\n" >&2' \
    'fi' \
    'printf "rewrite-stats redundant_casts=2 identity_binaries=0 integer_folds=0 constant_conditions=0 boolean_predicates=0 conditional_prunes=0\\n" >&2' \
    > "$fake_translator"
chmod +x "$fake_translator"
printf '%s\n' '{"selected_cases":["one","two"],"counts":{"passed":1,"failed":1},"results":[{"name":"one","status":"passed"},{"name":"two","status":"failed"}]}' > "$coverage_file"
printf '%s\n' '{"feature_families":{"one":["integer_semantics","pointers"],"two":["pointers"]}}' > "$coverage_manifest"
printf '%s\n' '{"schema":"elisa-transpiler-compiler-compatibility-v1","target":"test-target","compiler_pair":{"stage0":{"source_revision":"0000000000000000000000000000000000000000","source_worktree_clean":true,"source_freshness_verified":true,"executable":{"sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","artifact_source_revision":"0000000000000000000000000000000000000000"}},"stage1":{"source_revision":"1111111111111111111111111111111111111111","source_worktree_clean":false,"source_freshness_verified":false,"executable":{"sha256":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","artifact_source_revision":"1111111111111111111111111111111111111111"},"runtime":{"sha256":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","artifact_source_revision":"2222222222222222222222222222222222222222"}}},"translator_validation":{"status":"pending","current_translator_sources_verified":false,"compiler_products_current":false}}' > "$compiler_manifest"

hash_file() {
    python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())' "$1"
}

ELISA_TRANSLATOR_BIN="$fake_translator" \
ELISA_COMPILER_COMPATIBILITY_MANIFEST="$compiler_manifest" \
    sh "$root_dir/scripts/quality_report.sh" "$source_file" "$output_file" "$coverage_file" "$coverage_manifest" > "$report_file"
source_hash=$(hash_file "$source_file")
output_hash=$(hash_file "$output_file")
translator_hash=$(hash_file "$fake_translator")
compiler_manifest_hash=$(hash_file "$compiler_manifest")
rg -q '^provenance_schema: elisa-quality-provenance-v1$' "$report_file"
rg -Fq "source: \"$source_file\"" "$report_file"
rg -Fq "output: \"$output_file\"" "$report_file"
rg -q '^translation_mode: single-file$' "$report_file"
rg -q '^typed_ir_schema: typed-ir-v16$' "$report_file"
rg -q "^translator_invocation_path: .*fake-translator" "$report_file"
rg -q "^translator_resolved_path: .*fake-translator" "$report_file"
rg -q "^source_sha256: $source_hash$" "$report_file"
rg -q "^generated_elisa_sha256: $output_hash$" "$report_file"
rg -q "^translator_sha256: $translator_hash$" "$report_file"
rg -q '^compiler_manifest_status: valid$' "$report_file"
rg -q "^compiler_manifest_sha256: $compiler_manifest_hash$" "$report_file"
rg -q '^compiler_target: "test-target"$' "$report_file"
rg -q '^stage0_source_revision: "0000000000000000000000000000000000000000"$' "$report_file"
rg -q '^stage0_source_worktree_clean: true$' "$report_file"
rg -q '^stage0_executable_sha256: "a{64}"$' "$report_file"
rg -q '^stage0_products_fresh: true$' "$report_file"
rg -q '^stage1_source_worktree_clean: false$' "$report_file"
rg -q '^stage1_executable_sha256: "b{64}"$' "$report_file"
rg -q '^stage1_runtime_sha256: "c{64}"$' "$report_file"
rg -q '^stage1_products_fresh: false$' "$report_file"
rg -q '^translator_validation_status: "pending"$' "$report_file"
rg -q '^translator_sources_verified: false$' "$report_file"
rg -q '^compiler_products_current: false$' "$report_file"
rg -q '^rendered_casts_per_1000_ir_exprs: 300\.000$' "$report_file"
rg -q '^rendered_nonnull_per_1000_ir_exprs: 0\.000$' "$report_file"
rg -q '^rendered_unsafe_markers_per_100_ir_statements: 0\.000$' "$report_file"
rg -q '^rendered_synthetic_names_per_ir_function: 0\.000$' "$report_file"
rg -q '^ir_goto_label_nodes_per_100_ir_functions: 200\.000$' "$report_file"
rg -q '^ir_cast_nodes: 2$' "$report_file"
rg -q '^ir_sequence_nodes: 1$' "$report_file"
rg -q '^ir_control_nodes: 2$' "$report_file"
rg -q '^ir_loop_nodes: 1$' "$report_file"
rg -q '^ir_cast_nodes_per_1000_ir_exprs: 200\.000$' "$report_file"
rg -q '^ir_rewrite_events_total: 1$' "$report_file"
rg -q '^ir_rewrite_events_applied: 1$' "$report_file"
rg -q '^ir_rewrite_events_declined: 0$' "$report_file"
rg -q '^ir_rewrite_rule_constant-condition_applied: 1$' "$report_file"
rg -q '^ir_sequence_nodes_per_1000_ir_exprs: 100\.000$' "$report_file"
rg -q '^ir_control_nodes_per_function: 2\.000$' "$report_file"
rg -q '^ir_functions_with_bodies: 0$' "$report_file"
rg -q '^ir_reachable_goto_nodes_per_function_mean: n/a$' "$report_file"
rg -q '^ir_loop_switch_goto_candidate_state_label_targets: 0$' "$report_file"
rg -q '^ir_loop_switch_goto_candidate_state_label_targets_per_function_mean: n/a$' "$report_file"
rg -q '^ir_loop_switch_goto_candidate_state_label_targets_per_switch_mean: n/a$' "$report_file"
rg -q '^ir_reachable_label_nodes_per_function_mean: n/a$' "$report_file"
rg -q '^ir_functions_with_reachable_goto_or_label_fraction: n/a$' "$report_file"
rg -q '^ir_expr_nodes_per_function_mean: n/a$' "$report_file"
rg -q '^ir_declaration_nodes_per_function_mean: n/a$' "$report_file"
rg -q '^ir_declaration_nodes_per_function_max: n/a$' "$report_file"
rg -q '^ir_declaration_nodes_per_decision_unit_mean: n/a$' "$report_file"
rg -q '^ir_unreferenced_local_declarations_per_function_mean: n/a$' "$report_file"
rg -q '^ir_unreferenced_local_declarations_per_1000_declarations: n/a$' "$report_file"
rg -q '^ir_repeated_statement_shapes_per_function_mean: n/a$' "$report_file"
rg -q '^ir_duplicate_statement_shape_excess: 0$' "$report_file"
rg -q '^ir_duplicate_statement_excess_per_decision_unit_mean: n/a$' "$report_file"
rg -q '^ir_duplicate_statement_excess_per_1000_statements: n/a$' "$report_file"
rg -q '^rendered_text_pressure_metrics: heuristic' "$report_file"
rg -q '^acceptance_selected_cases: 2$' "$report_file"
rg -q '^acceptance_results_complete: true$' "$report_file"
rg -q '^acceptance_pass_fraction: 0\.5000$' "$report_file"
rg -q '^acceptance_unsupported: 0$' "$report_file"
rg -q '^acceptance_feature_families_reported: true$' "$report_file"
rg -q '^acceptance_feature_family\.pointers\.selected: 2$' "$report_file"
rg -q '^acceptance_feature_family\.pointers\.pass_fraction: 0\.5000$' "$report_file"
rg -q '^acceptance_feature_family\.integer_semantics\.pass_fraction: 1\.0000$' "$report_file"

source_hash_before_collision=$(hash_file "$source_file")
if ELISA_TRANSLATOR_BIN="$fake_translator" \
    ELISA_COMPILER_COMPATIBILITY_MANIFEST="$compiler_manifest" \
    sh "$root_dir/scripts/quality_report.sh" "$source_file" "$source_file" \
    > /dev/null 2> "$report_file"; then
    echo "quality report allowed its output to overwrite the source" >&2
    exit 1
fi
rg -q '^quality provenance: refusing to overwrite source, tool, manifest, or coverage input:' "$report_file"
[ "$(hash_file "$source_file")" = "$source_hash_before_collision" ]

for protected_path in "$fake_translator" "$compiler_manifest" "$coverage_file" "$coverage_manifest"; do
    protected_hash_before=$(hash_file "$protected_path")
    if ELISA_TRANSLATOR_BIN="$fake_translator" \
        ELISA_COMPILER_COMPATIBILITY_MANIFEST="$compiler_manifest" \
        sh "$root_dir/scripts/quality_report.sh" "$source_file" "$protected_path" \
        "$coverage_file" "$coverage_manifest" \
        > /dev/null 2> "$report_file"; then
        echo "quality report allowed output to overwrite protected input: $protected_path" >&2
        exit 1
    fi
    rg -q '^quality provenance: refusing to overwrite source, tool, manifest, or coverage input:' "$report_file"
    [ "$(hash_file "$protected_path")" = "$protected_hash_before" ]
done

source_alias="$test_dir/source-alias.c"
ln -s "$source_file" "$source_alias"
if ELISA_TRANSLATOR_BIN="$fake_translator" \
    ELISA_COMPILER_COMPATIBILITY_MANIFEST="$compiler_manifest" \
    sh "$root_dir/scripts/quality_report.sh" "$source_file" "$source_alias" \
    > /dev/null 2> "$report_file"; then
    echo "quality report allowed a symlink output to overwrite the source" >&2
    exit 1
fi
rg -q '^quality provenance: refusing to overwrite source, tool, manifest, or coverage input:' "$report_file"
[ "$(hash_file "$source_file")" = "$source_hash_before_collision" ]

QUALITY_EMPTY_IR=1 ELISA_TRANSLATOR_BIN="$fake_translator" \
ELISA_COMPILER_COMPATIBILITY_MANIFEST="$compiler_manifest" \
    sh "$root_dir/scripts/quality_report.sh" "$source_file" "$output_file" > "$report_file"
rg -q '^rendered_casts_per_1000_ir_exprs: n/a$' "$report_file"
rg -q '^rendered_lines_per_ir_function: n/a$' "$report_file"
rg -q '^ir_goto_label_nodes_per_100_ir_functions: n/a$' "$report_file"
rg -q '^ir_cast_nodes_per_1000_ir_exprs: n/a$' "$report_file"
rg -q '^ir_control_nodes_per_function: n/a$' "$report_file"
rg -q '^ir_declaration_nodes_per_decision_unit_mean: n/a$' "$report_file"
rg -q '^ir_unreferenced_local_declarations_per_function_mean: n/a$' "$report_file"
rg -q '^ir_unreferenced_local_declarations_per_1000_declarations: n/a$' "$report_file"
rg -q '^ir_repeated_statement_shapes_per_function_mean: n/a$' "$report_file"
rg -q '^ir_duplicate_statement_shape_excess: 0$' "$report_file"
rg -q '^ir_duplicate_statement_excess_per_1000_statements: n/a$' "$report_file"
rg -q '^ir_functions_with_bodies: 0$' "$report_file"
rg -q '^ir_reachable_goto_nodes_per_function_mean: n/a$' "$report_file"
rg -q '^ir_reachable_label_nodes_per_function_mean: n/a$' "$report_file"

if QUALITY_BAD_IR_HEADER=1 ELISA_TRANSLATOR_BIN="$fake_translator" \
    ELISA_COMPILER_COMPATIBILITY_MANIFEST="$compiler_manifest" \
    sh "$root_dir/scripts/quality_report.sh" "$source_file" "$output_file" \
    > /dev/null 2> "$report_file"; then
    echo "quality report accepted an unknown typed-IR version" >&2
    exit 1
fi
rg -q '^quality report: unsupported typed-IR dump version typed-ir-v99' "$report_file"

if QUALITY_MISSING_COUNTS=1 ELISA_TRANSLATOR_BIN="$fake_translator" \
    ELISA_COMPILER_COMPATIBILITY_MANIFEST="$compiler_manifest" \
    sh "$root_dir/scripts/quality_report.sh" "$source_file" "$output_file" \
    > /dev/null 2> "$report_file"; then
    echo "quality report accepted a typed-IR dump without counts" >&2
    exit 1
fi
rg -q '^quality report: expected exactly one typed-IR counts record, found 0$' "$report_file"

if QUALITY_MALFORMED_COUNTS=1 ELISA_TRANSLATOR_BIN="$fake_translator" \
    ELISA_COMPILER_COMPATIBILITY_MANIFEST="$compiler_manifest" \
    sh "$root_dir/scripts/quality_report.sh" "$source_file" "$output_file" \
    > /dev/null 2> "$report_file"; then
    echo "quality report accepted a malformed typed-IR count" >&2
    exit 1
fi
rg -q '^quality report: typed-IR v16 counts record has no unique non-negative exprs field$' "$report_file"

if QUALITY_DUPLICATE_COUNT=1 ELISA_TRANSLATOR_BIN="$fake_translator" \
    ELISA_COMPILER_COMPATIBILITY_MANIFEST="$compiler_manifest" \
    sh "$root_dir/scripts/quality_report.sh" "$source_file" "$output_file" \
    > /dev/null 2> "$report_file"; then
    echo "quality report accepted a duplicate typed-IR count field" >&2
    exit 1
fi
rg -q '^quality report: typed-IR v16 counts record has 2 exprs fields; expected exactly one$' "$report_file"

if QUALITY_TRUNCATED_IR=1 ELISA_TRANSLATOR_BIN="$fake_translator" \
    ELISA_COMPILER_COMPATIBILITY_MANIFEST="$compiler_manifest" \
    sh "$root_dir/scripts/quality_report.sh" "$source_file" "$output_file" \
    > /dev/null 2> "$report_file"; then
    echo "quality report accepted incomplete typed-IR node records" >&2
    exit 1
fi
rg -q '^quality report: typed-IR node records are malformed, unordered, or incomplete' "$report_file"

printf '{"selected_cases":[],"counts":{"unknown":1}}\n' > "$coverage_file"
if python3 "$root_dir/scripts/quality_coverage.py" "$coverage_file" > /dev/null 2>&1; then
    echo "quality coverage accepted an unknown outcome" >&2
    exit 1
fi

python3 "$root_dir/scripts/test_quality_ir_metrics.py"
python3 "$root_dir/scripts/test_quality_provenance.py"

echo "quality-report tests passed (IR-normalized pressure and acceptance coverage)"
