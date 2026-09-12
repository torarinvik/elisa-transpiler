# Elisa C/C++ to idiomatic Elisa: implementation plan

> Scope corrected on 2026-09-12. This document is the roadmap for **this Elisa transpiler repository**. The product goal is to translate C and C++ into correct, readable, maintainable, idiomatic Elisa. It replaces the unrelated language-server plan previously written here.

## 1. Objective and governing requirements

Build a translator written in Elisa that uses Clang for C/C++ parsing and semantic interpretation, preserves the observable behavior of supported source programs, and recovers the clearest Elisa representation justified by the available semantic evidence.

The translator should progressively support ordinary C, C-style C++, and then broader C++. cJSON, Kilo, inih and Wolf4SDL are regression corpora. Their names, function names, directory layouts and private data must never determine generic translation rules.

The final product has two complementary output policies:

- **Idiomatic mode:** the default; recover structured control flow, narrow mutability, meaningful names, direct typed calls, useful aggregates, modules and safe language constructs where equivalence is established.
- **Fidelity mode:** preserve source structure and low-level operations more closely for diagnosis and comparison. It shares the same semantic correctness requirements as idiomatic mode.

Neither policy may erase essential casts, aliasing, nullability, integer conversions, cleanup or side effects to improve a readability score. Unsupported semantics must produce an actionable diagnostic during staged implementation. A refusal is honest intermediate behavior, not completion of a planned support feature.

### 1.1 Requirements retained from this project

1. Implement translator logic and translator-owned compatibility libraries in Elisa. Shell/test drivers and a narrowly scoped Clang API binding may assist; do not move translation policy into a separate C++ or Python translator.
2. Obtain external declarations such as printf, allocation routines and SDL functions from Clang declarations and ABI metadata. Do not maintain handwritten target-function signature tables.
3. Keep C++ library adaptation in this repository's `cpp_lib/`, under module `cpp`. Use ordinary Elisa overloads, uniform call syntax and indexing protocols.
4. Preserve user variable/function names wherever Elisa syntax and binding identity permit. Generated state variables are compiler artifacts, not recovered source variable names.
5. Eliminate avoidable control-state dispatch through structural analysis; retain a correct localized fallback for control flow that cannot yet be restructured.
6. Prefer generic helpers to one helper per concrete type; preserve const/mutable distinctions that affect type safety.
7. Prefer native Elisa slice notation over explicit sview construction only after proving the compiler's actual endpoint, sentinel and lifetime semantics.
8. Use isolated stage0/stage1 compiler worktrees and explicit local binaries. Record updates from the main compiler checkouts and preserve local fixes.
9. Keep translator implementation source files at or below 600 lines with coherent module boundaries and namespace hygiene.
10. Commit completed, verified implementation slices steadily. Include only changes owned by the slice; record required compiler commits separately.
11. Keep heavy builds and corpus checks within measured memory limits, beginning with one heavy process at a time.
12. Report missing Elisa language/compiler features with minimized examples and explicit integration gates.

### 1.2 What success means

A successful translation is more than parseable output: it must lower without unresolved semantic placeholders, compile with the selected local Elisa compiler, link with the intended ABI/runtime, and pass behavior checks appropriate to the source program. Idiomatic quality is assessed only after those requirements.

The long-term scope includes the C and C++ feature work listed below. Publish a precise support matrix for each release and advance it through verified milestones. Do not label a C-style C++ subset as complete C++ support, or declare the whole roadmap complete because its first corpus compiles.

## 2. Current repository baseline

This baseline comes from source and script inspection in this repository. This planning turn has not rebuilt or retested the translator; existing code and test names indicate coverage intent, not fresh passing results.

| Existing area | Files | Current foundation / remaining audit |
|---|---|---|
| Entry and CLI | `src/main.elisa`, `src/cli.elisa` | Direct input, compilation database and project output modes exist |
| Clang acquisition and projection | `src/clang_ast.elisa`, `src/clang_ast_filter.elisa` | JSON AST capture and compaction exist; process status, argument handling and peak memory need stronger contracts |
| AST/type collection | `src/clang_context.elisa`, `src/clang_typedefs.elisa`, `src/clang_ast_initializers.elisa` | Declaration lookup, typedef recovery and aggregate handling exist |
| Typed lowering | `src/lower_expr.elisa`, `src/lower_stmt.elisa` | Typed index-based IR and source-qualified unsupported diagnostics exist |
| Scalar/type semantics | `src/c_semantics.elisa`, `src/emit_types.elisa`, `src/emit_types_records.elisa` | Promotions, pointers, arrays, records and ABI-related handling exist |
| Facts and effects | `src/emit_analysis.elisa`, `src/emit_expr_facts.elisa`, `src/emit_effects.elisa`, `src/emit_places.elisa` | Null facts, mutability, places and unsafe-region reduction exist |
| Expressions and calls | `src/emit_expr.elisa`, `src/emit_expr_calls.elisa`, `src/emit_expr_support.elisa` | Cast cleanup, typed callbacks and generic foreign declarations exist |
| Control flow and output | `src/emit_cfg.elisa`, `src/emit_program.elisa`, `src/emit_statements.elisa` | Structured constructs plus CFG dispatch fallback exist |
| Formatting and metrics | `src/emit_format.elisa`, `src/emit_quality.elisa`, `scripts/quality_report.sh` | Output cleanup and source-agnostic text metrics exist |
| C++ compatibility | `src/cpp_compat.elisa`, `cpp_lib/unordered_map.elisa` | Initial map type adaptation and bracket/clear/size operations exist |
| Build and tests | `scripts/setup_local_compilers.sh`, `scripts/test.sh`, `testdata/` | Local compiler worktrees and native-versus-generated fixture checks exist |
| Corpora | `testdata/upstream/{inih,kilo,cJSON,wolf4sdl}` | Small C acceptance targets and exploratory Wolf source are present |

Specific findings to address without assuming the older README is a complete feature inventory:

- `run_clang_ast` captures the full JSON byte stream before compaction; reducing parsed JSON size does not by itself bound Clang output memory.
- `run_command_output` currently discards pclose status; project invocation appends frontend options to a command string.
- `cli_compile_command` normalizes an arguments array back into shell command text; preserve argv structurally in the next frontend driver.
- `cpp_unordered_map_bounds` currently recognizes type spelling, including an unqualified name; recognition should use canonical declaration identity and resolved template arguments.
- The current map adapter inserts `zeroed`; general C++ mapped-value construction requires real default/value initialization and lifetime semantics.
- `cpp_lib/unordered_map.elisa` and the main entry contain relative compiler-worktree includes, and compatibility output assumes a normal build-directory layout.
- Generated project module filenames have occurrence-based collision handling, while initializer names derive separately from basenames; naming must share one project symbol registry.
- Eight translator source files currently exceed 600 lines: clang_ast, clang_ast_filter, emit_cfg, emit_expr, emit_program, emit_types, emit_types_records and lower_expr. Split these and enforce the same limit for successor modules.
- The 654-line test script mixes building, structural assertions, linking and runtime comparisons. Split its responsibilities while retaining one documented entry point.

Use status values `not-audited`, `present-unverified`, `partial`, `verified`, `blocked` and `deferred`. An unchecked task below is a remaining implementation or verification obligation; first preserve and prove any existing implementation.

## 3. Architecture and semantic contracts

### 3.1 Target pipeline

`CLI/project configuration → Clang invocation → bounded semantic projection → canonical typed source IR → verified semantic analyses → structured Elisa IR → deterministic source writer → compile/link/differential validation`

Maintain a faithful typed source representation separately from target-language idiom recovery. Passes should query semantic records rather than infer language facts from already-rendered text.

Proposed module families, introduced through compiling incremental changes:

