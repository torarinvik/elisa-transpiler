#!/bin/sh

# Bash propagates ERR traps into sourced test suites with errtrace enabled.
# Keep test.sh usable from other POSIX shells; those shells simply omit this
# extra source-line detail rather than depending on a non-portable trap mode.
test_install_failure_trace() {
    if [ -n "${BASH_VERSION:-}" ]; then
        set -E
        trap 'test_failure_status=$?; case $- in *e*) printf "translator test command failed (status %s) at %s:%s: %s\n" "$test_failure_status" "${BASH_SOURCE[0]}" "$LINENO" "$BASH_COMMAND" >&2 ;; esac' ERR
    fi
}
