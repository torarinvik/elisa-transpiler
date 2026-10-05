#!/bin/sh
set -eu

root_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root_dir"

if [ "$(uname -s)" = Darwin ]; then
    ELISA_SETUP_MIN_SYSTEM_FREE_PERCENT=${ELISA_SETUP_MIN_SYSTEM_FREE_PERCENT:-41}
    export ELISA_SETUP_MIN_SYSTEM_FREE_PERCENT
fi

. "$root_dir/scripts/test_support.sh"
test_install_failure_trace

test_suite=all
reuse_build=0

usage() {
    cat <<'EOF'
Usage: sh scripts/test.sh [--suite all|fixtures|projects|control-flow|upstream] [--reuse-build]

  --suite NAME   Run one focused suite; the default is all.
  --reuse-build  Reuse the translator only when source/toolchain fingerprints
                 and the built executable hash still match. Tests still run.
EOF
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --suite)
            [ "$#" -ge 2 ] || { usage >&2; exit 2; }
            test_suite=$2
            shift 2
            ;;
        --reuse-build)
            reuse_build=1
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            printf 'unknown test option: %s\n' "$1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

case "$test_suite" in
    all|fixtures|projects|control-flow|upstream) ;;
    *)
        printf 'unknown test suite: %s\n' "$test_suite" >&2
        usage >&2
        exit 2
        ;;
esac

sh scripts/check_source_line_limits.sh
sh scripts/test_build_cache.sh
sh scripts/test_test_support.sh
python3 scripts/test_fixture_manifest.py
python3 scripts/test_run_bounded_process.py
sh scripts/test_ensure_local_stdlib_link.sh

compiler_worktree_root=${ELISA_TRANSLATOR_COMPILER_WORKTREES:-$root_dir/../elisa-transpiler-worktrees}
# The current stage1 source uses syntax that the legacy Elisa-core checkout
# cannot parse. Default to the isolated stage0 built from structpy-tree; keep
# the override for deliberately testing an older bootstrap compiler.
stage0_worktree=${ELISA_STAGE0_WORKTREE:-$compiler_worktree_root/stage0-latest}
stage1_worktree=${ELISA_STAGE1_WORKTREE:-$compiler_worktree_root/transpiler}
if [ -d "$stage1_worktree" ]; then
    stage1_worktree=$(CDPATH= cd -- "$stage1_worktree" && pwd -P)
fi
stage1_stdlib=${ELISA_STAGE1_STDLIB:-$stage1_worktree/elisacore_std}

sh scripts/test_stage1_freshness.sh "$stage1_worktree"

if [ -n "${ELISAC_BIN:-}" ]; then
    elisa_bin=$ELISAC_BIN
    echo "using explicit Elisa compiler: $elisa_bin" >&2
else
    elisa_bin="$stage0_worktree/compiler/bin/elisac-local"
