# Elisa C translator

This is a C and C-compatible-C++-to-Elisa translator written in Elisa. Clang
is used as the frontend and emits its semantic AST as JSON. The Elisa program parses that
JSON, lowers the supported C subset into a typed, index-based intermediate
representation, and writes Elisa source. Unsupported constructs are reported
with their Clang AST kind and source location.

The acceptance targets are the small `inih` C library's `ini_dump.c` example,
the pinned `antirez/kilo` text editor, and the pinned cJSON library's combined
parser/printer smoke program. The generated programs are checked against
native C behavior where practical. Kilo exercises a source-defined variadic
function, while cJSON exercises recursive records, allocator function
pointers, C strings, record-sized allocation, one-element array idioms, and
pointer-address comparisons.

## Current scope

The prototype currently covers the constructs needed by the acceptance target:

- function definitions, parameters, integer and string literals
- local and static arrays
- calls, arithmetic/comparison/assignment expressions
- array subscripting and a limited conditional expression
- `if`/`else`, declarations, returns, and compound statements
- loops, `switch`, `break`/`continue`, and ordinary labels/gotos
- structs, enums, partial typedef recovery, scalar/pointer type lowering, and
  reserved-name avoidance
- record and array `sizeof` lowering through Elisa's `size_of[...]`
- enum `sizeof` uses Clang's collected backing/storage type, including
  bool-backed C++ enums
- C `-fshort-enums` compilation-database options preserve selected 8-/16-bit
  enum storage and the resulting record layout
- source-defined C variadic functions through Elisa `...`, `va_list`, and
  `llvm.va_start`/`llvm.va_end`, with typed `va_arg[T](...)` and `va_copy`
  lowering
- selected compiler builtins such as `__builtin_object_size`, lowered from
  object provenance and mode semantics rather than as guessed external calls
- Clang-derived external function and global declarations
- flow-sensitive null facts for names, fields, and indexed pointer slots, with
  invalidation after writes and opaque calls
- inferred local/parameter/field mutability, C integer promotions, boolean
  recovery, enum qualification, constant-condition cleanup, and complete
  zero-filled aggregate initializers
- integer constant folding, canonical C `NULL` handling, ABI-aware cast
  elision, const-preserving explicit casts, direct function decay, and readable
  source-derived temporary names
- idiomatic C `for`/`do`-`while` lowering, designated initializers, sparse array
  initializers, dense switch ranges, and symbolic enum switch patterns
- generic C floating builtins (`__builtin_nan*`, `__builtin_inf*`, and
  `__builtin_huge_val*`) plus IEEE-correct unordered floating `!=`
- a final output formatter that removes trailing whitespace and normalizes
  generated module boundaries, preserves literal/comment whitespace, and wraps
  long nested signatures and expressions
- localized `trusted Unsafe.StaleRef` regions in idiomatic mode, with a
  `--fidelity` mode for broad source-faithful unsafe regions
- typed non-null local function-pointer calls, source comments on translated
  declarations, demand-driven runtime helpers, and collision-safe project
  module names
- source-qualified, de-duplicated diagnostics for unsupported constructs
- a generic quality report for line count, cast/assertion pressure, unsafe
  markers, synthetic names, and invalid-IR regressions
- branch-local non-null reuse for named pointers, collapsed nested trusted
  regions, identity cleanup for C `sizeof` expressions, and no-op block removal
- C++-extension source files that remain within the supported C subset; direct
  `.cc`, `.cpp`, `.cxx`, and `.C` inputs select `clang++` automatically

For each translation, the frontend also queries predefined macros from the
same normalized Clang command and carries the resulting scalar ABI facts into
lowering. The currently supported scalar model requires 8-bit bytes, a
32-bit `int`, and a pointer width matching the Elisa compiler target; it
handles 8/16/32/64-bit integer types, target-specific plain
`char` signedness, `long`, and the Clang-provided `size_t` type. This correctly
distinguishes LP64 from LLP64 (for example, Windows `long` is 32-bit while
`size_t` can remain 64-bit). If Clang cannot provide a supported scalar ABI,
the command-line translator fails closed with the observed target macros;
this is not yet a complete target data-layout model for records, bit-fields,
address spaces, or calling conventions.

