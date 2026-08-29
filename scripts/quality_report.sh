#!/bin/sh
set -eu

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    echo "usage: $0 SOURCE [OUTPUT]" >&2
    exit 2
fi

source_path=$1
output_path=${2:-build/quality.generated.elisa}
mkdir -p "$(dirname -- "$output_path")"
./build/elisa-c-transpiler "$source_path" > "$output_path"

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