| Module family | Responsibility | Key outputs |
|---|---|---|
| Driver/project | Inputs, argv, target settings, scheduling, output transactions | Compilation contexts and build manifest |
| Clang adapter | AST/schema access, declarations, source origins, target data | Canonical semantic projection |
| Source IR | Types, identities, expressions, statements, storage, effects | Verified typed program |
| Analysis | CFG, dominance, liveness, aliases, null/bounds/effects | Versioned facts with provenance |
| Transform | Structured flow and safe idiom recovery | Target-independent verified rewrites |
| Elisa IR | Names, types, declarations, regions, statements, expressions | Explicit target program |
| Emit | Precedence, formatting, comments and source maps | Deterministic Elisa files |
| Compatibility | C++ source-library behavior implemented in Elisa | Demand-driven cpp modules |
| Validation/reporting | IR verifiers, diagnostics, differential harness, quality metrics | Evidence for correctness and readability |

### 3.2 Required data contracts

- **Compilation context:** working directory, original argv, normalized frontend argv, language standard, target triple, ABI flags, defines, include paths, selected configuration and Clang version.
- **Declaration identity:** canonical declaration plus translation-unit/linkage context; display name and linker name are separate fields.
- **Type identity:** structural canonical type plus source aliases, qualifiers at every pointer level, size/alignment, address space, function ABI and template arguments.
- **Expression:** result type, value category, storage/place identity where applicable, source span, sequenced children and effect summary.
- **Storage/place:** object identity, field/index path, offset relation, lifetime, address exposure and volatile/atomic qualifiers.
- **Control flow:** explicit edges and terminators, loop/switch targets, scope boundaries, cleanup obligations and exceptional edges.
- **Fact:** assertion, supporting control-flow region, alias/dependency set, invalidation condition and analysis revision.
- **Origin:** physical/spelling/expansion locations, source hash, macro chain and synthesized-node reason.
- **Rewrite record:** rule ID, matched nodes, proven preconditions, old/new IR roots and validity checks.
- **Output manifest:** generated files, dependencies, helper/library requirements, target/toolchain identities and generation hash.

### 3.3 Non-negotiable invariants

1. Evaluation count, sequencing, short-circuiting and observable side effects are preserved.
2. Integer widths, signedness, conversions, floating behavior and ABI layouts follow the selected source target.
3. Pointer optionality, constness, storage identity, aliasing and lifetime cannot be weakened through cosmetic cleanup.
4. Unproven facts cannot justify removing a check, changing ownership, eliding an effect or rewriting control flow.
5. All emitted references bind to the intended declarations; source names and library names are never semantic lookup keys by themselves.
6. Every transformation either establishes its preconditions or preserves the already-correct representation.
7. A failed unit/project translation does not publish an apparently complete output generation.
8. Generated output is deterministic for the same normalized input context and toolchain.
9. Compatibility code has ordinary Elisa semantics and explicit supported source-library contracts.
10. Compiler bugs, translator bugs, unsupported source features and invalid source programs are reported separately.

## 4. Milestones and implementation order

| Milestone | Focus | Exit gate |
|---|---|---|
| M0 | Reconcile current work, toolchain provenance, fixture harness | Fresh local build and truthful per-feature baseline |
| M1 | Clang context, bounded acquisition, canonical types/identities | Header-heavy inputs retain needed semantics with bounded resources |
| M2 | C semantic correctness and verified source IR | Differential fixtures pass for advertised C features |
| M3 | Structured control flow and expression readability | Major dispatcher/cast/temp reductions with identical behavior |
| M4 | Reliable multi-file translation and foreign ABI | Deterministic relocatable projects compile, link and initialize correctly |
| M5 | C-style C++ and initial compatibility contracts | Generic map fixtures and audited Wolf requirements pass |
| M6 | C++ object model, templates, cleanup and exceptions | Feature families pass their semantic and ABI gates |
| M7 | Broader library adaptation, diagnostics and product quality | Supported libraries/corpora have published coverage and reproducible reports |
| M8 | Release and continuous correctness | Packaged translator, portability matrix, soak/fuzz/performance gates |

Start measurement at M0, the typed IR contract at M1 and C++ lifetime design before adding class syntax. Run small native comparisons throughout. A compiler or runtime blocker should be minimized immediately while independent translator work continues.

The practical ROI order is: semantic correctness and trustworthy tests; canonical types/identities; safe structured control flow; names and declaration placement; expression/cast cleanup; project/ABI integrity; proven slice/null/mutability improvements; C++ object/lifetime support; library breadth; profile-driven tuning.

## 5. Detailed implementation backlog

Each work item includes an owner/location, prerequisites, concrete work and an acceptance gate. Locations prefixed “proposed” are architecture destinations, not existing files. All translator production code remains Elisa.

## 5.1 Foundation, provenance and maintainability

### B01 — Establish a fresh, isolated baseline [P0]

**Location:** scripts/setup_local_compilers.sh, scripts/test.sh, proposed docs/execution_status.md. **Depends on:** none.

- [ ] Inventory current tracked/untracked changes, compiler worktree revisions and executable hashes; preserve unrelated work and establish which changes belong to this roadmap.
- [ ] Verify stage0, stage1 and runtime paths resolve to the intended isolated worktrees; explicitly supplied invalid paths must fail without silently selecting an installed compiler.
- [ ] Build the translator once with an explicit local compiler and record the source tree fingerprint, target, flags, runtime and Clang identity.
- [ ] Run existing fixture/corpus checks serially with deadlines; separate old expected output mismatches from compiler failures and incorrect generated behavior.
- [ ] Record one evidence row per feature: source fixture, emitted artifact, compile/link result, runtime result and remaining limitation.

**Acceptance:** A new contributor can reproduce the baseline from recorded inputs; every claimed passing feature points to a fresh result.

### B02 — Split and strengthen the test driver [P0/P1]

**Location:** scripts/test.sh, proposed test runner/fixture manifest. **Depends on:** B01.

- [ ] Separate translator build, translation checks, compiler checks, linking, runtime comparison, quality assertions and corpus suites.
- [ ] Keep sh scripts/test.sh as the canonical full entry; add documented focused selections and a reuse-build mode with content-based freshness checks.
- [ ] Represent native and Elisa build/link arguments as arrays in a fixture manifest; do not rely on one universal linker command for every platform.
- [ ] Capture exit status, stdout, stderr and selected produced files; support expected nonzero exit codes and binary outputs.
- [ ] Report timeouts, crashes, skips, unsupported cases and pass/fail totals distinctly; required tests cannot silently pass when tools are absent.

**Acceptance:** A deliberately corrupted output, wrong exit status, crash and stale executable each fail the appropriate test stage.

### B03 — Restore source-size and namespace discipline [P1]

**Location:** src/clang_ast.elisa, src/emit_* and src/lower_expr.elisa. **Depends on:** B01–B02.

- [ ] Measure actual file lengths and split every production source file over 600 lines along responsibilities, beginning with AST acquisition/access, type layout and program/control-flow emission.
- [ ] Introduce explicit module interfaces for frontend, IR, analysis, transforms and output while proving Elisa include/extend behavior in small compilable changes.
- [ ] Keep public symbols narrow, avoid cyclic module ownership and eliminate accidental reliance on include order.
- [ ] Preserve existing output and behavior during each extraction; do not combine a large refactor with semantic rewrites.
- [ ] Add a source-file length gate with an explicit generated-file policy; split the test driver into focused suites.

**Acceptance:** Every maintained translator source file is at most 600 lines and the existing semantic suite passes after extraction.

### B04 — Maintain an evidence ledger and steady commits [P1]

**Location:** proposed docs/execution_status.md and docs/decisions/. **Depends on:** B01.

- [ ] Link every work-item status to its implementation commit, tests, toolchain context and unresolved requirements.
- [ ] Use one reviewable commit per verified slice where practical; include the minimized regression with the fix.
- [ ] Keep compiler fixes in their owning isolated repositories and record their commit IDs in the translator compatibility manifest.
- [ ] Record architecture decisions for projection, typed IR, pointer representation, object lifetime, source mapping and output packaging.
- [ ] Update README support claims when behavior changes; never mark a whole work item complete from one happy-path fixture.

**Acceptance:** The ledger distinguishes implemented, tested and still-unverified work without relying on conversational history.

## 5.2 Clang frontend and compilation context

### F01 — Preserve compilation commands exactly [P0]

**Location:** src/cli.elisa, src/clang_ast.elisa; proposed frontend/process.elisa. **Depends on:** B02.