The translator also owns a small, demand-driven C++ compatibility library under
`cpp_lib/`. When Clang reports a supported `std::unordered_map<K, V>` spelling,
the generated Elisa unit includes `cpp_lib/unordered_map.elisa` and lowers the
type to the generic `cpp::unordered_map[K, V]`. The verified subset supports
integer or enum keys and integer, floating-point, or nullable object-pointer
mapped values. Its current operations include `operator[]`, `clear`, `size`,
`empty`, `contains`, `count`, key-based `erase`, and `find`/`end`. Iterator
`first` and `second` projections are by value; writes to `second` are lowered
through the adapter. Address-taking and C++ reference binding to these
projections are rejected because the current dictionary-backed representation
does not provide those references. Additional hash/equality/allocator template
arguments are rejected rather than silently ignored, as are unsupported key
hashing and mapped-value initialization cases. This adapter is intentionally
generic and is not a cJSON- or Wolf4SDL-specific table. The Elisa compiler
provides only the language-level `Index` protocol and backend support for `[]`;
the C++ library emulation does not belong in `Elisa-compiler/elisacore_std`.

In project mode, translation-unit modules and the manifest are generated under
transaction-specific temporary names. The manifest is published last, and
failed translation or publication removes only that transaction's files while
preserving the previous generation. The default compatibility-library include
keeps the repository-local workflow short. For generated projects that must
move independently, provide both support roots explicitly:

```sh
./build/elisa-c-transpiler \
  --cpp-lib-dir /path/to/elisa-transpiler/cpp_lib \
  --elisa-std-dir /path/to/elisa-compiler/elisacore_std \
  --compile-commands build/compile_commands.json \
  --output-dir build/elisa-project
```

This emits direct includes for the selected runtime, collections and
translator-owned compatibility core. The generated Elisa files can then be
moved together and compiled without the translator's build-directory-relative
wrapper; the selected support roots remain explicit external dependencies.

Switches are lowered to Elisa `match` statements. Adjacent C labels that share
an arm become Elisa or-patterns such as `0 | 1:`; three or more consecutive
integer labels can become a range such as `10..=12:`, and enum labels retain
their qualified names when Clang proves the switch expression is that enum.
Ordinary terminal `break` statements disappear because the arm naturally ends
there, and a synthetic completion flag is retained only for conditional breaks
whose fall-through path still has code to suppress.

## External C functions

The translator has no built-in table for `printf`, `memset`, `read`, or any
other target C function. When a call is encountered, its declaration is looked
up in Clang's AST; the return type, parameter types, mutability, and variadic
shape are emitted from that declaration. The generated Elisa declaration
retains the source name and preserves the original linker spelling with
`@link_name("...")`. Reserved words are mapped through the normal identifier
sanitizer, and a collision-safe fallback is used only when a source name cannot
be represented directly.

The same rule is used for referenced external variables, which are emitted as
source-named declarations. Pointer values are nullable where Elisa can
represent the C pointer shape; translated C functions are explicitly marked as
unsafe ABI boundaries because C does not provide Elisa's ownership guarantees.
In project mode, a file-scope `extern` object with an initializer is treated as
a definition and emitted as a global; duplicate initialized external definitions
are rejected before a project manifest is published.
Same-arity C++ overloads exposed across project units receive small private
typed adapters when Elisa's export-alias target would otherwise be ambiguous;
unambiguous C and C++ wrappers retain the compact direct alias form. The
adapter decision is based on lowered signatures, never on a library name.
For nested C pointers, cast cleanup preserves qualifier differences at each
indirection, and wholly read-only chains remain immutable. Elisa currently has
only one mutability capability for an entire reference chain, so mixed
read-only/writable layers can still be broader than the source C type.

