# ADR 0001: Separate C object immutability from pointer capabilities

## Status

Accepted

## Context

C uses `const` on objects, pointer slots, and pointees. Elisa bindings are
immutable by default, while `mutable` describes rebinding or writable access.
Those concepts cannot be translated correctly by copying the C spelling or by
using one boolean for an entire declarator.

## Decision

The translator lowers an ordinary C object declaration such as:

```c
const int answer = 42;
const int *p = &answer;
int *const fixed = &answer;
```

to the corresponding Elisa capability model:

```elisa
answer: i32 = 42
p: i32&? = answer
fixed: mutable i32&? = answer
```

The first binding is immutable. The second binding may be reassigned, but its
pointee is read-only. The third binding cannot be rebound, but its pointee is
writable when the source permits it. Pointer depth and qualifiers are retained
independently at each supported boundary. No C `const` token is emitted.

Dynamic or unsupported immutable-global initialization remains a diagnostic;
the translator does not weaken it into mutable zeroed storage merely to make
the target compile.

## Consequences

- Generated Elisa is idiomatic and uses the target language's default
  immutability model.
- Address exposure can still make the containing C object mutable when a
  writable pointee escapes.
- Full per-indirection qualifier recovery remains a compiler-contract item and
  must not be approximated silently.

## Evidence

`testdata/fixtures/const_bindings.c`, `const_aggregates.c`, the pointer
qualifier fixtures, and the isolated stage0/stage1 fixture suites cover scalar,
array, record, pointer-slot, pointee, and writable-address cases.