- [ ] Keep compilation-database arguments as argv; support command strings through a documented platform-aware tokenizer rather than general shell evaluation.
- [ ] Normalize only build-output/dependency-generation options that conflict with AST extraction; preserve language, target, ABI, defines, includes and forced includes.
- [ ] Handle response files, compiler launchers, paths with spaces and duplicate source configurations with explicit policies and tests.
- [ ] Capture stdout, stderr and child status independently; propagate Clang failure even when it emitted partial JSON.
- [ ] Make C/C++ language/standard selection explicit and honor database -x options before filename defaults; remove silent semantic changes from unconditional default defines.

**Acceptance:** A matrix of direct inputs and databases reproduces native frontend contexts and never reports success after Clang failure.

### F02 — Bound AST acquisition and projection memory [P0/P1]

**Location:** src/clang_ast_filter.elisa, src/clang_ast.elisa. **Depends on:** F01.

- [ ] Measure raw JSON bytes, retained projection bytes, parsed nodes, Clang RSS and translator RSS separately.
- [ ] Stream or spool the AST under a budget instead of retaining full raw JSON and a second compact representation simultaneously.
- [ ] Preserve a dependency closure of referenced declarations, canonical types, layout, inline definitions and template specializations; source-directory membership alone is insufficient.
- [ ] Define a versioned compact semantic projection; prototype a small Clang API extractor/binding if JSON cannot supply required facts, with translation decisions still implemented in Elisa.
- [ ] Validate malformed/truncated JSON, escaped filenames, omitted inherited locations, deep nesting and missing declaration dependencies with bounded failure paths.

**Acceptance:** Header-heavy fixtures preserve all needed semantics, produce equivalent IR and stay within a measured configurable memory budget.

### F03 — Canonical declarations, source origins and diagnostics [P0/P1]

**Location:** src/clang_context.elisa, src/clang_ast.elisa; proposed frontend/symbols.elisa. **Depends on:** F01–F02.

- [ ] Index declaration IDs and canonical/redeclaration relationships once instead of recursively searching the AST per use.
- [ ] Separate physical path, spelling location, expansion location, owning translation unit and source hash.
- [ ] Retain source names, linker/mangled names, internal/external linkage, visibility and language linkage as distinct fields.
- [ ] Deduplicate diagnostics by semantic issue and precise source origin without merging different macro expansions or units.
- [ ] Make missing referenced declarations a projection/lowering error with a dependency trail rather than guessing a type.

**Acceptance:** Forward declarations, repeated headers, extern C, static same-name functions and macro-origin diagnostics retain correct identities.

### F04 — Use a structured target-aware type model [P0]

**Location:** src/emit_types.elisa, src/emit_types_records.elisa, src/clang_typedefs.elisa. **Depends on:** F03.

- [ ] Represent types structurally: builtins, pointers/references, arrays, records/unions, enums, functions, member pointers and template specializations.
- [ ] Retain typedef spelling for readability separately from canonical identity used for semantic decisions.
- [ ] Store qualifiers at each indirection level, address spaces, incomplete/complete state, target size/alignment and function calling convention.
- [ ] Use Clang's resolved types/layout data instead of parsing nested qualified-type strings as the primary semantic model.
- [ ] Reject unavailable essential ABI facts; permit a documented textual fallback only when it cannot change semantic interpretation.

**Acceptance:** Nested pointers, arrays of pointers, pointer-to-array types, callback typedefs, aliases and same-spelled unrelated types lower distinctly.

### F05 — Preprocessor and macro provenance [P1/P2]

**Location:** proposed frontend/preprocessor.elisa, source-map records. **Depends on:** F02–F04.

- [ ] Retain active preprocessor configuration, macro definitions/expansions and conditional-source provenance where available.
- [ ] Recover constant-like macros as named Elisa constants when their use context and source visibility permit.
- [ ] Translate eligible function-like macros into Elisa static functions only after compiler probes establish compatible evaluation count, laziness, typing and expansion behavior.
- [ ] Keep expanded semantics for token pasting, stringification, statement macros, repeated side effects and context-dependent identifiers until an equivalent source abstraction is proven.
- [ ] Distinguish one configured build translation from a multi-configuration migration; do not claim to preserve inactive branches that were never analyzed.

**Acceptance:** Macro fixtures cover side-effecting arguments, short-circuiting, repeated uses, token operations and nested expansion without changed behavior.

### F06 — Clang compatibility and build-context cache [P1]

**Location:** proposed frontend/schema.elisa, driver/cache.elisa. **Depends on:** F01–F04.

- [ ] Record and test supported Clang versions/schema variants; report missing required fields with a useful compatibility diagnostic.
- [ ] Cache semantic projections by normalized argv, compiler identity, target and content hashes of source plus dependencies.
- [ ] Invalidate on changed generated headers, response files, defines, target settings and extractor schema.
- [ ] Do not key caches by timestamps or source filename alone; publish entries atomically and validate corrupt entries.
- [ ] Provide uncached mode and compare cached/uncached results on deterministic dependency-edit sequences.

**Acceptance:** Cache hits preserve identical translation and stale dependency/configuration entries are never reused.

## 5.3 Source IR and exact C semantics

### S01 — Make the typed IR explicit and verifiable [P0]

**Location:** src/lower_expr.elisa, src/lower_stmt.elisa; proposed ir/. **Depends on:** F03–F04.

- [ ] Separate parsing, semantic normalization and target rendering; eliminate semantic decisions based on rendered expression text.
- [ ] Represent lvalues/rvalues, explicit loads/stores, casts, sequencing, calls, storage durations, initialization and control terminators.
- [ ] Attach source origins and full canonical types to every value, declaration and place.
- [ ] Verify indices, declaration references, types, CFG targets, value categories and scope/lifetime ownership before and after each pass.
- [ ] Add deterministic IR dumps and pass-selection controls for minimizing semantic regressions.

**Acceptance:** Invalid IR cannot reach source emission and a pass failure identifies the earliest broken invariant and source node.

### S02 — Preserve integer, enum and boolean semantics [P0]

**Location:** src/c_semantics.elisa, typed arithmetic lowering. **Depends on:** S01.

- [ ] Implement integer rank/promotions/usual conversions from the selected target, including char signedness, enum representation and pointer-sized integers.
- [ ] Model unsigned wraparound, signed overflow policy, division/remainder and valid shift counts explicitly.
- [ ] Fold constants at their source width/signedness rather than host integer width; preserve implementation-defined behavior selected by the source target.
- [ ] Recover bool only when all values/uses prove a boolean domain and the ABI/storage representation is unaffected.
- [ ] Keep flag enums distinct from closed alternatives; preserve mixed integer/enum operations and qualified symbolic constants.

**Acceptance:** Boundary-value differential tests pass across supported target models and both output modes.

### S03 — Preserve evaluation and sequencing [P0]

**Location:** expression lowering, call lowering, proposed analysis/effects.elisa. **Depends on:** S01–S02.

- [ ] Model comma expressions, pre/post increment, compound assignments and short-circuit expressions with exact evaluation counts.
- [ ] Lower side-effecting conditions and arguments through explicit sequence points/temporaries when required by target-language evaluation rules.
- [ ] Preserve source-standard sequencing guarantees for C++ calls and assignments; avoid tests that assume a universal order for unspecified C evaluations.
- [ ] Separate pure, potentially trapping, allocating, volatile, atomic and externally observable operations.
- [ ] Do not duplicate, reorder or drop loads/calls merely because their rendered expressions appear identical.

**Acceptance:** Counter/trace fixtures detect evaluation-order/count regressions, including aliasing assignments and early-return expressions.

### S04 — Correct floating-point and literal representation [P0/P1]

**Location:** typed numeric lowering and literal writer. **Depends on:** S01–S03.

- [ ] Preserve target floating formats, exact constant rounding and implicit arithmetic conversions.
- [ ] Keep NaN, infinities, negative zero and signed-zero-sensitive expressions intact; do not apply algebraic identities valid only for real numbers.
- [ ] Make fast-math or relaxed semantics explicit in compilation context and optimization eligibility.
- [ ] Preserve integer/float suffix intent, hexadecimal values and byte/code-unit values in character and string literals.
- [ ] Diagnose unavailable long-double/extended formats until a verified representation or compatibility path exists.

