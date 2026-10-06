# Translator-owned C++ library adapters

This document is the source-level contract for compatibility code under
`cpp_lib/`. An adapter is not a native C++ ABI implementation. Every support
claim is limited to the listed type and operation subset; implementation
presence alone does not establish semantic verification. Compiler-backed
status is tracked in `IMPLEMENTATION_PLAN.md` and `docs/execution_status.md`.

## `std::unordered_map`

The current adapter is emitted in Elisa module `cpp` and models a source
`std::unordered_map<K, V>` as `cpp::unordered_map[K, V]`. It is intended for
maps wholly inside translated code. Do not pass this Elisa representation
across a native C++ ABI boundary or reinterpret a native `std::unordered_map`
as this type.

| C++ operation | Current adapter behavior | Boundary |
|---|---|---|
| `map[key]` | Inserts a missing entry and returns its mapped-value place; reads and writes are lowered through the map's stable value slot. | Only the supported `K`/`V` types below. |
| `clear()` | Clears buckets and resets the per-map value arena. | Nontrivial mapped-value destructors are not modeled. |
| `size()`, `empty()` | Report the number of stored entries / whether it is zero. | No allocator or bucket-count API. |
| `contains(key)`, `count(key)` | Non-inserting key membership; `count` returns zero or one. | `contains` requires a C++ standard mode that provides it. |
| `erase(key)` | Removes the key and returns zero or one. | Iterator and range overloads are unsupported and must be diagnosed. |
| `find(key)`, `end()` | Mutable receivers produce `unordered_map_iterator`; immutable receivers produce read-only `unordered_map_const_iterator`. Both support end comparison and `first`/`second` reads; equality is overloaded in both directions for same-container mixed mutable/const iterators. | General iteration, increment, and full standard iterator semantics are not supported. |
| iterator `first` / `second` | Read the key and mapped value; translated assignment to `second` uses the adapter setter. | Address-taking and reference binding to these projections are rejected. |

The generated map template currently accepts exactly two template arguments;
custom hash, equality and allocator policies are rejected. Keys must be
integral or enum types supported by Elisa's dictionary equality/hash path.
Mapped values are limited to integer, floating-point and nullable object-pointer
types for which zero-initialization matches C++ value-initialization. Function
pointers, pointer keys, class-valued construction, and nontrivial destruction
are outside this contract.

The emitter recognizes only supported standard-library spellings and emits the
adapter dependency when generated Elisa actually refers to the adapter type.
Calls to unknown map member names are rejected. For `find`, `contains`, `count`
and key-based `erase`, the source now checks that the receiver's map key, the
call argument after Clang's implicit conversions, and the selected declaration's
single parameter (when that system-header declaration survived projection) have
the same normalized type. If the declaration is absent, the receiver/argument
type match remains mandatory. No-argument methods and unsupported arities are
checked separately; iterator and range `erase` remain rejected. Const
`find`/`end` calls route to a separate read-only iterator representation. These
latest checks have source-level regressions but still need a fresh translator
build and generated-Elisa compilation/runtime parity. The generic C++11 fixture
covers mixed mutable/const equality and inequality in both operand orders,
including both equal-element and found-versus-end cases; its native build and
execution pass.

### Storage, invalidation and complexity

The implementation separates dictionary buckets from arena-owned mapped-value
slots so bucket growth does not move a mapped object. Erased slots are linked
into a map-local free list; `clear()` resets the arena. This is the chosen
representation for C++'s mapped-reference stability across rehash, but the
current source revision's retention/reuse regressions have not yet been
revalidated with current Stage0/Stage1 compiler products. Do not treat that
intent as a verified guarantee until those tests pass.

The current dictionary/lifetime audit found these more specific properties:

- `dict` uses power-of-two open addressing, starts at eight buckets, and doubles
  capacity as needed. It grows before `(used + 1) / capacity` would exceed
  three-quarters; `used` includes tombstones, so removals can trigger a rehash.
  Probing is linear, deletion writes a tombstone, and `clear()` zeroes the
  existing table and resets its counters without shrinking it.
