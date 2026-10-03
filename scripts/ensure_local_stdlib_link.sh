#!/bin/sh
set -eu

if [ "$#" -ne 2 ]; then
    echo "usage: ensure_local_stdlib_link.sh TRANSLATOR_ROOT ELISACORE_STD_DIR" >&2
    exit 2
fi

translator_root=$(CDPATH= cd -- "$1" && pwd -P) || {
    echo "translator root does not exist: $1" >&2
    exit 2
}
stdlib_root=$(CDPATH= cd -- "$2" && pwd -P) || {
    echo "Elisa standard library directory does not exist: $2" >&2
    exit 2
}
link_path=$translator_root/src/.compiler_std

for required_file in elisacore_runtime.elisa elisacore_json.elisa collections.elisa; do
    if [ ! -f "$stdlib_root/$required_file" ]; then
        echo "selected Elisa standard library is missing $required_file: $stdlib_root" >&2
        exit 2
    fi
done

if [ ! -d "$translator_root/src" ]; then
    echo "translator source directory does not exist: $translator_root/src" >&2
    exit 2
fi

if [ -L "$link_path" ]; then
    existing_target=$(readlink "$link_path") || {
        echo "cannot read existing standard library link: $link_path" >&2
        exit 2
    }
    case "$existing_target" in
        /*) existing_path=$existing_target ;;
        *) existing_path=$(dirname "$link_path")/$existing_target ;;
    esac
    existing_root=$(CDPATH= cd -- "$existing_path" 2>/dev/null && pwd -P) || existing_root=
    if [ "$existing_root" != "$stdlib_root" ]; then
        echo "refusing to replace conflicting standard library link: $link_path" >&2
        echo "  existing: $existing_target" >&2
        echo "  selected: $stdlib_root" >&2
        exit 2
    fi
elif [ -e "$link_path" ]; then
    echo "refusing to replace non-symlink standard library path: $link_path" >&2
    exit 2
else
    ln -s "$stdlib_root" "$link_path"
fi