**Acceptance:** Literal round-trip and numerical edge fixtures agree with the selected native reference under the same semantic flags.

### S05 — Preserve pointer values, arithmetic and aliasing [P0]

**Location:** src/emit_places.elisa, type and expression lowering. **Depends on:** S01–S04.

- [ ] Represent pointee type, nullable shape, allocation/object provenance, offset and qualifiers separately.
- [ ] Support array decay, address-of, dereference, pointer stepping, subtraction, one-past values and pointer-to-array scaling without accidental integer truncation.
- [ ] Preserve null as a pointer value at ABI boundaries and keep pointer-depth information through void-pointer conversions.
- [ ] Audit C raw-pointer behavior against Elisa reference validity/alias/lifetime assumptions; add narrowly scoped compiler primitives when those contracts cannot express C.
- [ ] Test pointer arithmetic and equality within defined source behavior, and document target-specific policies for implementation-defined conversions.

**Acceptance:** Array walks, aliasing updates, pointer slots and 64-bit round-trips match native behavior without fabricated non-null guarantees.

### S06 — Records, unions, arrays and initialization [P0]

**Location:** src/emit_types_records.elisa, aggregate lowering. **Depends on:** F04, S01, S05.

- [ ] Preserve field order, padding/alignment requirements, packed records, anonymous members, unions and bitfield layout using verified target metadata.
- [ ] Handle partial/designated/sparse/nested initializers, zero filling and initializer evaluation order.
- [ ] Keep one record with six fields distinct from six array elements; emit positional or named Elisa aggregates only when the target parser and expected type establish the intended nesting.
- [ ] Represent flexible-array members, zero/one-element trailing-array idioms and variable-length arrays with explicit size/lifetime contracts.
- [ ] Preserve compound-literal storage duration and address identity; do not replace mutable storage with a shared constant.

**Acceptance:** Size/alignment/offset probes and runtime mutation checks pass; unsupported layouts produce exact diagnostics.

### S07 — Storage duration, initialization and teardown [P0/P1]

**Location:** global/local declaration lowering, project initializer emission. **Depends on:** S01, S06.

- [ ] Model automatic, static, thread-local and external storage independently of Elisa mutability.
- [ ] Preserve C zero initialization and constant initialization before runtime initializers.
- [ ] Ensure function-local statics initialize once and preserve their persistent identity.
- [ ] Define project initialization entry points and idempotence without basename collisions or accidental repeated execution.
- [ ] Carry teardown/cleanup obligations into IR so later C++ support does not retrofit lifetime semantics into formatted text.

**Acceptance:** Cross-unit globals and repeated function calls observe correct initial values, persistent state and initializer counts.

### S08 — Variadics, atomics and low-level extensions [P1/P2]

**Location:** foreign ABI lowering, proposed compatibility primitives. **Depends on:** F04, S03–S07.

- [ ] Complete source-defined variadics with default argument promotions, va_start, va_arg, va_copy and va_end lifetime rules.
- [ ] Verify actual platform va_list layout/ABI through compiler primitives and C interop probes.
- [ ] Preserve volatile access and atomic operation ordering using target-supported intrinsics or a verified runtime layer.
- [ ] Classify compiler builtins by intrinsic identity and semantics; do not infer ordinary external function signatures from a handwritten list.
- [ ] Plan explicit implementations for setjmp/longjmp, computed goto, inline assembly and supported compiler extensions; preserve lifetime/control constraints and diagnose unsupported families until their gates pass.

**Acceptance:** Each newly supported low-level family has native differential and ABI tests, including cleanup and side effects.

## 5.4 Control-flow recovery and idiomatic expressions

### I01 — Build reusable CFG analyses [P1]

**Location:** src/emit_cfg.elisa; proposed analysis/cfg.elisa. **Depends on:** S01–S03, S07.

- [ ] Build basic blocks with explicit scope, cleanup and exceptional-edge information.
- [ ] Compute reachability, predecessors, dominance/post-dominance, loop regions and strongly connected components once per function revision.
- [ ] Identify reducible structured regions and entry/exit constraints without relying on label names.
- [ ] Invalidate analysis when transforms change edges or scope obligations.
- [ ] Provide graph dumps and independent small-graph tests for analysis correctness.

**Acceptance:** Nested loops, cross-scope jumps, unreachable blocks and irreducible graphs have verified region classifications.

### I02 — Recover if/else, loops and early exits [P1]

**Location:** CFG transforms and src/emit_program.elisa. **Depends on:** I01.

- [ ] Convert single-entry regions into if/elif/else and loops using dominance and exit proofs.
- [ ] Recover guard returns and flatten nesting when doing so preserves scope, initialization and cleanup.
- [ ] Recognize for/while/do-while forms, retaining exact increment and continue behavior.
- [ ] Use Elisa iteration/ranges only when bounds, overflow, step, mutation and address-exposure conditions prove equivalence.
- [ ] Keep side-effecting predicates evaluated at their original frequency, including do-while continue edges.

**Acceptance:** Structured fixtures produce readable code and native-equivalent traces at zero/one/many iterations and boundary values.

### I03 — Localize and reduce remaining goto dispatch [P1]

**Location:** src/emit_cfg.elisa. **Depends on:** I01–I02.

- [ ] Thread empty jump-only blocks, merge compatible straight-line blocks and remove unreachable states.
- [ ] Recover common forward error exits and cleanup tails without deleting cleanup work.
- [ ] Restrict dispatch to residual unstructured regions; structured surrounding code should remain ordinary Elisa.
- [ ] Allow bounded code duplication only with a documented size budget and proofs for initialization, side effects and cleanup.
- [ ] Give residual states readable deterministic names/source notes; record why dispatch remains rather than merely renaming __c_pc.

**Acceptance:** Reducible examples eliminate dispatch, irreducible examples retain correct bounded fallback and metrics expose residual region size.

### I04 — Improve switch-to-match lowering [P1]

**Location:** switch lowering and CFG transforms. **Depends on:** S02–S03, I01.

- [ ] Evaluate the selector once and preserve promotions, enum type and full-width case constants.
- [ ] Group labels sharing equivalent arms into or-patterns; form ranges only when the represented values and Elisa range semantics match exactly.
- [ ] Remove terminal switch breaks and temporary completion flags only when control-flow proofs establish they are redundant.
- [ ] Model fallthrough, declarations crossing labels, conditional breaks, enclosing-loop continue and nested switches explicitly.
- [ ] Choose a readable structured lowering or localized state region for complex fallthrough; cap duplicated arm tails.

**Acceptance:** Cases/default, sparse/dense labels, fallthrough chains and nested loop interactions agree with native C/C++.

### I05 — Recover source names and declaration placement [P1]

**Location:** name registry, declaration and CFG transforms. **Depends on:** F03, S01, I01.

- [ ] Allocate output identifiers from canonical binding identity and scope; preserve legal source spelling by default.
- [ ] Handle keywords, Unicode, shadowing, aliases and sanitized-name collisions deterministically.
- [ ] Name necessary temporaries from their role and related source expression, using stable suffixes only for real collisions.
- [ ] Move declarations toward first definition and narrow scopes only after dominance, lifetime and jump-entry checks.
- [ ] Eliminate redundant alias temporaries and phi-like variables when SSA/liveness analysis proves a direct expression is safe.

**Acceptance:** Repeated names bind correctly and unnecessary hoisted locals/synthetic names decline on generic fixtures.

### I06 — Simplify expressions through verified rules [P1]

**Location:** src/emit_quality.elisa, proposed transform/expressions.elisa. **Depends on:** S01–S05.

- [ ] Create explicit rewrite rules for redundant casts, identity operations, constant conditions, boolean predicates and conditional expressions.
- [ ] Require source-width, signedness, trapping and effect preconditions for every algebraic rewrite.
- [ ] Preserve cast operations that encode sign extension, truncation, const changes, pointer ABI or foreign conversion.
- [ ] Fold only the pure subexpressions proven safe; do not remove side-effecting evaluation under multiplication by zero or equivalent-looking branches.
- [ ] Keep rule counters and negative fixtures for every transformation so readability gains remain explainable.