Functions containing a C `goto` are lowered through a control-flow graph. The
translator emits Elisa basic blocks selected by a mutable program-counter loop,
so forward, backward, and cross-nested jumps do not require adding a `goto`
construct to Elisa itself. Locals in those functions are hoisted to the
function entry and their initializers remain in their original CFG blocks. The
dispatcher variable is named `control_state` unless that conflicts with a
source symbol, in which case a readable fallback is selected.

Lowering is deliberately fail-closed: a construct outside this subset stops
translation with a diagnostic instead of being replaced by a placeholder.

The translator is generic; cJSON and Kilo are regression targets, not special
cases in the emitter.

Non-null assertions are generic too. The prelude emits a mutable
`elisa_nonnull[T]` only when a writable view is required, and a separate
`elisa_nonnull_readonly[T]` only when a `const` C view needs narrowing. Neither
helper has knowledge of cJSON, Kilo, or any other target program.

C `const` object qualification follows Elisa's default immutability model: a
scalar, array, or record declared `const` in C is emitted as an ordinary Elisa
binding, without a generated `const` keyword or a source-specific helper.
Pointer qualification is handled at the capability boundary instead. A
`const T *` becomes a read-only `T&?`, while a `T * const` keeps a writable
`mutable T&?` pointee view; the Elisa binding itself remains ordinary and
therefore cannot be rebound. This separates C's binding qualifier from its
pointee qualifier without inventing a second const system in Elisa.

It is intentionally not a general C translator yet. Macros as source
constructs, full pointer arithmetic, aggregate variadic extraction and complete
variadic lifetime/ABI rules, ownership/region inference, and broader
library/runtime coverage still need work. Floating formats beyond the supported
target scalar model, long-double fidelity, fast-math policy, and signaling-NaN
payload preservation remain open. C pointers are represented as nullable Elisa references at
the ABI boundary; the translator does not pretend that C ownership can be
inferred soundly from syntax alone.
C callback fields are emitted as nullable first-class function values, for
example `(fn(usize) -> mutable void&?)?`, and guarded calls remain typed.
C++ syntax outside the C-compatible subset—such as classes, most templates, and
standard-library containers other than the translator-owned compatibility
adapters—still receives a diagnostic rather than a source-specific workaround.

The current work covers the high-value, backend-compatible portion of the
translator improvement roadmap. The remaining deep items—full macro expansion,
complete pointer arithmetic, aggregate variadic extraction and complete
variadic ABI/lifetime modeling, precise ownership inference, broad
standard-library modeling, bounded AST projection for header-heavy units, and
large-unit compiler/backend capacity—are kept
explicitly conservative rather than emitted as misleading Elisa.

Wolf4SDL is the next exploratory corpus. Its implementation is predominantly
procedural C-style code, although most files use a `.cpp` extension and a few
translation units use genuine C++ containers. The source is kept separate from
the acceptance suite while the translator's large-header translation-unit
handling is improved.

## Requirements

The repository uses isolated local compiler worktrees so its tests do not race
with or overwrite an installed `elisac`. Run
`scripts/setup_local_compilers.sh` once to create sibling worktrees at
`../elisa-transpiler-worktrees/stage0-latest` and
`../elisa-transpiler-worktrees/transpiler` (the stage-1 compiler checkout),
build the local stage-0 compiler, seed the local stage-1 compiler, and build
its runtime object. The default test commands use those local binaries. Setup
also creates the ignored `src/.compiler_std` link to that stage-1 worktree's
standard library; this keeps source includes independent of the worktree's
location. Set `ELISA_TRANSLATOR_COMPILER_WORKTREES`, `ELISA_STAGE0_WORKTREE`,
`ELISA_STAGE1_WORKTREE`, or `ELISA_STAGE1_STDLIB` to select another isolated
layout. A pre-existing conflicting `src/.compiler_std` path is left untouched
and reported as an error. Set `ELISAC_BIN` only when deliberately testing a
different compiler.

## Compiler freshness

