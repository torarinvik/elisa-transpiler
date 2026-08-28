# Elisa C translator

This is a C-to-Elisa translator written in Elisa. Clang is used as the C
frontend and emits its semantic AST as JSON. The Elisa program parses that
JSON, lowers the supported C subset into a typed, index-based intermediate
representation, and writes Elisa source. Unsupported constructs are reported
with their Clang AST kind and source location.

The first acceptance target is the small `inih` C library's `ini_dump.c`
example. The generated Elisa program is linked with the original native `ini.c`
library so the translator can be checked against the original executable's
behavior. The pinned `antirez/kilo` text editor is also translated completely,
including its source-defined variadic status-message function, and linked
without a C adapter.

## Current scope

The prototype currently covers the constructs needed by the acceptance target:

- function definitions, parameters, integer and string literals
- local and static arrays
- calls, arithmetic/comparison/assignment expressions
- array subscripting and a limited conditional expression
- `if`/`else`, declarations, returns, and compound statements
- loops, `switch`, `break`/`continue`, and basic labels/gotos
- structs, enums, scalar/pointer type lowering, and reserved-name avoidance
- source-defined C variadic functions through Elisa `...`, `va_list`, and
  `llvm.va_start`/`llvm.va_end`
- Clang-derived external function and global declarations

## External C functions

The translator has no built-in table for `printf`, `memset`, `read`, or any
other target C function. When a call is encountered, its declaration is looked
up in Clang's AST; the return type, parameter types, mutability, and variadic
shape are emitted from that declaration. The generated Elisa declaration uses
an opaque name such as `__c_ext_3` and preserves the original linker spelling
with `@link_name("...")`. This keeps the translator generic and prevents C
library names from colliding with Elisa/runtime functions.

The same rule is used for referenced external variables, which are emitted as
opaque `__c_global_N` aliases. Pointer values are nullable where Elisa can
represent the C pointer shape; translated C functions are explicitly marked as
unsafe ABI boundaries because C does not provide Elisa's ownership guarantees.

Lowering is deliberately fail-closed: a construct outside this subset stops
translation with a diagnostic instead of being replaced by a placeholder.

It is intentionally not a general C translator yet. Typedef recovery, macros
as source constructs, full pointer arithmetic, function pointers, `va_arg`,
and broader library/runtime coverage still need work.
C++ support comes after the C pipeline has a broader typed IR.

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

The script builds the Elisa translator, translates the small local fixture,
the pinned `inih` example, and Kilo, then compiles all generated programs. It
compares `ini_dump` with native behavior and verifies Kilo's no-argument path,
including direct Elisa varargs lowering with no adapter. It also verifies that
library bindings are Clang-derived opaque aliases and checks that unsupported
syntax receives a source-located diagnostic.

The upstream test source is vendored under
`testdata/upstream/inih` at commit `26254ee` (release `r62`).
