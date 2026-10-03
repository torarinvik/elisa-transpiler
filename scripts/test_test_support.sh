#!/bin/sh
set -eu

root_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

set +e
failure_output=$(bash -c '
    set -eu
    . "$1/scripts/test_support.sh"
    test_install_failure_trace
    . /dev/stdin
' test_test_support "$root_dir" 2>&1 <<'SH'
if ! false; then
    printf 'handled expected failure\n'
fi
set +e
false
handled_status=$?
set -e
[ "$handled_status" -eq 1 ]
printf 'reached deliberate failure\n'
false
SH
)
failure_status=$?
set -e

if [ "$failure_status" -ne 1 ] || \
    ! printf '%s\n' "$failure_output" | rg -Fq 'translator test command failed (status 1) at /dev/stdin:10: false' || \
    ! printf '%s\n' "$failure_output" | rg -Fq 'handled expected failure' || \
    ! printf '%s\n' "$failure_output" | rg -Fq 'reached deliberate failure'; then
    printf 'failure-trace test expected a line-qualified error for the deliberate command (exit=%s)\n%s\n' \
        "$failure_status" "$failure_output" >&2
    exit 1
fi

trace_count=$(printf '%s\n' "$failure_output" | rg -c 'translator test command failed' || true)
if [ "$trace_count" -ne 1 ]; then
    printf 'failure-trace test reported an expected/handled failure\n%s\n' "$failure_output" >&2
    exit 1
fi

printf 'test failure line attribution checks passed\n'