**Acceptance:** Positive fixtures simplify while nearby overflow, NaN, volatile, alias and side-effect counterexamples remain semantically intact.

### I07 — Improve null, mutability and effect inference [P1]

**Location:** src/emit_analysis.elisa, src/emit_expr_facts.elisa, src/emit_effects.elisa. **Depends on:** S03, S05, I01.

- [ ] Track facts by storage/place identity through branches and loops, with explicit alias and call invalidation.
- [ ] Infer immutable bindings independently from immutable pointees; C pointer constness has multiple levels.
- [ ] Narrow optional pointers inside proven dominated regions and reuse the narrowed value without repeated assertions.
- [ ] Audit generic nonnull helper contracts, including the existing zeroed-on-null behavior; do not manufacture a valid non-null reference from null.
- [ ] Compute local and call-graph effects to minimize unsafe/trusted regions without suppressing required checks or foreign ABI constraints.

**Acceptance:** Aliasing and callback-mutation fixtures invalidate stale facts; valid narrowing reduces helper and unsafe-region noise.

### I08 — Recover slices, strings and aggregates safely [P1/P2]

**Location:** proposed analysis/bounds.elisa, target idiom transforms. **Depends on:** S05–S06, I06–I07.

- [ ] Recognize pointer-plus-length relations only when object extent, lifetime, mutation and escape behavior are known.
- [ ] Use native slice syntax when it preserves exact start/end/length semantics, including explicit handling of -1 conventions.
- [ ] Distinguish byte buffers, NUL-terminated C strings, borrowed text views and owned text; do not replace arbitrary char pointers with strings.
- [ ] Recover fixed-array literals and named/positional record values from typed initialization rather than bracket-shape heuristics.
- [ ] Preserve ABI-facing pointer/length signatures unless a separate internal wrapper proves conversion safe.

**Acceptance:** Compiler probes and runtime fixtures cover empty slices, embedded NULs, non-ASCII bytes, mutation, lifetime escape and endpoint boundaries.

## 5.5 Project translation, output quality and external ABI

### P01 — Use one project identity and naming registry [P0/P1]

**Location:** src/cli.elisa, project IR and module emission. **Depends on:** F03–F04, S07.

- [ ] Give files, declarations, generated helpers and initializer functions stable identities across a whole project.
- [ ] Resolve duplicate basenames and sanitized-name collisions with the same registry used by both module filenames and emitted references.
- [ ] Respect internal linkage and anonymous scopes; two static functions with the same spelling in different units remain distinct.
- [ ] Merge compatible external redeclarations and diagnose incompatible ones.
- [ ] Use stable ordering independent of compilation-database enumeration where semantics permit.

**Acceptance:** Same-basename units, headers with static definitions and reordered databases produce correct deterministic projects.

### P02 — Resolve headers, shared declarations and initialization [P0/P1]

**Location:** project dependency graph and global emission. **Depends on:** P01, S06–S07.

- [ ] Choose explicit ownership for shared record/enum/typedef declarations and header-defined inline functions.
- [ ] Avoid duplicate definitions while preserving source-language linkage and per-unit static objects.
- [ ] Handle cyclic declarations with forward/type dependency planning supported by Elisa modules.
- [ ] Preserve required initialization relationships and model C++ dynamic/static initialization rules as object-model support arrives.
- [ ] Emit a project entry/initializer contract that external hosts can call without relying on one generated main.

**Acceptance:** Multi-file native-versus-Elisa fixtures compile/link and observe correct shared types, globals and initialization.

### P03 — Strengthen foreign declarations and ABI verification [P0]

**Location:** src/emit_expr_calls.elisa, external declaration emitter. **Depends on:** F04, S05–S08, P01.

- [ ] Derive callable/global declarations from Clang identities, including variadics, linkage, calling convention, qualifiers and linker spelling.
- [ ] Verify struct by-value arguments/returns, sret, callbacks, function pointer fields and nested aggregate ABI.
- [ ] Test mixed native/Elisa linking in both directions; include nontrivial pointer returns to catch truncation.
- [ ] Separate translated definitions from externally linked declarations and preserve export/link-name rules.
- [ ] Represent unsupported foreign layouts/calling conventions with diagnostics or a narrowly scoped verified shim, never a guessed signature.

**Acceptance:** C harnesses call translated functions and translated code calls C/SDL fixtures with matching values, sizes and side effects.

### P04 — Publish relocatable output transactionally [P1]

**Location:** src/cli.elisa, runtime/helper library packaging. **Depends on:** P01–P03.

- [ ] Generate all files into a staging generation and publish a manifest only after translation and validation stages required by the selected workflow succeed.
- [ ] Avoid publishing a mixed old/new project when one unit fails; retain previous usable output with explicit failure status.
- [ ] Resolve runtime and cpp_lib dependencies through explicit output configuration or vendored release assets, not hard-coded build-directory-relative paths.
- [ ] Emit only required generic helpers and compatibility fragments, deduplicated across project units.
- [ ] Record output ownership and remove obsolete generated files only from a validated prior manifest, never by broad directory deletion.

**Acceptance:** Projects move outside the repository and still compile; failed regeneration cannot look like complete successful output.

### P05 — Use a structured Elisa writer [P1]

**Location:** src/emit_format.elisa, target IR and source writer. **Depends on:** S01, I02–I08.

- [ ] Render precedence and associativity from target expression structure instead of cleaning arbitrary parentheses afterward.
- [ ] Format signatures, calls, aggregates and nested expressions with stable indentation and width policies.
- [ ] Preserve literal bytes, escapes, multiline strings and source-comment content exactly where required.
- [ ] Attach comments to declarations/statements using origin/trivia ownership; keep licenses and conditional/macro context useful.
- [ ] Round-trip emitted output through the selected Elisa parser and reject invalid target constructs before publication.

**Acceptance:** Formatting is deterministic/idempotent, literals remain identical and nested operator fixtures parse to the intended target structure.

### P06 — Provide source maps and actionable translation reports [P1/P2]

**Location:** diagnostics, emitter origins and proposed reports/. **Depends on:** F03, S01, P04–P05.

- [ ] Emit generated-span to source-span mappings with source hashes, macro origins and synthesized-node reasons.
- [ ] Report unsupported constructs with source location, semantic category, relevant type and the missing translator/compiler capability.
- [ ] Offer machine-readable reports and human summaries of translation coverage, residual fallback and generated dependencies.
- [ ] Support a rewrite explanation mode that shows the proof category for a simplification and why a desired rewrite was declined.
- [ ] Keep mapping generation generic; do not add a language-server implementation to this repository.

**Acceptance:** Users can trace a generated statement, ABI wrapper or residual state region to its original source and understand blockers.

## 5.6 C++ language support

### C01 — Audit real C++ requirements and resolve names [P1]

**Location:** src/cpp_compat.elisa, frontend identities, corpus inventory. **Depends on:** F03–F04, S01.

- [ ] Inventory Wolf4SDL and other candidate units by Clang node/type/operation families and runtime use, including rare paths.
- [ ] Support namespaces, aliases, using declarations, extern C and overload resolution using Clang's resolved targets.
- [ ] Lower references and const member access with correct storage identity; do not replace references with nullable pointers by default.
- [ ] Represent default arguments at resolved call sites and preserve overload/template selections.
- [ ] Publish separate coverage for C-style C++, object-model features and source-library adapters.

**Acceptance:** The requirement report covers every selected project unit and no genuine C++ construct is silently treated as C.

### C02 — Classes, members and constructors [P1/P2]

**Location:** proposed cpp/object_lowering.elisa. **Depends on:** C01, S06–S07, P03.

- [ ] Represent class layout, access, data members, static members, methods and implicit receiver semantics.
- [ ] Lower default/value/aggregate/copy/move initialization distinctly using Clang-selected constructors.
- [ ] Preserve base/member initialization order, delegating constructors and partial-construction state.
- [ ] Handle operators as resolved functions/protocol operations only when Elisa semantics match.
- [ ] Keep source-level migrated class representation separate from native C++ ABI layout when an external boundary requires an adapter.

