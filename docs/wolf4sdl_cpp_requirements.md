# Wolf4SDL C++ requirements — first-pass source inventory

This is a preliminary source-level inventory for roadmap item C01, not a
complete Clang AST or runtime inventory. The upstream checkout is
`testdata/upstream/wolf4sdl` at commit
`a51c229ed89cab1904d68abb8938def3cf456725` from
`https://github.com/fabiangreffrath/wolf4sdl`. Its top level contains 27
`.cpp` files and one `.c` file, and 41,236 lines across C/C++ source and
headers. The default Makefile selects 25 `.cpp` files plus `opl3.c` (26 units);
it does not list `wl_dir3dspr.cpp` or `wl_shade.cpp`, whose build roles still
need investigation. A compiler-independent provenance test now verifies the
Makefile's `SRCS` entries against all 28 tracked translation units and the two
default-build exclusions. The checkout is pinned as a Git submodule and must
not be edited as part of translator implementation.

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

A source-level include/token scan of the pinned checkout found no other active
C++ standard-library header or `std::` API beyond these map uses, and no
source-level class, template definition, namespace declaration, virtual
member, exception, or explicit `new`/`delete` construct in the default build
units. The sources do include C/POSIX headers and SDL headers, with some
platform-conditional headers (`io.h`, `direct.h`, `unistd.h`). This narrows the
initial Wolf adapter target, but it is only a lexical scan: it does not account
for macro-expanded constructs, every inactive configuration, compiler-inserted
AST nodes, or ABI behavior, and is not a complete C++ support claim.

Existing generic regressions already cover integer and enum keys, scalar and
nullable `const char *` mapped values, bracket insertion, map growth, clear,
and `find`/`end`/iterator access in separate focused fixtures. A new generic
two-unit regression now combines the `int`/`int8_t` specialization with an
external map global and macro-expanded bracket reads/writes, and reverses
compile-database order. A separate generic pointer-valued `find`/`end`/iterator
fixture now covers a missing key, a hit, key projection and nullable mapped
value reads. Both fixtures are wired to native/generated parity checks, but
their current-tree execution remains pending a safe compiler window.

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
3. Run the new cross-unit signed-8-bit/macro regression through native and
   translated compile/link/execution with both database orders; run the
   pointer-map `find`/`end`/iterator-read fixture with native/generated parity;
   then attempt full Wolf units incrementally.
4. Translate and compile the real units incrementally, using the exact Clang
   commands and reporting translator, Elisa compiler, SDL ABI/link and runtime
   failures separately. The interactive gameplay/data-file path is a later
   end-to-end acceptance gate, not a substitute for per-unit coverage.

This document advances C01's inventory but does not check off its Clang-node,
type, operation, runtime-use or rare-path acceptance requirements.
