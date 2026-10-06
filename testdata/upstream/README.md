# Upstream corpus inventory

This file explains the translator's corpus inventory. The machine-readable
pins, required files, license identifiers, translation inputs, and native
command contexts are in [`corpus_manifest.json`](corpus_manifest.json), and
`scripts/test_upstream_provenance.py` validates them before the upstream suite
starts. It distinguishes upstream revision identity from a locally
reproducible vendored snapshot; a tree hash is not claimed to be an upstream
Git commit.

## Pinned sources

| Corpus | Upstream source | Pinned source identity | License in this snapshot |
|---|---|---|---|
| inih | <https://github.com/benhoyt/inih> | Release `r62`, upstream commit `26254ee9de7681f8825433415443e7116ff24b98`. Its root Git tree is exactly `33787047c04375515565b09f2bbf7f9116e96291`, also the vendored tree introduced by translator commit `dc4e1cc6ddcb81c421027a55a30ca912c77cc6b6` (2026-08-28). | BSD-3-Clause (`LICENSE.txt`, also identified by the SPDX tag in `ini.h`). |
| Kilo | <https://github.com/antirez/kilo> | Upstream commit `323d93b29bd89a2cb446de90c4ed4fea1764176e`; its root Git tree exactly matches vendored tree `a51e102d34c15cacb4ec931761a40d139cf2962a`, introduced by translator commit `dc4e1cc6ddcb81c421027a55a30ca912c77cc6b6` (2026-08-28). | BSD-2-Clause (`LICENSE`). |
| cJSON | <https://github.com/DaveGamble/cJSON> | Nested repository commit `c859b25da02955fef659d658b8f324b5cde87be3`, release 1.7.19 (2025-09-09). | MIT (`LICENSE`). |
| Wolf4SDL | <https://github.com/fabiangreffrath/wolf4sdl> | Nested repository commit `a51c229ed89cab1904d68abb8938def3cf456725` (2026-05-04). The committed tree has 60 files and 28 C/C++ source units; the default Makefile builds 26 (25 `.cpp` plus `opl3.c`) and omits `wl_dir3dspr.cpp` and `wl_shade.cpp`. | Wolf4SDL source: GPL-2.0 (`license-gpl.txt`). The separate `license-id.txt` governs original id Software material; it is not a license to redistribute user game data. |

The inih `r62` and Kilo upstream root-tree identities have both been verified
against their vendored tree object IDs. The translator-owned cJSON harness is
in the repository fixture tree at
`../fixtures/cjson_smoke.c`; it is not part of cJSON commit `c859b25`. cJSON
and Wolf4SDL are Git submodules pinned by the superproject. Initialize them
with `git submodule update --init --recursive`; cJSON is required by the
upstream suite, while Wolf4SDL remains exploratory. Any pre-existing local
untracked `.DS_Store` in the Wolf checkout is outside its pinned source commit.

## Native and generated smoke contexts

The reproducible small-corpus commands live in
[`../../scripts/test_suites/upstream_smoke.sh`](../../scripts/test_suites/upstream_smoke.sh)
and are run by `sh scripts/test.sh --suite upstream`. In summary:

| Corpus | Native compile/link context | Generated Elisa context and checked behavior |
|---|---|---|
| inih | `clang -std=c11 -DINI_USE_STACK=1`, with the vendored include and examples directories; link `ini_dump.c` with `ini.c`. | Translate `examples/ini_dump.c`, compile Elisa to an object with the selected local Elisa compiler at `-O0`, and link that object with the native `ini.o` plus `-lm`. Compare sample output, no-argument status/output/diagnostics, and missing-file status/output/diagnostics. |
| cJSON | `clang -std=c11 -I testdata/upstream/cJSON testdata/fixtures/cjson_smoke.c -lm`. | Translate the tracked smoke harness, compile generated Elisa at `-O0` when the selected compiler passes the nullable-function capability probe, link with `-lm`, and compare exact output. The capability skip is reported separately from translation. |
| Kilo | `clang -std=c11 testdata/upstream/kilo/kilo.c`. | Translate `kilo.c`, compile generated Elisa at `-O0`, link with `-lm`, then compare the no-argument exit status, stdout, and stderr. This is a startup/failure-path smoke, not an interactive terminal or editing test. |

These are macOS/Clang smoke commands, not a cross-platform support claim.
The compiler executable/runtime are selected by the test environment and
fingerprinted by `scripts/test.sh`; generated-object links use the matching
runtime when the selected Elisa compiler requires one.

## Wolf4SDL: known context and acceptance gap

The vendored Wolf4SDL Makefile's default native context uses
`pkg-config sdl2 SDL2_mixer`, `-std=gnu99` for its C source, and the host C++
compiler defaults for its C++ sources. It links all listed objects with the
SDL2/SDL2_mixer flags. `version.h` selects `GOODTIMES` and `CARMACIZED` in this
snapshot and enables `DEBUGKEYS`, `ARTSEXTERN`, `DEMOSEXTERN`, and
`PLAYDEMOLIKEORIGINAL`.

The exploratory compile database in
`../fixtures/wolf_wl_act1_compile_commands.json` is not a portable build recipe:
it names a separate user checkout at
`Documents/Coding Projects/Elisa Projects/elisa-wolf3d`, uses C++ GNU++11,
Homebrew SDL3_mixer headers and the Xcode macOS 26 arm64 SDK, and contains
vendor-specific Clang flags. It describes a syntax-only `wl_act1.cpp` job; it
does not provide a complete native link context for this vendored Wolf4SDL
revision. The unit-level `wl_menu.cpp` translation/object evidence in
`docs/execution_status.md` is likewise not full game acceptance.

To generate a local compilation database for the pinned SDL2 source tree,
install the SDL2 and SDL2_mixer development packages discoverable by
`pkg-config`, then run:

```sh
python3 scripts/wolf_compile_commands.py
```

The generator verifies the nested Git commit and Makefile source inventory,
asks the vendored Makefile for its forced dry-run compile commands, and writes
`build/wolf4sdl/compile_commands.json` plus a provenance sidecar with source and
configuration hashes, package versions, compiler versions/targets and the
database hash. It does not compile or link Wolf4SDL and does not access game
data. The database is host-local and intentionally ignored by Git; missing SDL2
packages are reported before a database is published. Pass it to the
translator with its normal `--compile-commands` option and the desired source
operands.

The manually supplied Wolfenstein data under ignored `build/` output is local
user material. It must remain outside this source corpus, version control,
release archives, and generic CI. A reproducible Wolf gate still needs a
portable native link recipe, a unit/dependency inventory tied to that build,
explicit local data-path configuration, and staged translation,
link, startup, and deterministic runtime checks.
