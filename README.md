# Elisa C translator

This is a C-to-Elisa translator written in Elisa. Clang is used as the C
frontend and emits its semantic AST as JSON. The Elisa program parses that
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
- source-defined C variadic functions through Elisa `...`, `va_list`, and
  `llvm.va_start`/`llvm.va_end`
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

It is intentionally not a general C translator yet. Macros as source
constructs, full pointer arithmetic, `va_arg`, ownership/region inference,
and broader library/runtime coverage
still need work. C pointers are represented as nullable Elisa references at
the ABI boundary; the translator does not pretend that C ownership can be
inferred soundly from syntax alone.
C callback fields are emitted as nullable first-class function values, for
example `(fn(usize) -> mutable void&?)?`, and guarded calls remain typed.
C++ support comes after the C pipeline has a broader typed IR.

The current work covers the high-value, backend-compatible portion of the
translator improvement roadmap. The remaining deep items—full macro expansion,
complete pointer arithmetic, `va_arg`, precise ownership inference, broad
standard-library modeling, and large-unit compiler/backend capacity—are kept
explicitly conservative rather than emitted as misleading Elisa.

## Requirements

The current source imports the Elisa runtime and JSON modules from a sibling
checkout at `../Elisa-compiler`. It also requires `clang` and a working Elisa
compiler. The local test commands use the stage-0 compiler at
`~/.elisac/elisac`; set `ELISAC_BIN` to use another compiler.

## Test

From the repository root:

```sh
sh scripts/test.sh
```

The script builds the Elisa translator, translates the local fixtures, the
pinned `inih` example, cJSON, and Kilo, then compiles all generated programs.
It compares the executable fixtures with native behavior, checks constant
folding and dead-branch removal, C loop lowering, designated/sparse
initializers, switch ranges and enum patterns, const-preserving casts, direct
Elisa varargs lowering, source comments, formatter invariants, and
Clang-derived external bindings. It also checks that unsupported syntax
receives a source-qualified diagnostic and that a generic quality report has
no invalid-IR markers.

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

Each database entry retains its `directory` and `command`, so Clang sees the
same working directory, include paths, defines, and other frontend options as
the original build. Multiple direct input paths can also be supplied with
`--output-dir`; a single input keeps the original stdout mode. Use
`--idiomatic` (the default) for inferred mutability and localized unsafe
regions, or `--fidelity` to retain mutable C-style bindings and broad unsafe
regions.
