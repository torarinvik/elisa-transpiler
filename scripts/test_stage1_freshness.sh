#!/bin/sh
set -eu

root_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
workspace_parent=$(CDPATH= cd -- "$root_dir/.." && pwd)
stage1_worktree=${1:-${ELISA_STAGE1_WORKTREE:-$workspace_parent/elisa-transpiler-worktrees/transpiler}}
freshness_guard=$stage1_worktree/scripts/assert_stage1_fresh.sh

if [ ! -f "$freshness_guard" ]; then
    echo "SKIP Stage1 freshness-guard regression: compiler guard unavailable at $freshness_guard"
    exit 0
fi

test_root=$(CDPATH= cd -- "$(mktemp -d "${TMPDIR:-/tmp}/elisa-stage1-freshness.XXXXXX")" && pwd -P)
trap 'rm -rf "$test_root"' EXIT HUP INT TERM
mkdir -p "$test_root/compiler/bin" "$test_root/compiler/scripts" \
    "$test_root/compiler/src" "$test_root/compiler/elisacore_std"
cp "$freshness_guard" "$test_root/compiler/scripts/assert_stage1_fresh.sh"
cp "$(command -v sh)" "$test_root/compiler/bin/elisac-stage1"
chmod +x "$test_root/compiler/bin/elisac-stage1"
touch -t 200001010000 "$test_root/compiler/bin/elisac-stage1"
touch -t 200001020000 "$test_root/compiler/src/newer_source.elisa"

set +e
stale_output=$(bash "$test_root/compiler/scripts/assert_stage1_fresh.sh" \
    "$test_root/compiler/bin/elisac-stage1" 2>&1)
stale_status=$?
set -e
if [ "$stale_status" -ne 2 ] || ! printf '%s\n' "$stale_output" \
    | grep -q 'stage1 product binary is stale'; then
    echo "Stage1 freshness guard did not reject a stale in-worktree product" >&2
    printf '%s\n' "$stale_output" >&2
    exit 1
fi

touch -t 200001030000 "$test_root/compiler/bin/elisac-stage1"
bash "$test_root/compiler/scripts/assert_stage1_fresh.sh" \
    "$test_root/compiler/bin/elisac-stage1"
echo "Stage1 freshness-guard regressions passed"