`docs/compiler_compatibility.json` is the authoritative compiler-pair record.
Its 2026-10-05 snapshot has isolated Stage0 and Stage1 sources at
`11858f2e` and `2691a64c`, while the local Stage0 executable and Stage1
executable/runtime are from older revisions; translator validation is pending.
Historical test results therefore do not verify the current translator source
against that refreshed compiler pair. Rebuild the local products and rerun the
focused and serial acceptance suites before making that claim. The snapshot
also records the private Stage1 worktree as dirty because of a modified
tracked `.DS_Store`; preserve and inspect that unrelated change rather than
silently reverting it.

## Test

From the repository root:

```sh
sh scripts/test.sh
```

The translator's object build and final link run in separate owned POSIX
process groups. Each is limited to 2 GiB aggregate resident memory and a
10-minute deadline by default; override these for a larger host with
`ELISA_TRANSLATOR_BUILD_MAX_RSS_KB` and
`ELISA_TRANSLATOR_BUILD_TIMEOUT_SECONDS`. The test driver reports the measured
process-group peak and terminates only the group it launched if a limit is
exceeded. Direct translator, Elisa compiler, Clang and Clang++ invocations in
the sourced suites are also run with per-tool process-group RSS and deadline
limits. Compiler-bearing Python integration probes run as bounded process
groups, covering the harness and its nested compiler processes together. These
limits are configurable with `ELISA_TEST_TRANSLATOR_*`, `ELISA_TEST_ELISA_*`,
`ELISA_TEST_NATIVE_*`, and `ELISA_TEST_PYTHON_PROBE_*` settings. On macOS the
canonical test driver defaults to requiring more than 60% host free memory
before launching each bounded stage and stops its owned group if memory falls
to that floor; override the floor with `ELISA_SETUP_MIN_SYSTEM_FREE_PERCENT`.
Successful per-command telemetry stays off captured compiler output so
diagnostics and typed-IR fixtures remain deterministic; failures and limit
breaches retain resource details. These are process-group bounds, not a cap on
the operating system's total memory use.

Focused checks are available with `--suite fixtures`, `--suite projects`,
`--suite control-flow`, or `--suite upstream`. Add `--reuse-build` to reuse
the translator executable only when hashes of its Elisa sources, required
standard-library inputs, compiler and Clang still match the recorded build;
the selected tests themselves always run.

The script first runs bounded self-tests for the build cache, manifest runner,
and selected-compiler standard-library link. The cache tests reject stale source fingerprints, modified
executables, and non-executable outputs. Manifest tests cover argv execution,
separate stdout/stderr capture, expected nonzero exits, mismatches,
timeouts/process-tree cleanup, crashes, skips, unsupported translations,
missing tools, and invalid manifests. A fixture manifest then
drives native-vs-Elisa checks for representative C, C++-compatible, and
readonly-pointer-helper programs. It builds the Elisa translator and runs four
sourced suites: focused C/C++ fixtures, project-generation checks, control-flow
checks, and upstream smoke programs. The local `inih` example is compared with native behavior; generated
Kilo is compiled and its no-argument behavior is compared; cJSON translation
and structural checks always run, while its compile/runtime comparison is
conditional on the local Elisa compiler supporting nullable function fields.
Generated programs supported by the selected compiler are compiled and run.
The suite checks constant folding and dead-branch removal, C loop lowering, designated/sparse
initializers, switch ranges and enum patterns, const-preserving casts, direct
Elisa varargs lowering, source comments, formatter invariants, and
Clang-derived external bindings. It also checks that unsupported syntax
receives a source-qualified diagnostic and that a generic quality report has
no invalid-IR markers.

Before the corpus suites, a bounded metamorphic check translates a
semantics-neutral identifier rename and verifies identical normalized Elisa;
it also verifies that truncated C fails without partial output.

