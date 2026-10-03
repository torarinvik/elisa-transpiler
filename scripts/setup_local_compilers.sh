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

echo "building local stage0 compiler: $stage0_bin" >&2
(
    cd "$stage0_worktree/compiler"
    go build -o "$stage0_bin" ./src
)

if [ ! -x "$stage1_bin" ]; then
    echo "seeding local stage1 compiler: $stage1_bin" >&2
    (
        cd "$stage1_worktree"
        ELISACORE_BIN="$stage0_bin" ELISA_STAGE1_BIN="$stage1_bin" \
            bash scripts/elisac_stage1.sh --seed
    )
fi

if [ ! -f "$stage1_runtime" ]; then
    echo "building local stage1 runtime: $stage1_runtime" >&2
    (
        cd "$stage1_worktree"
        ELISACORE_BIN="$stage0_bin" ELISA_RUNTIME_OBJ="$stage1_runtime" \
            bash scripts/build_runtime_object.sh
    )
fi

if [ ! -f "$stage1_worktree/scripts/assert_stage1_fresh.sh" ]; then
    echo "missing Stage1 source-freshness guard: $stage1_worktree/scripts/assert_stage1_fresh.sh" >&2
    exit 2
fi
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
