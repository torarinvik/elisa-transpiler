#!/bin/sh

# Shared translator-build cache checks. The caller provides hash_file().
translator_build_cache_is_fresh() {
    [ "$#" -eq 3 ] || return 2
    translator_cache_binary=$1
    translator_cache_fingerprint=$2
    translator_cache_expected_inputs=$3
    [ -x "$translator_cache_binary" ] && [ -f "$translator_cache_fingerprint" ] || return 1

    translator_cache_recorded_inputs=$(sed -n '1p' "$translator_cache_fingerprint") || return 1
    translator_cache_recorded_binary=$(sed -n '2p' "$translator_cache_fingerprint") || return 1
    [ "$translator_cache_recorded_inputs" = "$translator_cache_expected_inputs" ] || return 1
    translator_cache_current_binary=$(hash_file "$translator_cache_binary") || return 1
    [ "$translator_cache_recorded_binary" = "$translator_cache_current_binary" ]
}

translator_build_cache_write() {
    [ "$#" -eq 3 ] || return 2
    translator_cache_write_path=$1
    translator_cache_write_inputs=$2
    translator_cache_write_binary=$3
    translator_cache_write_tmp="$translator_cache_write_path.tmp.$$"
    printf '%s\n%s\n' "$translator_cache_write_inputs" "$translator_cache_write_binary" > "$translator_cache_write_tmp" || return 1
    if ! mv -f "$translator_cache_write_tmp" "$translator_cache_write_path"; then
        rm -f "$translator_cache_write_tmp"
        return 1
    fi
}

# Bind compatibility metadata to the translator build cache. A compiler-pair
# or validation-status change must make an old translator build ineligible for
# reuse, even when its Elisa sources are unchanged.
translator_build_cache_inputs_fingerprint() {
    [ "$#" -eq 2 ] || return 2
    translator_cache_source_fingerprint=$1
    translator_cache_compatibility_manifest=$2
    [ -f "$translator_cache_compatibility_manifest" ] || return 1
    translator_cache_compatibility_hash=$(hash_file "$translator_cache_compatibility_manifest") || return 1
    printf 'source_fingerprint=%s\ncompatibility_manifest_sha256=%s\n' \
        "$translator_cache_source_fingerprint" "$translator_cache_compatibility_hash" | hash_stream
}