fi
case "$elisa_bin" in
    /*) ;;
    *) elisa_bin="$root_dir/$elisa_bin" ;;
esac

# A self-hosted stage1 compiler emits translator objects that may need the
# runtime object from the same compiler worktree at the final link. Keep this
# opt-in so the normal local stage0 path retains its existing profile-hook
# behavior, while explicit stage1 verification cannot accidentally link a
# mismatched or installed runtime.
elisa_runtime=${ELISAC_RUNTIME:-}
case "$elisa_runtime" in
    "") ;;
    /*) ;;
    *) elisa_runtime="$root_dir/$elisa_runtime" ;;
esac
if [ -n "$elisa_runtime" ] && [ ! -f "$elisa_runtime" ]; then
    echo "missing explicit Elisa runtime object: $elisa_runtime" >&2
    exit 2
fi

stage1_bin=${ELISA_STAGE1_BIN:-$stage1_worktree/bin/elisac-stage1}
stage1_runtime=${ELISA_STAGE1_RUNTIME:-$stage1_worktree/build/runtime/elisacore_runtime.o}

# When the caller explicitly selects a stage1 compiler/runtime pair, use that
# same runtime for the legacy direct-link checks below as well. Otherwise a
# direct check that explicitly names the default stage1 runtime can be mixed
# with ELISAC_RUNTIME from another worktree, producing duplicate symbols (or,
# worse, a subtly mismatched ABI).
if [ -n "$elisa_runtime" ]; then
    stage1_runtime=$elisa_runtime
fi

# Some focused checks invoke the Stage1 driver from inside its compiler
# worktree. Resolve repo-relative overrides here so those later `cd`s do not
# reinterpret the binary/runtime paths relative to the wrong repository.
case "$stage1_bin" in
    /*) ;;
    *) stage1_bin="$root_dir/$stage1_bin" ;;
esac
if [ -x "$stage1_bin" ]; then
    stage1_bin_dir=$(CDPATH= cd -- "$(dirname -- "$stage1_bin")" && pwd -P)
    stage1_bin="$stage1_bin_dir/$(basename -- "$stage1_bin")"
fi
case "$stage1_runtime" in
    /*) ;;
    *) stage1_runtime="$root_dir/$stage1_runtime" ;;
esac

# Every sourced suite uses the selected compiler/runtime pair, including
# invocations of the Stage1 wrapper that temporarily changes directory.
export ELISA_STAGE1_BIN="$stage1_bin"
export ELISA_RUNTIME_OBJ="$stage1_runtime"

if [ ! -x "$elisa_bin" ]; then
    echo "missing local Elisa stage0 compiler: $elisa_bin" >&2
    echo "run scripts/setup_local_compilers.sh or set ELISAC_BIN explicitly" >&2
    exit 2
fi

case "$test_suite" in
    all|projects)
        if [ ! -x "$stage1_bin" ]; then
            echo "missing local Elisa stage1 compiler: $stage1_bin" >&2
            echo "set ELISA_STAGE1_WORKTREE or ELISA_STAGE1_BIN to the intended local worktree" >&2
            exit 2
        fi
        if [ ! -f "$stage1_runtime" ]; then
            echo "missing local Elisa stage1 runtime object: $stage1_runtime" >&2
            echo "set ELISA_STAGE1_RUNTIME to the runtime built with the selected stage1 worktree" >&2
            exit 2
        fi
        if [ ! -f "$stage1_worktree/scripts/elisac_stage1.sh" ]; then
            echo "missing local Elisa stage1 driver: $stage1_worktree/scripts/elisac_stage1.sh" >&2
            exit 2
        fi
        if [ ! -f "$stage1_worktree/scripts/assert_stage1_fresh.sh" ]; then
            echo "missing Stage1 source-freshness guard: $stage1_worktree/scripts/assert_stage1_fresh.sh" >&2
            exit 2
        fi
        ;;
esac

# Direct Stage1 fixture/project invocations must not silently test a product
# older than its selected compiler sources. The compiler-owned guard only
# checks binaries inside that compiler worktree; explicitly selected external
# snapshots remain under the caller's control.
if [ -x "$stage1_bin" ] && [ -f "$stage1_runtime" ] \
    && [ -f "$stage1_worktree/scripts/assert_stage1_fresh.sh" ]; then
    bash "$stage1_worktree/scripts/assert_stage1_fresh.sh" "$stage1_bin"
fi

sh "$root_dir/scripts/ensure_local_stdlib_link.sh" "$root_dir" "$stage1_stdlib"

mkdir -p build

profile_hooks="$stage0_worktree/compiler/runtime/profile_hooks.c"
if [ ! -f "$profile_hooks" ]; then
    profile_hooks=
fi

hash_stream() {
    if command -v shasum >/dev/null 2>&1; then
        shasum -a 256 | awk '{ print $1 }'
    elif command -v sha256sum >/dev/null 2>&1; then
        sha256sum | awk '{ print $1 }'
    else
        echo "need shasum or sha256sum to fingerprint the translator build" >&2
        return 2
    fi
}

hash_file() {
    if command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | awk '{ print $1 }'
    elif command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{ print $1 }'
    else
        echo "need shasum or sha256sum to fingerprint the translator build" >&2
        return 2
    fi
}

. "$root_dir/scripts/build_cache.sh"

translator_run_bounded() {
    translator_max_rss_kb=$1
    translator_timeout_seconds=$2
    shift 2
    if [ "$(uname -s)" = Darwin ]; then
        python3 scripts/run_bounded_process.py \
            --max-rss-kb "$translator_max_rss_kb" \
            --timeout-seconds "$translator_timeout_seconds" \
            --min-system-free-percent "${ELISA_SETUP_MIN_SYSTEM_FREE_PERCENT:-41}" -- "$@"
    else
        python3 scripts/run_bounded_process.py \
            --max-rss-kb "$translator_max_rss_kb" \
            --timeout-seconds "$translator_timeout_seconds" -- "$@"
    fi
}

compute_translator_inputs_fingerprint() {
    clang_path=$(command -v clang || true)
    [ -n "$clang_path" ] || { echo "clang is required to build the translator" >&2; return 2; }
    std_root=$stage1_stdlib
    {
        printf '%s\n' "platform=$(uname -s)/$(uname -m)" \
            'elisa_flags=-emit obj -O0' \
            'link_flags=clang -Wl,-dead_strip -lm' \
            "elisa_compiler_path=$elisa_bin" \
            "elisa_compiler_sha256=$(hash_file "$elisa_bin")" \
            "clang_path=$clang_path" \
            "clang_version=$(clang --version 2>/dev/null | sed -n '1p')" \
            "clang_sha256=$(hash_file "$clang_path")"
        if [ -n "$elisa_runtime" ]; then
            printf '%s\n' "translator_runtime=$elisa_runtime" \
                "translator_runtime_sha256=$(hash_file "$elisa_runtime")" \
                'translator_link_mode=matching-runtime-only'
        elif [ -n "$profile_hooks" ]; then
            printf '%s\n' "profile_hooks=$profile_hooks" \
                "profile_hooks_sha256=$(hash_file "$profile_hooks")" \
                'translator_link_mode=stage0-profile-hooks'
        else
            printf '%s\n' 'translator_link_mode=runtime-defaults'
        fi
        {
            find "$root_dir/src" "$root_dir/cpp_lib" "$std_root" -type f -name '*.elisa' -print
        } | LC_ALL=C sort | while IFS= read -r source_file; do
            printf 'source=%s\n' "$source_file"
            hash_file "$source_file"
        done
    } | hash_stream
}

translator_path=build/elisa-c-transpiler
fingerprint_path=build/translator-build.fingerprint
translator_inputs_fingerprint=$(compute_translator_inputs_fingerprint)
reuse_valid=0
if [ "$reuse_build" -eq 1 ] && translator_build_cache_is_fresh \
    "$translator_path" "$fingerprint_path" "$translator_inputs_fingerprint"; then
    reuse_valid=1
fi

if [ "$reuse_valid" -eq 1 ]; then
    echo "reusing fresh translator build ($translator_path)"
else
    if [ "$reuse_build" -eq 1 ]; then
        echo "translator reuse unavailable or stale; rebuilding"
    fi
    # A self-hosted frontend build is the largest routine process in this suite.
    # Keep the bound configurable for larger hosts and collect aggregate RSS for
    # the owned compiler/linker process groups. On macOS, the wrapper also bounds
    # physical footprint because compressed/swapped pages can exceed RSS greatly.
    # It never shells the argv and only signals the process group it created.
    translator_build_max_rss_kb=${ELISA_TRANSLATOR_BUILD_MAX_RSS_KB:-2097152}
    translator_build_timeout_seconds=${ELISA_TRANSLATOR_BUILD_TIMEOUT_SECONDS:-600}
    translator_run_bounded "$translator_build_max_rss_kb" "$translator_build_timeout_seconds" \
        "$elisa_bin" -emit obj -O0 -o build/transpiler.o src/main.elisa
    # A selected self-hosted stage1 runtime is a complete, matching runtime
    # boundary. Do not mix it with stage0 profiling hooks: those hooks belong
    # to the stage0 ABI and can make a stage1-built translator hang or fail in
    # otherwise unrelated probes. The default path remains unchanged.
    if [ -n "$elisa_runtime" ]; then
        translator_run_bounded "$translator_build_max_rss_kb" "$translator_build_timeout_seconds" \
            clang -Wl,-dead_strip -o "$translator_path" build/transpiler.o "$elisa_runtime" -lm
    elif [ -n "$profile_hooks" ]; then
        translator_run_bounded "$translator_build_max_rss_kb" "$translator_build_timeout_seconds" \
            clang -Wl,-dead_strip -o "$translator_path" build/transpiler.o "$profile_hooks" -lm
    else
        translator_run_bounded "$translator_build_max_rss_kb" "$translator_build_timeout_seconds" \
            clang -Wl,-dead_strip -o "$translator_path" build/transpiler.o -lm
    fi
    translator_binary_fingerprint=$(hash_file "$translator_path")
    translator_build_cache_write "$fingerprint_path" \
        "$translator_inputs_fingerprint" "$translator_binary_fingerprint"
fi

sh scripts/test_clang_failure.sh
python3 scripts/test_clang_timeout.py "$translator_path"
python3 scripts/test_ast_depth.py "$translator_path"
python3 scripts/test_metamorphic.py "$translator_path"
python3 scripts/test_decl_dependency_closure.py "$translator_path"
python3 scripts/test_inline_dependency_closure.py "$translator_path" "$elisa_bin" "$elisa_runtime"
python3 scripts/test_template_specialization_closure.py "$translator_path" "$elisa_bin" "$elisa_runtime"
python3 scripts/test_transitive_decl_closure.py "$translator_path" "$elisa_bin"
python3 scripts/test_unqualified_cpp_layout.py "$translator_path" "$elisa_bin"
python3 scripts/test_missing_decl_dependency.py "$translator_path"

case "$test_suite" in
    all|fixtures)
        python3 scripts/run_fixture_manifest.py \
            --manifest testdata/fixtures/acceptance_manifest.json \
            --translator build/elisa-c-transpiler \
            --elisa-compiler "$elisa_bin" \
            --elisa-runtime "$elisa_runtime" \
            --output-dir build/manifest-tests \
            --max-rss-kb "${ELISA_FIXTURE_PROCESS_MAX_RSS_KB:-1572864}" \
            --case simple \
            --case rewrite_explanations \
            --case function_pointer_const_field_call \
            --case c_compatible_cpp \
            --case cpp_overloads \
            --case readonly_nonnull_helper \
            --case nullable_index_after_guard \
            --case compound_assignment_once \
            --case increment_evaluation \
            --case sequencing_expressions \
            --case nested_conditional_operator \
            --case short_circuit_constant \
            --case call_argument_conditional_comma \
            --case c_enum_integer_semantics \
            --case runtime_unsigned_wrap \
            --case c_enum_typedef_aliases \
            --case c_array_to_pointer_decay \
            --case c_record_pointer_call_arguments \
            --case c_pointer_difference_element_units \
            --case c_record_pointer_difference_layout \
            --case c_record_sizeof_alignof_layout \
            --case c_void_pointer_boundaries \
            --case cpp_scoped_enum_namespace_aliases \
            --case variadic_va_arg \
            --case variadic_promotions \
            --case designated_initializers \
            --case c_record_and_six_element_array \
            --case floating_edge_values \
            --case variadic_va_copy
        ;;
esac

# The sourced suites contain many small, direct `clang -Wl,-dead_strip` links.
# That flag identifies generated Elisa objects in this harness. When an
# explicit self-hosted stage1 compiler is selected, those objects need the
# matching runtime object; inject it at the one shared link boundary rather
# than allowing each suite to grow a separate stage1/stage0 branch. Native
# C/C++ links do not use this linker flag and remain untouched. The default
# stage0 path has an empty runtime override and therefore keeps its historical
# profile-hook behavior.
elisa_host_clang=$(command -v clang)
clang() {
    if [ -z "${elisa_runtime:-}" ]; then
        "$elisa_host_clang" "$@"
        return
    fi
    elisa_generated_link=0
    elisa_runtime_present=0
    for elisa_arg in "$@"; do
        [ "$elisa_arg" = "-Wl,-dead_strip" ] && elisa_generated_link=1
        [ "$elisa_arg" = "$elisa_runtime" ] && elisa_runtime_present=1
    done
    if [ "$elisa_generated_link" -eq 1 ] && [ "$elisa_runtime_present" -eq 0 ]; then
        "$elisa_host_clang" "$@" "$elisa_runtime"
    else
        "$elisa_host_clang" "$@"
    fi
}

# These suites are sourced so they share the freshly built translator and the
# resolved local compiler/toolchain paths above.
optional_fn_supported=0
case "$test_suite" in
    all|fixtures|upstream)
        ./build/elisa-c-transpiler testdata/fixtures/nullable_function_field.c \
            > build/nullable_function_field.generated.elisa
        if "$elisa_bin" -emit obj -O0 -o build/nullable_function_field.generated.o \
            build/nullable_function_field.generated.elisa >/dev/null \
            2>build/nullable_function_field.probe.err; then
            optional_fn_supported=1
        else
            echo "SKIP capability: local Elisa compiler cannot compile nullable function fields; cJSON compile/runtime parity is skipped" >&2
        fi
        ;;
esac

case "$test_suite" in
    all)
        . "$root_dir/scripts/test_suites/core_fixtures.sh"
        . "$root_dir/scripts/test_suites/project_generation.sh"
        . "$root_dir/scripts/test_suites/control_flow.sh"
        . "$root_dir/scripts/test_suites/upstream_smoke.sh"
        ;;
    fixtures) . "$root_dir/scripts/test_suites/core_fixtures.sh" ;;
    projects) . "$root_dir/scripts/test_suites/project_generation.sh" ;;
    control-flow) . "$root_dir/scripts/test_suites/control_flow.sh" ;;
    upstream) . "$root_dir/scripts/test_suites/upstream_smoke.sh" ;;
esac

echo "translator tests passed (suite: $test_suite)"
