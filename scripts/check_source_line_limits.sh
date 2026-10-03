#!/bin/sh
set -eu

root_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
max_lines=600

# Only maintained Elisa implementation files are in scope. Generated Elisa and
# compiler outputs under build/ are intentionally excluded from this gate.
find "$root_dir/src" "$root_dir/cpp_lib" -type f -name '*.elisa' -print |
while IFS= read -r source_file; do
    line_count=$(awk 'END { print NR }' "$source_file")
    if [ "$line_count" -gt "$max_lines" ]; then
        printf 'source line limit exceeded (%s > %s): %s\n' \
            "$line_count" "$max_lines" "$source_file" >&2
        exit 1
    fi
done

echo "Elisa source line limit OK (src/ and cpp_lib/, max ${max_lines}; generated build outputs excluded)"
