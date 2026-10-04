# Wolf4SDL C++ requirements — first-pass source inventory

This is a preliminary source-level inventory for roadmap item C01, not a
complete Clang AST or runtime inventory. The upstream checkout is
`testdata/upstream/wolf4sdl` at commit
`a51c229ed89cab1904d68abb8938def3cf456725` from
`https://github.com/fabiangreffrath/wolf4sdl`. Its top level contains 27
`.cpp` files and one `.c` file, and 41,236 lines across C/C++ source and
headers. The default Makefile selects 25 `.cpp` files plus `opl3.c`; it does
not list `wl_dir3dspr.cpp` or `wl_shade.cpp`, whose build roles still need
investigation. The checkout is pinned locally, but its source tree is
gitignored and must not be edited as part of translator implementation.

## Build context

The Makefile compiles the `.c` unit with `-std=gnu99` and compiles the `.cpp`
units with the configured C++ compiler defaults. Both receive SDL2 and
SDL2_mixer compiler flags from `pkg-config`; the final link uses those SDL
libraries. A faithful Clang run must therefore use the selected C++ language
mode and the same target, defines, include paths and SDL flags as the real
build. This first pass did not run Clang over the project, because the shared
Stage1 seed lock was held and host memory was below the configured safe-build
floor.

## Confirmed standard-library surface

The source has two `std::unordered_map` objects, both declared in
`wl_def.h`/`id_in.h` or `wl_menu.cpp` and used across multiple translation
units:

| Object | Type | Observed operations | Translation implications |
| --- | --- | --- | --- |
| `Keyboard` (`id_in.cpp`, declared `id_in.h`) | `std::unordered_map<ScanCode, boolean>` where `ScanCode` aliases `int` and `boolean` aliases `int8_t` | `operator[]` for reads and writes; `clear()`; accessed through `IN_KeyDown` and `IN_ClearKey` macros | Bracket access must be an assignable lvalue and preserve C++ default insertion/value initialization for the exact signed 8-bit mapped type. The key uses integer hash/equality. Macro expansion and cross-translation-unit declarations must resolve to the same map object. |
| `ScanNames` (`wl_menu.cpp`) | `std::unordered_map<ScanCode, const char *>` | default construction; many `operator[]` assignments; `find()`, `end()`, iterator comparison and dereference | In addition to bracket insertion, the adapter needs a source-compatible iterator/end surface and must preserve the nullable pointer-to-constant-character mapped type. |

`wl_def.h` includes `<unordered_map>`; `id_in.h` declares the external
`Keyboard` object; `id_in.cpp` defines/clears it and performs bracket
reads/writes; `wl_menu.cpp` defines and populates `ScanNames` and uses
`find`/`end` plus iterator dereference in its scan-name lookup. These are
ordinary standard-library requirements. The translator must
select any adapter from Clang's resolved canonical template identity and emit
the generic `cpp` adapter; it must not special-case these Wolf4SDL names,
files, or call sites.

Existing generic regressions already cover integer and enum keys, scalar and
nullable `const char *` mapped values, bracket insertion, map growth, clear,
and `find`/`end`/iterator access in separate focused fixtures. They do not yet
combine Wolf's exact `int`/`int8_t` typedef specialization with the
cross-translation-unit global plus macro access pattern, nor do they exercise
`find`/iterator reads on the pointer-valued specialization. Those are the
smallest useful adapter-level additions before attempting the full project.

## C++-looking but C-style scope

The project is built from `.cpp` translation units and uses C++ headers and
types, but the confirmed map use is the main standard-library surface exposed
by this lightweight scan. The game code otherwise appears predominantly
procedural and C-like. That observation is not a claim that classes,
overloads, references, templates, initialization rules, or other C++ semantic
families are absent: headers, macro expansions, inactive configuration paths
and uncommon functions still need a compilation-database-backed Clang audit.

## Required next evidence

1. Reproduce the native compile context as normalized per-unit Clang arguments
   (prefer a generated compilation database); record target, C++ mode, defines,
   include paths, SDL headers/libraries and upstream revision.
2. Run the translator's Clang projection over every selected unit and report
   node kinds, canonical type families, declaration/linkage families, macro
   origins, calls/operators and global initialization. Retain per-unit counts
   and identify rare constructs as well as aggregate totals.
3. Extend the existing isolated generic C++ fixtures to cover both exact Wolf
   map specializations, including `Keyboard`-like signed 8-bit mapped values
   across translation units and macro-expanded reads/writes, plus pointer-map
   `find`/`end`/iterator reads. Compile, link and execute native and translated
   fixtures for parity before claiming this adapter surface complete.
4. Translate and compile the real units incrementally, using the exact Clang
   commands and reporting translator, Elisa compiler, SDL ABI/link and runtime
   failures separately. The interactive gameplay/data-file path is a later
   end-to-end acceptance gate, not a substitute for per-unit coverage.

This document advances C01's inventory but does not check off its Clang-node,
type, operation, runtime-use or rare-path acceptance requirements.
