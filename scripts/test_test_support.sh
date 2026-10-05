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

. "$root_dir/scripts/test_support.sh"
cd "$root_dir"
bounded_test_dir=$(mktemp -d "${TMPDIR:-/tmp}/elisa-bounded-test-command.XXXXXX")
trap 'rm -rf "$bounded_test_dir"' EXIT HUP INT TERM
bounded_fake_command=$bounded_test_dir/fake-command
bounded_stdout=$bounded_test_dir/stdout
bounded_stderr=$bounded_test_dir/stderr
printf '%s\n' \
    '#!/bin/sh' \
    'printf "child-stdout\\n"' \
    'printf "child-stderr\\n" >&2' \
    'printf "arg:%s\\n" "$@"' \
    'exit "${FAKE_TEST_STATUS:-0}"' > "$bounded_fake_command"
chmod +x "$bounded_fake_command"

if [ "$(uname -s)" = Darwin ]; then
    ELISA_SETUP_MIN_SYSTEM_FREE_PERCENT=1 \
        test_run_bounded_process 262144 5 "$bounded_fake_command" "arg with spaces" \
        > "$bounded_stdout" 2> "$bounded_stderr"
else
    test_run_bounded_process 262144 5 "$bounded_fake_command" "arg with spaces" \
        > "$bounded_stdout" 2> "$bounded_stderr"
fi
printf 'child-stdout\narg:arg with spaces\n' > "$bounded_test_dir/expected.stdout"
printf 'child-stderr\n' > "$bounded_test_dir/expected.stderr"
if ! cmp -s "$bounded_test_dir/expected.stdout" "$bounded_stdout" \
    || ! cmp -s "$bounded_test_dir/expected.stderr" "$bounded_stderr"; then
    echo "bounded test command changed successful child output" >&2
    exit 1
fi

if [ "$(uname -s)" = Darwin ]; then
    if ELISA_SETUP_MIN_SYSTEM_FREE_PERCENT=1 FAKE_TEST_STATUS=23 \
        test_run_bounded_process 262144 5 "$bounded_fake_command" > /dev/null 2> "$bounded_stderr"; then
        bounded_status=0
    else
        bounded_status=$?
    fi
else
    if FAKE_TEST_STATUS=23 test_run_bounded_process 262144 5 "$bounded_fake_command" \
        > /dev/null 2> "$bounded_stderr"; then
        bounded_status=0
    else
        bounded_status=$?
    fi
fi
if [ "$bounded_status" -ne 23 ] || ! rg -q 'child-stderr' "$bounded_stderr" \
    || ! rg -q 'peak process-group RSS' "$bounded_stderr"; then
    echo "bounded test command did not preserve child failure/diagnostics" >&2
    exit 1
fi

for bounded_probe in \
    scripts/test_clang_timeout.py \
    scripts/test_ast_depth.py \
    scripts/test_metamorphic.py \
    scripts/test_decl_dependency_closure.py \
    scripts/test_inline_dependency_closure.py \
    scripts/test_template_specialization_closure.py \
    scripts/test_transitive_decl_closure.py \
    scripts/test_unqualified_cpp_layout.py \
    scripts/test_missing_decl_dependency.py; do
    if ! rg -Fq "test_python_probe_bounded $bounded_probe" "$root_dir/scripts/test.sh"; then
        printf 'integration probe is not process-bounded: %s\n' "$bounded_probe" >&2
        exit 1
    fi
done
if ! rg -Fq 'test_run_bounded_process \' "$root_dir/scripts/test.sh" \
    || ! rg -Fq 'sh scripts/test_clang_failure.sh' "$root_dir/scripts/test.sh"; then
    echo "Clang-failure shell probe is not process-bounded" >&2
    exit 1
fi

printf 'test failure attribution and bounded-command checks passed\n'