Pass `--diagnostics-json` to emit deterministic machine-readable translation
diagnostics on stderr. Schema version 3 records include the semantic category
and Clang node kind, the rejected node's Clang type when available, an explicit
`required_capability` for specific unsupported features, source and canonical
paths, half-open source byte ranges, primary coordinates, and any available
macro spelling/expansion origins.
Unavailable type/capability values are empty strings; generic unsupported
constructs are categorized by their Clang AST kind (expression, statement,
declaration, or frontend) and do not claim a specific missing capability.
Human-readable diagnostics remain the default and include type/capability
context when known.

Pass `--source-map-json PATH` to write an opt-in source-map file for a
single-file translation or a project. Generated offsets address UTF-8 Elisa output bytes;
source ranges use zero-based half-open byte offsets. Each mapping retains the
primary, macro-spelling and macro-expansion origins, immediate include edges,
and any synthesized-node reason. The `sources` table includes each translation
unit even if it has no emitted origins, plus deterministic FNV-1a-64 content
hashes for readable physical files (useful for cache invalidation, not
cryptographic verification). With `--output-dir`, PATH must
be inside that directory; the resulting JSON contains one map per translated
unit and is published transactionally with the modules and project manifest.
Symlinks resolving to an input, generated module or project manifest are
rejected as output collisions.
Source-map capture is disabled by default.

To inspect readability metrics for any translated C file:

```sh
./scripts/quality_report.sh testdata/upstream/cJSON/cjson_smoke.c \
  build/cjson.quality.elisa
```

The report is source-agnostic and can be used as a baseline when adding new
corpus programs.

The normal tests use the stage-0 Elisa compiler. The translator source itself
can also be checked with the stage-1 compiler, but the current stage-1 backend
may decline a large translation unit after semantic analysis. That is a
compiler capacity/sound-subset boundary, not a successful translation: no
linkable object is produced in that case. The acceptance suite remains the
authoritative end-to-end check until stage-1 can compile the emitter as a whole.

The upstream test source is vendored under
`testdata/upstream/inih` at commit `26254ee` (release `r62`).
The cJSON source is vendored under `testdata/upstream/cJSON` at tag `v1.7.19`.

## Project translation

For a compilation database, project mode emits one Elisa module per C source and
an `elisa_project.elisa` manifest containing the shared runtime prelude:

```sh
./build/elisa-c-transpiler \
  --compile-commands build/compile_commands.json \
  --output-dir build/elisa-project
```

Per-unit C++ mode follows Clang's effective command-line configuration (including
`-x` overrides). Supported non-inline namespace-scope const object types with
internal linkage receive translation-unit-private names; a prior explicit
`extern` declaration keeps a later const definition externally linked. Complex
const-qualified function-pointer declarators and inline-variable ODR checks
remain unsupported.

