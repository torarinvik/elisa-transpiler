#!/bin/sh
set -eu

root_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root_dir"
workspace_parent=$(CDPATH= cd -- "$root_dir/.." && pwd)
worktree_root=${ELISA_TRANSLATOR_COMPILER_WORKTREES:-$workspace_parent/elisa-transpiler-worktrees}
stage0_worktree=${ELISA_STAGE0_WORKTREE:-$worktree_root/stage0-latest}
stage1_worktree=${ELISA_STAGE1_WORKTREE:-$worktree_root/transpiler}

# The defaults match the two compiler checkouts already used by this workspace.
# Stage0 is the Go compiler in the sibling `Go projects/Elisa-core` checkout,
# while stage1 lives beside the translator. Override either source when
# bootstrapping a different layout. The old `structpy-tree` path was a
# historical checkout stub and is deliberately not selected implicitly.
stage0_source=${ELISA_STAGE0_REPO:-$workspace_parent/../Go projects/Elisa-core}
stage1_source=${ELISA_STAGE1_REPO:-$workspace_parent/Elisa-compiler}
stage0_branch=${ELISA_STAGE0_BRANCH:-codex/transpiler-local-stage0-latest}
stage1_branch=${ELISA_STAGE1_BRANCH:-codex/transpiler-local-stage1}
stage0_go_parallelism=${ELISA_STAGE0_GO_BUILD_PARALLELISM:-1}
minimum_free_percent=${ELISA_SETUP_MIN_SYSTEM_FREE_PERCENT:-60}
minimum_seed_initial_free_percent=${ELISA_SETUP_SEED_MIN_INITIAL_SYSTEM_FREE_PERCENT:-80}

case "$stage0_go_parallelism" in
    [1-9]|[1-9][0-9]|1[01][0-9]|12[0-8]) ;;
    *)
        echo "invalid ELISA_STAGE0_GO_BUILD_PARALLELISM '$stage0_go_parallelism': expected an integer from 1 to 128" >&2
        exit 2
        ;;
esac
case "$minimum_free_percent" in
    [1-9]|[1-9][0-9]) ;;
    *)
        echo "invalid ELISA_SETUP_MIN_SYSTEM_FREE_PERCENT '$minimum_free_percent': expected an integer from 1 to 99" >&2
        exit 2
        ;;
esac
case "$minimum_seed_initial_free_percent" in
    [1-9]|[1-9][0-9]) ;;
    *)
        echo "invalid ELISA_SETUP_SEED_MIN_INITIAL_SYSTEM_FREE_PERCENT '$minimum_seed_initial_free_percent': expected an integer from 1 to 99" >&2
        exit 2
        ;;
esac

# Do not rebuild Stage0 while another worktree is in the high-memory Stage1
# seed. The actual seed script still acquires this lock later; this early
# read-only check avoids adding compiler load before that script can refuse a
# known conflict. The seed script remains authoritative for stale-lock recovery
# and for the race where another seed starts after this check.
global_seed_lock=${ELISA_STAGE1_GLOBAL_SEED_LOCK_DIR:-${TMPDIR:-/tmp}/elisac-stage1-global-seed.lock}
if [ -d "$global_seed_lock" ] && [ -f "$global_seed_lock/pid" ]; then
    global_seed_lock_pid=$(sed -n '1p' "$global_seed_lock/pid")
    case "$global_seed_lock_pid" in
        ''|*[!0-9]*) ;;
        *)
            if kill -0 "$global_seed_lock_pid" 2>/dev/null; then
                echo "compiler setup: Stage1 seed already running (pid $global_seed_lock_pid); refusing before Stage0 build" >&2
                exit 2
            fi
            ;;
    esac
fi

mkdir -p "$worktree_root"

ensure_worktree() {
    source_repo=$1
    target_worktree=$2
    branch_name=$3

    if [ -e "$target_worktree/.git" ] || [ -f "$target_worktree/.git" ]; then
        git -C "$target_worktree" rev-parse --show-toplevel >/dev/null
        return
    fi
    if [ -e "$target_worktree" ]; then
        echo "refusing to use non-worktree path: $target_worktree" >&2
        exit 2
    fi
    source_repo=$(CDPATH= cd -- "$source_repo" && pwd -P)
    if git -C "$source_repo" show-ref --verify --quiet "refs/heads/$branch_name"; then
        git -C "$source_repo" worktree add "$target_worktree" "$branch_name"
    else
        git -C "$source_repo" worktree add -b "$branch_name" "$target_worktree" HEAD
    fi
}