**Acceptance:** Constructor-order and member-method fixtures produce matching traces and correct object identity/layout at supported boundaries.

### C03 — Destructors, RAII and temporary lifetimes [P0 for C++ objects]

**Location:** source IR cleanup edges, proposed cpp/lifetimes.elisa. **Depends on:** C02, I01.

- [ ] Track automatic object lifetimes, temporary materialization, lifetime extension and destruction order.
- [ ] Insert cleanup on normal exits, returns, breaks, continues, supported jumps and later exception unwinding.
- [ ] Model copy/move operations, elision permitted/required by the selected standard and moved-from object behavior.
- [ ] Use Elisa region/defer/destructor features only after compiler probes establish equivalent cleanup semantics.
- [ ] Preserve resource release for foreign/library objects and distinguish ownership from non-owning references.

**Acceptance:** Counter/resource fixtures match construction/destruction traces on every exit path with no double destruction or leaks.

### C04 — Templates and generic recovery [P1/P2]

**Location:** Clang specialization projection, proposed cpp/templates.elisa. **Depends on:** C01–C03.

- [ ] Translate resolved specializations as a correct initial path while preserving their source template identity.
- [ ] Recover Elisa generics only where type/value parameters, constraints, overload behavior and operation semantics map faithfully.
- [ ] Support non-type parameters, defaults, partial/explicit specialization and parameter packs in staged independently tested increments.
- [ ] Avoid expanding unused library implementations; retain exactly the instantiated semantic dependencies required.
- [ ] Control instantiation/code growth and keep specialized output names stable and readable.

**Acceptance:** Specialization-dependent behavior is preserved; eligible templates become readable generics without conflating distinct cases.

### C05 — Lambdas, callable objects and captures [P1/P2]

**Location:** proposed cpp/callables.elisa. **Depends on:** C02–C04, S03, P03.

- [ ] Lower closure storage and by-value/by-reference/this/init captures with exact capture time and lifetime.
- [ ] Preserve mutable lambdas, generic lambdas and overloaded call operators.
- [ ] Model callable copies/moves and destruction through the object-lifetime system.
- [ ] Use Elisa closures/functions where representation and effects fit; keep explicit closure records otherwise.
- [ ] Handle noncapturing conversion to function pointers only when calling convention and function-value representation are verified.

**Acceptance:** Escaping/non-escaping capture fixtures and callback interop match native state and lifetime behavior.

### C06 — Inheritance, virtual dispatch and RTTI [P2]

**Location:** proposed cpp/inheritance.elisa, class layout metadata. **Depends on:** C02–C03, P03.

- [ ] Support base subobjects, conversions, access and member lookup from canonical Clang facts.
- [ ] Implement virtual dispatch, overriding and destructor behavior before simplifying eligible closed hierarchies.
- [ ] Plan multiple/virtual inheritance and pointer adjustment explicitly; do not assume a single receiver address represents every base.
- [ ] Model dynamic_cast/typeid behavior where RTTI is enabled, including failure modes and polymorphic requirements.
- [ ] Separate ordinary source translation from interoperability with compiler-specific native vtables/member-pointer ABIs.

**Acceptance:** Hierarchy fixtures verify dispatch, casts, base offsets and destruction for each advertised inheritance category.

### C07 — Exceptions and cleanup-aware control flow [P2]

**Location:** source IR exceptional edges, proposed cpp/exceptions.elisa. **Depends on:** C03, C06, I01.

- [ ] Represent throw, rethrow, catch matching, exception object lifetime and propagation explicitly.
- [ ] Preserve stack unwinding and partial-construction cleanup across translated functions.
- [ ] Model noexcept and termination behavior rather than translating every failure to an ordinary return.
- [ ] Prototype an Elisa exception/effect/runtime bridge and verify its ABI limits for native C++ boundaries.
- [ ] Keep exception-enabled and disabled source configurations distinct in the support matrix and build context.

**Acceptance:** Nested throw/catch/rethrow and destructor traces match native behavior; crossing unsupported native boundaries fails clearly.

### C08 — Remaining language families and standard coverage [P2/P3]

**Location:** C++ feature matrix and compiler adapters. **Depends on:** C01–C07.

- [ ] Add member pointers, user-defined conversions/literals, initializer_list lifetimes and allocation/deallocation overloads through canonical semantic records.
- [ ] Support constexpr/consteval results and static assertions without changing runtime-visible semantics or evaluating untrusted translated programs.
- [ ] Plan concepts/requires, newer deduction forms, structured bindings and range-for through resolved Clang semantics.
- [ ] Treat coroutines as a state/lifetime transformation with suspension, destruction and exception behavior; do not equate them to ordinary loops.
- [ ] Add C++ modules and newer standards as explicit contexts and fixtures; track every unsupported family until implemented or explicitly excluded by a revised product requirement.

**Acceptance:** Each advertised standard/feature has positive, negative and lifetime/ABI tests; broad support claims match the feature matrix.

## 5.7 Translator-owned C++ compatibility libraries

### L01 — Define library adapter contracts [P1]

**Location:** src/cpp_compat.elisa, cpp_lib/. **Depends on:** F04, C01.

- [ ] Recognize standard-library entities by resolved canonical declaration/specialization identity, including legitimate implementation namespaces.
- [ ] Distinguish a user-defined unordered_map from std::unordered_map even when the spelling matches.
- [ ] Declare supported methods, overloads, template policies, exceptions, complexity expectations, lifetimes and ABI boundaries per adapter.
- [ ] Use ordinary Elisa names such as find, clear and size with overloads/uniform call syntax in module cpp.
- [ ] Emit adapter requirements only for reachable translated operations and report unsupported policy combinations before code generation.

**Acceptance:** An unrelated same-named user type never triggers a standard-library adapter and unsupported operations have exact diagnostics.

### L02 — Complete unordered_map semantics incrementally [P1]

**Location:** cpp_lib/unordered_map.elisa and its generic lowering. **Depends on:** L01, C02–C04.

- [ ] Audit dict semantics against key equality/hash, default construction, value/reference stability, allocation and destruction requirements.
- [ ] Make operator[] insert a correctly constructed mapped value on a miss; zeroed is valid only for types where it is equivalent.
- [ ] Implement non-inserting find/contains/count, iterator/end comparison, insertion/emplacement, erase, clear, size and empty in tested increments.
- [ ] Support custom hash/equality/allocator policies explicitly or diagnose them; never ignore extra template arguments.
- [ ] Preserve standard-required reference/iterator validity across insert/rehash/erase, using an appropriate storage design instead of assuming dict guarantees.
- [ ] Test allocation failures, key/value copy/move/destruction and actual Wolf operations without Wolf-specific branches.

**Acceptance:** Native C++ and Elisa contract traces agree for supported operations, including misses, collisions, growth and retained references.

### L03 — Add containers and strings by semantic family [P2]

**Location:** proposed cpp_lib/vector.elisa, string.elisa and related modules. **Depends on:** L01, C03–C04.

- [ ] Prioritize additional adapters using actual corpus requirements and frequency, beginning with a recorded inventory.
- [ ] Map vector/array/span/string/string_view only after auditing ownership, capacity, contiguity, terminators and invalidation rules.
- [ ] Preserve bounds/error behavior, embedded NULs, character element widths and allocator/lifetime behavior.
- [ ] Implement iterators and range operations with correct end/sentinel semantics and invalidation.
- [ ] Keep internal idiomatic Elisa use possible while preserving the source-library contract at observable boundaries.

**Acceptance:** Each added adapter has native-versus-Elisa contract tests and a documented supported API surface.

### L04 — Utilities, algorithms, smart pointers and streams [P2/P3]

**Location:** additional cpp_lib modules. **Depends on:** L01, C03–C07.

