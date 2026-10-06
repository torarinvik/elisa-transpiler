# Release packaging

`scripts/package_release.py` assembles a relocatable release directory from an
already-built translator. It copies the executable, translator-owned Elisa
compatibility modules, and Elisa standard-library source files. It writes a
versioned `release-manifest.json` containing SHA-256 hashes, the target and
verified compiler source/product identities. Absolute input paths are not
written into the release manifest.

The packager fails closed unless `--build-record` names a
`docs/compiler_compatibility.json` record that verifies the current translator
sources, fresh Stage0 and Stage1 products, and a Stage1 bootstrap reproduced
from that Stage0. The record's target is used by default; `--target` can require
an exact target match. The destination must not exist, and the tool checks that
it does not overlap either support source tree. A completed directory can be
moved; the compiler-free packager regression moves a generated release and
invokes its packaged translator from the new location.

The repository currently has no project-level license file. Release assembly
therefore requires one or more explicit `--license NAME=PATH` arguments and
does not select a license. Supply the complete applicable license set for the
translator and packaged support sources before creating a distributable build.
The packager does not include or configure an Elisa compiler executable or
native Clang; Clang is needed to translate C/C++, and a compatible Elisa
compiler plus its matching runtime is needed to build generated Elisa.

Example after the compiler and license gates are satisfied:

```sh
python3 scripts/package_release.py \
  --version 0.1.0 \
  --translator build/elisa-c-transpiler \
  --cpp-lib-dir cpp_lib \
  --elisa-std-dir "$ELISA_STAGE1_STDLIB" \
  --build-record docs/compiler_compatibility.json \
  --clang-identity "$(clang --version | sed -n '1p')" \
  --license project=LICENSE \
  --output-dir dist/elisa-c-transpiler-0.1.0
```

The example is not runnable until the project license file and a fresh verified
compiler record exist. Exercise the assembly and relocation checks with:

```sh
python3 scripts/test_package_release.py
```
