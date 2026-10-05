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
git -C "$test_root/compiler" init -q
git -C "$test_root/compiler" -c user.name="Stage1 freshness test" \
    -c user.email="stage1-freshness@example.invalid" commit --allow-empty -q -m baseline
cp "$freshness_guard" "$test_root/compiler/scripts/assert_stage1_fresh.sh"
cp "$(command -v sh)" "$test_root/compiler/bin/elisac-stage1"
chmod +x "$test_root/compiler/bin/elisac-stage1"

if [ -f "$stage1_worktree/scripts/stage1_provenance.py" ]; then
    cp "$stage1_worktree/scripts/stage1_provenance.py" \
        "$test_root/compiler/scripts/stage1_provenance.py"
    for recipe in elisac_stage1.sh elisac_stage1_seed.sh \
        build_runtime_object.sh write_profiler_hook_fallbacks.sh; do
        touch "$test_root/compiler/scripts/$recipe"
    done
    touch "$test_root/compiler/src/baseline.elisa"
    python3 "$test_root/compiler/scripts/stage1_provenance.py" record \
        "$test_root/compiler" "$test_root/compiler/bin/elisac-stage1" >/dev/null
    touch "$test_root/compiler/src/changed_after_record.elisa"
    stale_pattern='stage1 product is stale'
else
    touch -t 200001010000 "$test_root/compiler/bin/elisac-stage1"
    touch -t 200001020000 "$test_root/compiler/src/newer_source.elisa"
    stale_pattern='stage1 product binary is stale'
fi

set +e
stale_output=$(bash "$test_root/compiler/scripts/assert_stage1_fresh.sh" \
    "$test_root/compiler/bin/elisac-stage1" 2>&1)
stale_status=$?
set -e
if [ "$stale_status" -ne 2 ] || ! printf '%s\n' "$stale_output" \
    | grep -q "$stale_pattern"; then
    echo "Stage1 freshness guard did not reject a stale in-worktree product" >&2
    printf '%s\n' "$stale_output" >&2
    exit 1
fi

if [ -f "$test_root/compiler/scripts/stage1_provenance.py" ]; then
    python3 "$test_root/compiler/scripts/stage1_provenance.py" record \
        "$test_root/compiler" "$test_root/compiler/bin/elisac-stage1" >/dev/null
    touch "$test_root/compiler/bin/elisac-stage1"
else
    touch -t 200001030000 "$test_root/compiler/bin/elisac-stage1"
fi
bash "$test_root/compiler/scripts/assert_stage1_fresh.sh" \
    "$test_root/compiler/bin/elisac-stage1"
echo "Stage1 freshness-guard regressions passed"