- [ ] Implement pair/tuple/optional/variant and comparison behavior using target constructs only where source semantics match.
- [ ] Handle unique/shared ownership and custom deleters with correct destruction and aliasing behavior.
- [ ] Lower algorithms through resolved iterator/category requirements and preserve evaluation/side-effect contracts.
- [ ] Add stream formatting/state/error/locale behavior as explicitly supported increments; avoid a naive replacement of stream insertion with print calls.
- [ ] Audit functional wrappers and exception propagation through callable objects before advertising support.

**Acceptance:** Every supported library family has independent generic fixtures; absence of a corpus use does not justify incorrect placeholder behavior.

## 5.8 Verification, performance and compiler integration

### V01 — Differential and ABI correctness harness [P0]

**Location:** testdata/fixtures, proposed test harness. **Depends on:** B02, S01.

- [ ] Compile native and generated programs with recorded compatible source/target semantics.
- [ ] Compare exit status, exact binary/text outputs and meaningful state traces; normalize only documented nondeterministic fields.
- [ ] Use C/C++ harnesses to test translated library APIs without requiring every fixture to be a standalone main.
- [ ] Exercise optimized and debug Elisa builds where supported; compiler optimization defects must not be hidden by testing only O0.
- [ ] Classify source undefined behavior, implementation-defined behavior, translator mismatch and compiler/backend failure before interpreting differential results.

**Acceptance:** Intentional wrong lowering and ABI mismatches are caught by independent tests, with minimized reproducible artifacts.

### V02 — Property, metamorphic and fuzz testing [P1]

**Location:** proposed tests/property and tests/fuzz. **Depends on:** S01, V01.

- [ ] Generate bounded well-defined programs for integer operations, pointers, aggregates, sequencing and control flow.
- [ ] Compare semantic results before/after each rewrite where a small interpreter/oracle is practical.
- [ ] Use semantics-preserving source transformations such as safe renaming to detect name-dependent logic.
- [ ] Fuzz AST/projection parsers with malformed/truncated/oversized input and enforce allocation/time limits.
- [ ] Retain deterministic seeds and automatically minimize mismatches into permanent focused regressions.

**Acceptance:** Fuzz/property runs produce replayable failures and remain bounded; no translation rule depends on a target program's names.

### V03 — Measure idiomatic output quality honestly [P1]

**Location:** scripts/quality_report.sh, structured transformation report. **Depends on:** I01–I08, P05, V01.

- [ ] Measure residual dispatcher regions/states, duplicated code, unnecessary locals, proven redundant casts, assertion pressure and unsafe scope.
- [ ] Compute metrics from IR/rewrite records so source identifiers, comments and strings do not create false matches.
- [ ] Normalize readability metrics by function/control complexity and report correctness/unsupported coverage alongside them.
- [ ] Maintain curated before/after examples with reviewer notes for cJSON plus unrelated fixtures and projects.
- [ ] Gate only justified regressions; never reward dropping unsupported code, stripping licenses or compressing lines.

**Acceptance:** Reports distinguish real semantic cleanup from text-count changes and every claimed improvement retains correctness evidence.

### V04 — Advance real corpora to verified acceptance [P1]

**Location:** testdata/upstream and corpus suite. **Depends on:** V01–V03, P01–P04.

- [ ] Pin upstream revisions, source licenses, translation commands and native build/link contexts.
- [ ] Keep inih, Kilo and cJSON as continuous regressions covering normal inputs, malformed inputs and relevant failure paths.
- [ ] Inventory every Wolf unit and dependency; progress from translation to compile, link, startup and deterministic runtime checks.
- [ ] Debug Wolf crashes against native behavior with bounded reproductions, separating file lookup, ABI, memory and backend failures.
- [ ] Keep proprietary game data outside version control and generic CI; support explicit local data paths for authorized manual gameplay tests.
- [ ] Add independent projects that challenge each new semantic family so acceptance cannot overfit existing corpora.

**Acceptance:** Each corpus has an honest stage/status matrix; compile-only success is never reported as a working game or equivalent library.

### V05 — Bound memory and profile throughput [P0/P1]

**Location:** driver, AST pipeline, scripts and benchmarks. **Depends on:** B01, F02, V04.

- [ ] Start with one heavy Clang/compiler job; measure peak RSS for parent and children plus system memory pressure.
- [ ] Set configurable input/projection limits, per-process deadlines, worker count and retained-unit/cache budgets.
- [ ] Release translation-unit arenas when their data is no longer referenced; retain only required project summaries.
- [ ] Profile hot paths before optimizing, including repeated AST searches, type-string scans, JSON copies and global string storage.
- [ ] Increase concurrency only when aggregate memory remains within a calibrated host budget; prioritize avoiding swap storms.
- [ ] Terminate only owned processes on timeout, reap them and preserve bounded diagnostics/reproducers.

**Acceptance:** Repeated large-unit/project runs show bounded retained memory and documented latency/throughput without exhausting the host.

### V06 — Track and fix Elisa compiler capability gaps [P1]

**Location:** isolated stage0/stage1 worktrees; translator compatibility tests. **Depends on:** B01, V01.

- [ ] Probe every required Elisa feature through small compiling/running examples: slices, aggregate syntax, nullable functions, varargs, indexing, raw-pointer operations and foreign exports.
- [ ] Minimize backend traps, invalid LLVM, pointer truncation, layout mismatches and optimizer miscompilations before changing compiler code.
- [ ] Implement compiler fixes in isolated worktrees, add compiler-owned regressions and record dependency commits here.
- [ ] Integrate main-worktree gains by inspecting commits and dirty state, preserving local fixes and verifying the resulting compiler identity.
- [ ] Test translator and generated outputs with both compiler stages as their support permits; keep stage1 decline visible until it is actually resolved.
- [ ] Require a full translator/corpus compatibility check before switching the default local compiler.

**Acceptance:** Missing language features are implemented or accurately tracked with reproducers; default toolchains have recorded translator compatibility evidence.

### V07 — Packaging, CLI UX and reproducible releases [P1/P2]

**Location:** CLI, README, proposed docs and release scripts. **Depends on:** P04, V01, V04–V06.

- [ ] Provide explicit options for language/standard/target, compilation configuration, output policy, diagnostics, budgets and compiler/runtime paths.
- [ ] Package translator-owned support libraries and a versioned manifest without dependence on the author's directory layout.
- [ ] Document installation, standalone/library/project workflows, native dependency linking and the exact feature matrix.
- [ ] Validate macOS/Linux and additional targets through actual build/ABI tests before claiming support.
- [ ] Test release artifacts in a clean layout, record hashes/dependencies/licenses and maintain upgrade/rollback instructions.

**Acceptance:** A user translates and builds a documented supported project from the packaged release outside this workspace.

## 6. Proof obligations for readability transformations

These obligations are part of implementation, not optional documentation. Use actual compiler-valid Elisa fixtures for exact syntax.

| Desired improvement | Required evidence | Must retain the faithful form when |
|---|---|---|
| Rename a synthetic variable away | Binding/liveness proves it unnecessary or a direct source binding exists | State is still needed to represent residual unstructured flow |
| for loop → range iteration | Same start/bound/step, termination, overflow and continue behavior | The bound mutates, stepping overflows differently or induction address escapes |
| switch → simple match | Selector evaluated once; arm exits/fallthrough preserved | Conditional fallthrough requires additional structure |
| Remove a cast | Identical value representation, conversion result and ABI role | Signedness, width, pointer form or calling convention changes |
| Optional pointer → narrowed reference | Dominating proof and no intervening invalidating write/alias/call | A callback or alias can change the pointer or its validity |
| Pointer and length → slice | Proven extent, endpoint semantics, lifetime and permitted mutation | Buffer ownership/extent is unknown or external ABI needs raw pointers |
| Mutable → immutable binding | No writes through the binding and target semantics permit it | An alias/foreign operation can mutate required storage |
| Hoisted local → declaration at use | Dominance, scope entry and destruction/initialization equivalence | A jump enters the region or storage identity/lifetime changes |
| Error goto → early return/defer | Cleanup order and exactly-once behavior are equivalent | Multiple paths have different live resources or unwinding rules |
| Macro → static function | Proven expansion/evaluation/type equivalence in Elisa | Arguments repeat, short-circuit or depend on call-site tokens/scopes |
| std container → Elisa-backed adapter | Full contract for the used operations and policies | Reference stability, construction, hashing or destruction differs |
| C string → text view | Terminator/length/encoding/mutation/lifetime requirements are met | Arbitrary bytes, embedded NUL or mutable storage make it inequivalent |