- Scalar integer, boolean, character and enum keys use the compiler's
  `ctx_hash_value` path (zero-extension to `u64`, then splitmix64); equality is
  Elisa `==`. For the currently admitted same-typed scalar keys, this preserves
  the required equal-keys-have-equal-hashes relation. It does not reproduce
  implementation-specific C++ bucket placement or iteration order; general
  iteration remains unsupported.
- The adapter's dictionary buckets are currently allocated through the global
  `perm_arena`, not through an arena owned by the map. Mapped-value slots use an
  embedded per-map `value_arena`; `clear()` calls `arena_reset`, which resets
  region cursors but retains the arena's allocated regions. The adapter defines
  no `__drop__` hook, so leaving a local map's scope does not release either
  arena's backing storage. Long-running code that repeatedly creates maps or
  forces growth can therefore retain memory until process teardown. This is a
  known semantic/resource gap, not an acceptable completed lifetime contract.
- Insertion uses `arena_dict_put_or_panic`. Elisa allocation failure therefore
  panics rather than propagating C++ `std::bad_alloc`; allocation-failure
  compatibility is not supported. Only trivial mapped values are accepted, so
  no C++ mapped-value destructor is currently invoked.

A cleanup fix must account for map moves: `dict` retains a reference to its
allocation `Arena`, and arena collection-stack bookkeeping is keyed to the owner
address. Replacing `perm_arena` with an inline self-owned arena without proving
that its address stays stable across every accepted map move can introduce a
dangling arena reference. In the inspected Stage1 source revision
`6b475d89`, destructor-hook discovery recognizes a concrete named receiver type,
not a generic `unordered_map[K, V]` receiver. A move-safe owner and generic or
translator-emitted destruction path must be designed and tested before
claiming that storage is released at map lifetime end.

Supported dictionary operations are expected to have the behavior of the
underlying Elisa dictionary. This adapter does not currently promise the full
C++ standard's complexity bounds, bucket policy, load-factor behavior, or
worst-case guarantees. `reserve`, `rehash`, `bucket_count`, `load_factor`,
`at`, insertion/emplacement APIs, and other unlisted operations are unsupported
and should fail with a source-located diagnostic rather than be approximated.

The adapter does not reproduce C++ exception types or exception propagation.
Operations that require exception-compatible behavior are unsupported; internal
invalid-iterator checks may panic in Elisa and are not a substitute for C++
undefined-behavior or exception semantics. Allocation-failure and full C++
construction/destruction behavior remain open.

### Corpus-driven adapter priority

The current upstream smoke suite selects C translation units from inih, Kilo,
and cJSON; those selected inputs do not require C++ standard-library adapters.
Wolf4SDL's default build is the first current C++ corpus target with an observed
standard-library dependency: its two `std::unordered_map` objects require
integer/int8 and integer/nullable-character-pointer specializations, including
bracket access and the `find`/`end` iterator path. The source-level Wolf
inventory and its limits are recorded in
[`wolf4sdl_cpp_requirements.md`](wolf4sdl_cpp_requirements.md).

The vendored inih release also contains an optional C++ `INIReader` wrapper,
but the current acceptance suite selects only `examples/ini_dump.c` with the C
library. A lexical scan of `inih/cpp/INIReader.{h,cpp}` finds
`std::string`, `std::map`, `std::vector`, `std::set`, `std::transform`,
`std::to_string`, and references; the example programs also use `std::cout`.
This is a useful independent future challenge, not evidence that those
adapters are currently required by the accepted inih path. Translating the
wrapper also depends on C++ class/member, reference, construction, and
destruction semantics, so it should follow those foundations rather than
triggering a string/container adapter in isolation. Re-run the inventory when
the accepted project set or its selected build inputs change.

### Required regression evidence

For each extension, add a generic fixture that compares native C++ behavior to
generated Elisa behavior, including the exact standard mode and target ABI.
Cover successful and missing-key operations, insertion/default initialization,
rehash stability, erase/reinsert/clear reuse, overload selection, and rejection
of unsupported policies. Keep fixture identifiers and source-project names out
of production translator rules.
