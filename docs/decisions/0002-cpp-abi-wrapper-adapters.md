# ADR 0002: Use typed adapters for ambiguous C++ export aliases

## Status

Accepted

## Context

Project output exposes C/C++ definitions through Elisa `export fn` declarations
with native `@link_name` metadata. Elisa's alias form resolves its target by
source spelling and arity. A C++ overload set may contain several functions
with the same spelling and arity but different parameter types, so a direct
alias can bind every native wrapper to the first overload and produce invalid
LLVM call signatures.

## Decision

The translator detects ambiguous same-name/same-arity overloads structurally by
comparing lowered parameter types and mutability. Only those wrappers receive a
private, deterministic typed adapter:

```elisa
def __elisa_c_abi_adapter_choose__1__HASH(value: f32) -> i32:
    return choose(value)

@link_name("_Z6choosef")
export fn __c_abi_choose__1__abi_HASH(value: f32) -> i32 = __elisa_c_abi_adapter_choose__1__HASH
```

The adapter call is resolved using the exact Elisa parameter types. Unambiguous
C and C++ functions keep the compact direct alias form. No library or project
name is special-cased.

## Consequences

- The source-level overload names remain readable in translated definitions.
- Native ABI wrappers have unique targets and cannot collapse onto a different
  overload.
- Ambiguous wrappers add small private functions; this is preferable to
  globally renaming every overload or relying on backend overload heuristics.
- Overloads involving references, templates, operators, and member receivers
  still require their own semantic gates.

## Evidence

`testdata/fixtures/project_cpp_overloads` verifies four same-arity overloads,
reversed compilation-database order, native/generated exit parity, and the
absence of direct ambiguous export aliases.