Examples should demonstrate both a successful transformation and a counterexample. For example, a guard around a pointer can justify a direct use until an aliasing call; a plain name-based fact must not survive that call. A clean integer counting loop may become a range, while a loop whose body updates its bound requires the original evaluation behavior.

## 7. Verification matrix

### 7.1 Required semantic fixtures

- [ ] Integer width/signedness boundaries, char signedness, enum flags, bool conversions, shifts and division.
- [ ] Floating NaN, infinities, negative zero, literal rounding and target extended formats.
- [ ] Sequenced/short-circuit calls, increment/decrement, compound stores and side-effecting addresses.
- [ ] Const at every pointer level, null pointers, pointer-to-pointer, pointer-to-array, arithmetic, alias invalidation and 64-bit pointer round-trips.
- [ ] Nested arrays/records, anonymous members, designated/sparse initialization, padding/packing, unions, bitfields and trailing storage.
- [ ] Static locals, thread locals, external globals, shared headers and project initializers.
- [ ] Nested loops, continue, do-while, switch fallthrough, forward/backward goto and irreducible regions.
- [ ] Macro constants/functions/statement expansions, token operations, source origins and configuration variants.
- [ ] Variadic functions/calls, callbacks, aggregate ABI and foreign linkage in both directions.
- [ ] Namespaces, overloads, references, templates, constructors/destructors, capture lifetimes, inheritance and exceptions as each family lands.
- [ ] Library growth, invalidation, custom policies, allocation failure and nontrivial value lifetime.
- [ ] Invalid source, unsupported source, Clang errors, malformed projection and compiler/backend failures with distinct reports.

### 7.2 Required integration scenarios

1. Translate a single source to stdout and to a chosen output directory.
2. Translate an arguments-based and command-based compilation database with spaces and multiple configurations.
3. Translate two units with identical basenames, internal symbols and conflicting sanitized names.
4. Translate a project with shared declarations, inline headers and runtime initialization.
5. Move generated output outside the repository and rebuild it using the emitted dependency manifest.
6. Fail one unit during regeneration and verify the prior complete generation remains identifiable.
7. Change a header/define/target/compiler and verify cached semantic data is invalidated.
8. Translate the same normalized input twice and compare deterministic IR, output and manifests.
9. Run idiomatic and fidelity modes against the same native oracle.
10. Compile generated library functions into a native host and call native callbacks from generated code.
11. Run selected corpora under constrained memory and cancellation; verify process cleanup.
12. Test local Wolf startup/gameplay only with explicitly supplied user-owned data and record the exact executable/toolchain.

### 7.3 Performance evidence and proposed budgets

Establish measured workload classes before enforcing absolute latency/RSS thresholds: tiny semantic fixture, cJSON-sized unit, header-heavy C++ unit, many-unit project and the selected Wolf configuration.

Record elapsed time per phase, child/parent peak RSS, source/raw/projected bytes, node/type/declaration counts, cache size and output size. Compare cold/warm runs on the same machine and toolchain. Use configurable host budgets; initially run one heavy process and reserve substantial memory for the OS and user applications. Set concrete published thresholds from this baseline rather than inventing performance claims.

Correctness tests should be deterministic and fast enough for every slice. Larger randomized tests, release compiler matrices and memory soak runs have separate scheduled gates. A performance regression cannot be hidden by dropping dependencies or increasing unsupported coverage.

## 8. Compiler dependencies and ownership boundaries

The translator owns recognition, semantic normalization, idiom selection, compatibility policy and output generation. Clang owns C/C++ parsing, overload selection and source-target semantic facts. Elisa compilers own valid Elisa syntax/type semantics, target lowering, runtime ABI and code generation.

When Elisa lacks an essential representation, create a dependency ticket containing the smallest source example, expected semantics, actual compiler behavior, target architecture, proposed language/runtime contract and a compiler regression test. Update the translator only after the capability is validated or emit a clear unsupported diagnostic while implementation continues.

Use the existing isolated compiler worktrees under `../elisa-transpiler-worktrees/`, unless explicitly configured otherwise. Pin actual local revisions/binary hashes and record main-worktree integrations. Never infer that the newest installed executable is the intended compiler.

The `cpp` compatibility module remains in this repository. External-function declarations remain Clang-derived. LSP/editor work is outside this implementation plan; a generic source map or project manifest may be consumed by such tools later.

## 9. Initial implementation slices from the inspected state

1. **Correct and commit this roadmap:** make the active scope explicit, then establish B01's execution ledger.
2. **Fresh serial baseline:** build with local stage0, run focused fixtures and existing corpora, record exact failures and provenance.
3. **Frontend process integrity:** preserve child status and argv, validate compilation contexts and add regression cases for malformed databases/failing Clang.
4. **Memory-bound projection:** measure raw versus projected AST retention, remove avoidable full copies and prove declaration dependency closure.
5. **Canonical type/declaration foundation:** eliminate unsafe type-spelling recognition and unify project symbol/initializer naming.
6. **IR verifiers and semantic counterexamples:** establish independent correctness checks before new cleanup rules.
7. **Source module extraction:** split over-limit files with parity checks and explicit interfaces.
8. **Control-flow quality:** improve switch fallthrough, natural loops, guard exits and residual dispatcher localization.
9. **Expression and pointer facts:** proven cast/null/alias cleanup, meaningful temporaries and safe declaration placement.
10. **Relocatable project and ABI gate:** output transaction, support-library resolution, mixed native/Elisa probes and global initialization.
11. **C++ map/object contracts:** canonical adapter recognition, mapped-value construction, validity guarantees and cleanup.
12. **Wolf requirement closure:** implement every audited missing source/runtime feature generically; reproduce and fix backend/runtime failures with bounded tests.
13. **Broader C++ and library support:** follow C02–C08 and L03–L04 dependencies until their explicit acceptance gates pass.
14. **Release-quality completion:** corpus, fuzz, performance, compiler-stage and relocation gates with documented support.

Parallel work can cover independent fixture design, frontend schema research and documentation while one heavy build runs. Changes to shared IR or compiler contracts must be integrated in dependency order. Do not leave a partial compiler/API migration spread across unverified commits.

## 10. Definition of done for each slice

- [ ] The source-language behavior and intended emitted improvement are stated precisely.
- [ ] Existing implementation was audited and preserved where correct.
- [ ] The slice contains production changes and independent positive/negative regressions where needed.
- [ ] Source typing, evaluation, alias, layout, lifetime and cleanup obligations remain satisfied.
- [ ] Both output modes pass applicable tests.
- [ ] Generated output parses, compiles, links and runs at the stage claimed.
- [ ] No invalid-IR placeholder or guessed external signature is emitted.
- [ ] Production source files stay within the 600-line bound and module ownership is clear.
- [ ] Runtime/helper/compatibility dependencies are generic and demand-driven.
- [ ] Relevant memory/time evidence and local compiler identities are recorded.
- [ ] README/support matrix, fixture metadata and execution ledger reflect actual results.
- [ ] A focused commit records the verified gain, with separate compiler dependency commits when needed.

## 11. Completion audit for the full roadmap

Before declaring the goal complete, audit every work item, checklist, milestone and stated deliverable against the current repository. A status label, intent, existence of a handler or one green corpus is insufficient.

For each item, point to production implementation, precise tests and fresh results under the supported target/toolchain matrix. Mark missing, weak or indirect evidence as incomplete. Verify all explicitly planned C/C++ feature families and library contracts, all mandatory negative cases, output relocation, source-file boundaries, resource limits and release documentation.

The completed result must produce correct idiomatic Elisa for its fully documented supported inputs, preserve the required semantic and ABI contracts, explain residual low-level representations, reject invalid/unsupported requests without misleading output, and remain generic across unrelated C/C++ programs. Any deliberately deferred feature from this roadmap remains unfinished unless the user explicitly changes the goal.
