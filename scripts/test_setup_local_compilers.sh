#!/bin/sh
set -eu

root_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
temporary_root=$(mktemp -d "${TMPDIR:-/tmp}/elisa-compiler-setup-test.XXXXXX")
trap 'rm -rf "$temporary_root"' EXIT HUP INT TERM
setup_script="$root_dir/scripts/setup_local_compilers.sh"
test_script="$root_dir/scripts/test.sh"
manifest_runner="$root_dir/scripts/run_fixture_manifest.py"

expect_rejected_before_side_effects() {
    setting_name=$1
    setting_value=$2
    expected_message=$3
    worktree_root="$temporary_root/worktrees-$setting_name"
    if env \
        ELISA_TRANSLATOR_COMPILER_WORKTREES="$worktree_root" \
        "$setting_name=$setting_value" \
        sh "$setup_script" >"$temporary_root/out" 2>"$temporary_root/err"; then
        echo "compiler setup accepted invalid $setting_name=$setting_value" >&2
        exit 1
    fi
    grep -Fq "$expected_message" "$temporary_root/err"
    [ ! -e "$worktree_root" ]
}

expect_rejected_before_side_effects \
    ELISA_STAGE0_GO_BUILD_PARALLELISM 0 \
    'invalid ELISA_STAGE0_GO_BUILD_PARALLELISM'
expect_rejected_before_side_effects \
    ELISA_STAGE0_GO_BUILD_PARALLELISM 129 \
    'invalid ELISA_STAGE0_GO_BUILD_PARALLELISM'
expect_rejected_before_side_effects \
    ELISA_STAGE0_GO_BUILD_PARALLELISM many \
    'invalid ELISA_STAGE0_GO_BUILD_PARALLELISM'
expect_rejected_before_side_effects \
    ELISA_SETUP_MIN_SYSTEM_FREE_PERCENT 0 \
    'invalid ELISA_SETUP_MIN_SYSTEM_FREE_PERCENT'
expect_rejected_before_side_effects \
    ELISA_SETUP_MIN_SYSTEM_FREE_PERCENT 100 \
    'invalid ELISA_SETUP_MIN_SYSTEM_FREE_PERCENT'
expect_rejected_before_side_effects \
    ELISA_SETUP_SEED_MIN_INITIAL_SYSTEM_FREE_PERCENT 0 \
    'invalid ELISA_SETUP_SEED_MIN_INITIAL_SYSTEM_FREE_PERCENT'
expect_rejected_before_side_effects \
    ELISA_SETUP_SEED_MIN_INITIAL_SYSTEM_FREE_PERCENT 100 \
    'invalid ELISA_SETUP_SEED_MIN_INITIAL_SYSTEM_FREE_PERCENT'

live_seed_lock="$temporary_root/live-seed-lock"
mkdir "$live_seed_lock"
printf '%s\n' "$$" > "$live_seed_lock/pid"
live_lock_worktrees="$temporary_root/worktrees-live-seed-lock"
if env \
    ELISA_TRANSLATOR_COMPILER_WORKTREES="$live_lock_worktrees" \
    ELISA_STAGE1_GLOBAL_SEED_LOCK_DIR="$live_seed_lock" \
    sh "$setup_script" >"$temporary_root/out" 2>"$temporary_root/err"; then
    echo "compiler setup started despite a live Stage1 seed lock" >&2
    exit 1
fi
grep -Fq 'Stage1 seed already running' "$temporary_root/err"
[ ! -e "$live_lock_worktrees" ]

grep -Fq 'stage0_go_parallelism" -o "$stage0_bin" ./src' "$setup_script"
grep -Fq 'minimum_free_percent=${ELISA_SETUP_MIN_SYSTEM_FREE_PERCENT:-60}' "$setup_script"
grep -Fq 'minimum_seed_initial_free_percent=${ELISA_SETUP_SEED_MIN_INITIAL_SYSTEM_FREE_PERCENT:-80}' "$setup_script"
grep -Fq 'run_bounded 6291456 900 "$minimum_free_percent"' "$setup_script"
grep -Fq '"$minimum_seed_initial_free_percent"' "$setup_script"
grep -Fq 'require-initial-system-free-percent "$initial_free_floor"' "$setup_script"
grep -Fq 'run_bounded 2097152 300 "$minimum_free_percent"' "$setup_script"
grep -Fq 'ELISA_SETUP_MIN_SYSTEM_FREE_PERCENT:-60' "$test_script"
grep -Fq 'DEFAULT_MACOS_SYSTEM_MEMORY_FLOOR_PERCENT = 60' "$manifest_runner"
if grep -Fq 'if [ ! -x "$stage1_bin" ]' "$setup_script"; then
    echo "compiler setup must not reuse Stage1 based only on binary existence" >&2
    exit 1
fi

echo "local compiler setup resource-configuration checks passed"
