#!/bin/sh
set -eu

root_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
. "$root_dir/scripts/build_cache.sh"

hash_file() {
    if command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | awk '{ print $1 }'
    elif command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{ print $1 }'
    else
        echo "need shasum or sha256sum to test build-cache fingerprints" >&2
        return 2
    fi
}

hash_stream() {
    if command -v shasum >/dev/null 2>&1; then
        shasum -a 256 | awk '{ print $1 }'
    elif command -v sha256sum >/dev/null 2>&1; then
        sha256sum | awk '{ print $1 }'
    else
        echo "need shasum or sha256sum to test build-cache fingerprints" >&2
        return 2
    fi
}

cache_test_dir=$(mktemp -d /tmp/elisa-transpiler-cache-test.XXXXXX)
trap 'rm -rf "$cache_test_dir"' EXIT HUP INT TERM
cache_test_binary="$cache_test_dir/elisa-c-transpiler"
cache_test_fingerprint="$cache_test_dir/translator-build.fingerprint"
cache_test_manifest="$cache_test_dir/compiler_compatibility.json"

printf '{"compiler":"pair-a"}\n' > "$cache_test_manifest"
first_inputs_fingerprint=$(translator_build_cache_inputs_fingerprint source-fingerprint "$cache_test_manifest")
printf '{"compiler":"pair-b"}\n' > "$cache_test_manifest"
second_inputs_fingerprint=$(translator_build_cache_inputs_fingerprint source-fingerprint "$cache_test_manifest")
[ "$first_inputs_fingerprint" != "$second_inputs_fingerprint" ] || {
    echo "compiler compatibility manifest change did not invalidate the build fingerprint" >&2
    exit 1
}

printf '#!/bin/sh\nexit 0\n' > "$cache_test_binary"
chmod +x "$cache_test_binary"
original_binary_hash=$(hash_file "$cache_test_binary")
translator_build_cache_write "$cache_test_fingerprint" source-fingerprint "$original_binary_hash"
translator_build_cache_is_fresh "$cache_test_binary" "$cache_test_fingerprint" source-fingerprint || {
    echo "matching build-cache fingerprint was rejected" >&2
    exit 1
}

translator_build_cache_write "$cache_test_fingerprint" stale-source-fingerprint "$original_binary_hash"
if translator_build_cache_is_fresh "$cache_test_binary" "$cache_test_fingerprint" source-fingerprint; then
    echo "stale source fingerprint was accepted" >&2
    exit 1
fi

translator_build_cache_write "$cache_test_fingerprint" source-fingerprint "$original_binary_hash"
printf '# changed binary bytes\n' >> "$cache_test_binary"
if translator_build_cache_is_fresh "$cache_test_binary" "$cache_test_fingerprint" source-fingerprint; then
    echo "modified translator executable was accepted" >&2
    exit 1
fi

changed_binary_hash=$(hash_file "$cache_test_binary")
translator_build_cache_write "$cache_test_fingerprint" source-fingerprint "$changed_binary_hash"
translator_build_cache_is_fresh "$cache_test_binary" "$cache_test_fingerprint" source-fingerprint || {
    echo "updated binary fingerprint was rejected" >&2
    exit 1
}

chmod -x "$cache_test_binary"
if translator_build_cache_is_fresh "$cache_test_binary" "$cache_test_fingerprint" source-fingerprint; then
    echo "non-executable translator was accepted" >&2
    exit 1
fi

echo "translator build-cache tests passed (input fingerprint, binary hash, executable status)"