ensure_worktree "$stage0_source" "$stage0_worktree" "$stage0_branch"
ensure_worktree "$stage1_source" "$stage1_worktree" "$stage1_branch"
stage1_worktree=$(CDPATH= cd -- "$stage1_worktree" && pwd -P)

stage1_stdlib=${ELISA_STAGE1_STDLIB:-$stage1_worktree/elisacore_std}
sh "$root_dir/scripts/ensure_local_stdlib_link.sh" "$root_dir" "$stage1_stdlib"

mkdir -p "$stage0_worktree/compiler/bin" "$stage1_worktree/bin" "$stage1_worktree/build"
stage0_bin=${ELISAC_LOCAL_BIN:-$stage0_worktree/compiler/bin/elisac-local}
stage1_bin=${ELISA_STAGE1_BIN:-$stage1_worktree/bin/elisac-stage1}
stage1_runtime=${ELISA_STAGE1_RUNTIME:-$stage1_worktree/build/runtime/elisacore_runtime.o}

run_bounded() {
    max_rss_kb=$1
    timeout_seconds=$2
    free_floor=$3
    initial_free_floor=$4
    shift 4
    if [ "$(uname -s)" = Darwin ]; then
        if [ -n "$initial_free_floor" ]; then
            set -- python3 "$root_dir/scripts/run_bounded_process.py" \
                --max-rss-kb "$max_rss_kb" --timeout-seconds "$timeout_seconds" \
                --min-system-free-percent "$free_floor" \
                --require-initial-system-free-percent "$initial_free_floor" -- "$@"
        else
            set -- python3 "$root_dir/scripts/run_bounded_process.py" \
                --max-rss-kb "$max_rss_kb" --timeout-seconds "$timeout_seconds" \
                --min-system-free-percent "$free_floor" -- "$@"
        fi
    else
        set -- python3 "$root_dir/scripts/run_bounded_process.py" \
            --max-rss-kb "$max_rss_kb" --timeout-seconds "$timeout_seconds" -- "$@"
    fi
    "$@"
}

echo "building local stage0 compiler: $stage0_bin" >&2
(
    cd "$stage0_worktree/compiler"
    run_bounded 1572864 600 "$minimum_free_percent" "" go build \
        -p "$stage0_go_parallelism" -o "$stage0_bin" ./src
)

if [ ! -f "$stage1_worktree/scripts/assert_stage1_fresh.sh" ]; then
    echo "missing Stage1 source-freshness guard: $stage1_worktree/scripts/assert_stage1_fresh.sh" >&2
    exit 2
fi

# Stage0 was just rebuilt above, but Stage1 provenance does not currently include
# the Stage0 product hash. Therefore an existing Stage1 binary can be fresh with
# respect to its own sources and still have been seeded by an older Stage0. Always
# reseed here so this command produces a reproducible, current compiler pair.
echo "seeding local stage1 compiler: $stage1_bin" >&2
(
    cd "$stage1_worktree"
    export ELISACORE_BIN="$stage0_bin" ELISA_STAGE1_BIN="$stage1_bin"
    run_bounded 6291456 900 "$minimum_free_percent" \
        "$minimum_seed_initial_free_percent" \
        bash scripts/elisac_stage1.sh --seed
)

# The runtime builder hashes all runtime inputs and the selected Stage1 product;
# invoking it each time safely no-ops when the configured object is already current.
echo "verifying local stage1 runtime: $stage1_runtime" >&2
(
    cd "$stage1_worktree"
    export ELISACORE_BIN="$stage0_bin" ELISA_STAGE1_BIN="$stage1_bin" \
        ELISA_RUNTIME_OBJ="$stage1_runtime"
    run_bounded 2097152 300 "$minimum_free_percent" "" \
        bash scripts/build_runtime_object.sh
)

case "$stage1_bin" in
    /*) ;;
    *) stage1_bin="$root_dir/$stage1_bin" ;;
esac
if [ -x "$stage1_bin" ]; then
    stage1_bin_dir=$(CDPATH= cd -- "$(dirname -- "$stage1_bin")" && pwd -P)
    stage1_bin="$stage1_bin_dir/$(basename -- "$stage1_bin")"
fi
bash "$stage1_worktree/scripts/assert_stage1_fresh.sh" "$stage1_bin"

echo "local stage0: $stage0_bin"
echo "local stage1: $stage1_bin"
echo "local runtime: $stage1_runtime"