Each database entry retains its `directory`. An `arguments` array stays as
structured argv and runs directly through `execvp` without shell interpretation;
the translator copies JSON string slices into stable NUL-terminated argument
storage and applies the entry's working directory in the child. AST stdout,
stderr and exit status are captured independently, and the byte cap is enforced
while stdout is streamed. Ordinary `command` strings are tokenized into argv
and use that same direct process runner. The accepted subset preserves
single/double quotes and backslash escapes, and supports leading `NAME=value`
environment assignments via `env`; it is not a general shell parser. Expansion,
redirection, pipelines, globbing, command substitution, and control operators
are rejected before launch. The command-string decoder and process runner
currently target POSIX hosts (Darwin is tested); Windows command-line decoding
and process launching are unsupported. The first argv word is executed directly
through `execvp`: explicit launchers such as `env`, `ccache`, or `distcc` are
preserved as argv and must be installed and forward the appended Clang options.
No wrapper chain is inferred or executed through a shell. Prefer `arguments`
arrays when the build system provides them. Exact duplicate entries for the
same canonical source and working directory are translated once; filesystem
aliases that resolve to an existing
source share that identity, while entries with differing settings are rejected
before project files are written. Unresolved paths retain a lexical fallback.
`command` and `arguments` forms are compared after response expansion and
output/dependency-flag normalization; their working directories remain
significant. Explicit Clang `@file`
arguments are expanded before normalization in both database forms. Relative
and nested response-file paths resolve from the entry's working directory;
response contents use the same restricted POSIX-like quoting and escaping
rules, with no shell expansion. Empty files are accepted, while missing,
unreadable, cyclic/deep, over-budget, or over-argument inputs fail closed with
the offending response-file path and source in the diagnostic. Malformed
response-file quoting is likewise reported before Clang launches.
Expansion is limited to 16 nested files and 1,000,000 argv words; cumulative
response-file bytes share the `--max-frontend-output-bytes` budget. Response
files are not yet included in dependency-aware cache invalidation. Known
build-output and dependency-generation options are removed before AST
extraction, while semantic options such as standards, targets, defines and
include paths are retained. Direct-file mode selects C11 or GNU C++11 by
extension and does not inject feature-test macros or disable fortify.
Compilation-database `-x` and `-std` settings take precedence over the source
suffix; direct-file mode currently has no explicit language/standard override
option. Multiple direct input paths can also be supplied with `--output-dir`; a
single input keeps the original stdout mode. Clang AST source locations are
matched to compilation-database paths by filesystem identity, including when a
response file names a relative source and the database entry names it
absolutely. Matching locations are normalized in the projected AST so later
translation stages retain those declarations. The projector resolves the main
source's physical identity once and reuses it for location checks; only exact
main-file matches are rewritten to the selected source spelling, while
same-directory headers retain their own origins. Canonical identity also drives
duplicate-source detection. After response expansion and option normalization,
the effective source operand is checked against the database `file`; a mismatch
or omitted source is rejected before project output is written. Canonical
physical identity in diagnostic/origin records, separate macro spelling and
expansion locations, and response-file cache invalidation remain open. Use
`--idiomatic` (the default) for inferred mutability, localized unsafe regions,
and verified readability rewrites, or `--fidelity` to retain mutable C-style
bindings, broad unsafe regions, and source-level expression structure where
the rewrite is optional.

Frontend subprocess output is capped at 128 MiB by default. Set
`--max-frontend-output-bytes N` to another positive byte limit; the cap applies
to Clang AST output, compilation-database contents, and cumulative response
file contents. When source-map output is enabled, the same limit separately
bounds JSON output and cumulative origin-file bytes hashed across the
translation units (physical aliases are deduplicated within each unit). An
exceeded limit fails without publishing partial output.
This limits captured output, not the
translator's total memory use: JSON projection and parsing may expand the
representation. Clang AST output is streamed to an auto-deleted temporary file
and mapped read-only during projection, avoiding a second full-size heap buffer;
this requires temporary storage up to the configured cap and is not a total RSS
bound. Raw Clang JSON is syntax-checked before projection so malformed or
truncated fields cannot be hidden by filtering. The raw root is also checked
against the supported schema: it must be a `TranslationUnitDecl` object with an
array-valued `inner` field. Schema failures report the source and the violated
root field before projection; optional nested Clang fields remain version-
tolerant. The projected AST is also
limited to 1,000,000 JSON values by default; set
`--max-frontend-json-values N` to another positive limit. The translator counts
values before constructing its JSON DOM, so an oversized AST is rejected
before those arena allocations. These limits do not constitute a total
process-tree RSS bound. Pass `--frontend-stats` to report raw and
projected AST JSON byte counts, JSON-arena payload bytes, and projected JSON
value count to stderr for each input; object member names are not counted as
values. Pass `--explain-rewrites` to report applied idiomatic typed-IR
readability rewrites with proof tags and source ranges, plus declined rewrite
candidates with reasons, to stderr without changing generated stdout.

Each Clang frontend child has a 600-second monotonic deadline by default,
including target-macro queries and AST extraction. Set
`--frontend-timeout-seconds N` to a positive value up to 86,400 seconds. When
the deadline expires, the translator terminates and reaps the dedicated Clang
process group, emits a source-qualified diagnostic, and does not publish partial
Elisa. This bounds each frontend child invocation, not total project time across
multiple source files.
