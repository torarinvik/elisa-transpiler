# Elisa C/C++ Transpiler: Implementation Plan

> Project roadmap for the Elisa-written, Clang-backed translator in this repository. Its goal is to translate supported C and C++ programs into correct, readable, maintainable, idiomatic Elisa while preserving their observable behavior.

## 1. Objective and governing requirements

Build a translator written in Elisa that uses Clang for C/C++ parsing and semantic interpretation, preserves the observable behavior of supported source programs, and recovers the clearest Elisa representation justified by the available semantic evidence.

The implementation sequence is deliberate: first make ordinary C semantics dependable; then cover C-style C++ and the genuine C++ constructs required by Wolf4SDL; then expand to the broader C++ object model and standard-library surface. cJSON, Kilo, inih and Wolf4SDL are regression corpora, not product-specific targets. Their names, function names, directory layouts and private data must never determine generic translation rules.

The scope covers the complete translation workflow: frontend invocation, semantic modeling, typed lowering, idiom recovery, Elisa emission, translator-owned compatibility libraries, project/build integration, diagnostics, performance and correctness evidence.

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
6. Prefer generic helpers to one helper per concrete type. Map C `const` to Elisa's ordinary immutable-by-default bindings and references; do not invent a redundant Elisa `const` wrapper or keyword. Preserve mutability only where the source semantics permit writes, while still respecting which side of a pointer is qualified.
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

This baseline describes the current translator worktree, not a clean checkout of `HEAD`. Fresh verification results, local compiler identities and capability skips are recorded in `docs/execution_status.md`; a feature is not considered complete merely because its handler or test fixture exists.

| Existing area | Files | Current foundation / remaining audit |
|---|---|---|
| Entry and CLI | `src/main.elisa`, `src/cli.elisa` | Direct input, compilation database and project output modes exist |
| Clang acquisition and projection | `src/clang_ast.elisa`, `src/clang_process.elisa`, `src/clang_ast_projection.elisa` | AST stdout is budgeted and spooled; compile argv, child status, schema checks and declaration-closure projection have verified foundations. Complete semantic dependency closure, phase-level memory accounting and broader Clang-version coverage remain open |
| AST/type collection | `src/clang_context.elisa`, `src/clang_typedefs.elisa`, `src/clang_ast_initializers.elisa` | Declaration lookup, typedef recovery and aggregate handling exist |
| Typed lowering | `src/lower_expr.elisa`, `src/lower_stmt.elisa` | Typed index-based IR and source-qualified unsupported diagnostics exist |
| Scalar/type semantics | `src/c_semantics.elisa`, `src/emit_types.elisa`, `src/emit_types_records.elisa` | Promotions, pointers, arrays, records and ABI-related handling exist |
| Facts and effects | `src/emit_analysis.elisa`, `src/emit_expr_facts.elisa`, `src/emit_effects.elisa`, `src/emit_places.elisa` | Null facts, mutability, places and unsafe-region reduction exist |
| Expressions and calls | `src/emit_expr.elisa`, `src/emit_expr_calls.elisa`, `src/emit_expr_support.elisa` | Cast cleanup, typed callbacks and generic foreign declarations exist |
| Control flow and output | `src/emit_cfg.elisa`, `src/emit_program.elisa`, `src/emit_statements.elisa` | Structured constructs plus CFG dispatch fallback exist |
| Formatting and metrics | `src/emit_format.elisa`, `src/emit_quality.elisa`, `scripts/quality_report.sh` | Output cleanup and source-agnostic text metrics exist |
| C++ compatibility | `src/cpp_compat.elisa`, `src/emit_record_templates.elisa`, `cpp_lib/unordered_map.elisa` | Initial map adapter exists; direct external class-template specializations with explicit type arguments, including named namespace scopes, retain distinct concrete layouts |
| Build and tests | `scripts/setup_local_compilers.sh`, `scripts/test.sh`, `testdata/` | Local compiler worktrees and native-versus-generated fixture checks exist |
| Corpora | `testdata/upstream/{inih,kilo,cJSON,wolf4sdl}` | Small C acceptance targets and exploratory Wolf source are present |

Specific findings to address without assuming the older README is a complete feature inventory:

- AST stdout is now byte-bounded and spooled to temporary storage before projection. Header-heavy inputs such as the `<unordered_map>` fixture still require a large raw JSON scan, but the projection fallback optimization below reduced the measured unsupported-policy case from beyond a minute to about 13 seconds; phase-level profiling and more scalable one-pass projection remain needed.
- Both compilation-database forms now reach the same direct `execvp` runner: `arguments` remain structured, while a tested restricted POSIX command grammar handles `command`; output/dependency flags are filtered before AST extraction. The supported host and launcher policy are documented, but broad driver-option and target/context matrices remain open.
- The current `cpp_unordered_map_bounds` scanner recognizes only `std::unordered_map` and the tested libc++/libstdc++ implementation namespace spellings, not an unqualified same-named user template. This is a useful fail-closed spelling boundary, not canonical declaration identity; AST declaration resolution and alias handling remain open.
- The unordered-map adapter now boxes its mapped value in an Elisa entry so nullable pointers are ordinary fields rather than nullable dictionary elements. The emitter projects `.value` only at recognized C++ map subscripts. Stage1 generic `Index` field typing was fixed in the isolated compiler worktree and has a focused regression; translator fixtures cover integer and nullable `const char *` values, including default-null insertion. For a newly inserted supported `V`, the adapter reads `[0]` from a zeroed `V` box before storing it: `arena_box_zeroed[V]` alone is a heap reference, not a zero-valued `V`. Class construction, function-pointer values and pointer keys remain outside the supported subset.
- `cpp_lib/unordered_map.elisa` and the main entry contain relative compiler-worktree includes, and compatibility output assumes a normal build-directory layout.
- Generated project module filenames have occurrence-based collision handling, while initializer names derive separately from basenames; naming must share one project symbol registry.
- At plan-audit baseline, eight translator source files exceeded 600 lines; these have since been split and the maintained `src/` plus `cpp_lib/` trees now have an enforced bound.
- At plan-audit baseline, the 654-line test script mixed building, structural assertions, linking and runtime comparisons; its tests now live in focused sourced suites behind one canonical entry point.

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

- [x] Inventory current tracked/untracked changes, compiler worktree revisions and executable hashes; preserve unrelated work and establish which changes belong to this roadmap.
  - [x] Capture dated preservation and re-audit records in `docs/worktree_inventory.md`. The initial 2026-10-05 inventory records translator commit `7c794ad`, a clean translator worktree after that commit, Stage0 main/private worktrees at `6a0628cc48a7`, Stage1 main/private worktrees at `8e08cd3397b1`, the intended local Stage1 standard-library symlink, and hashes for those compiler products. The isolated source worktrees were fast-forwarded later the same day; the subsequent source/artifact split and stale-product state are recorded below and in `docs/compiler_compatibility.json`. The memory/ABI safety slice is committed separately as translator work; ignored build outputs and upstream fixtures were left untouched.
- [x] Verify stage0, stage1 and runtime paths resolve to the intended isolated worktrees; explicitly supplied invalid paths must fail without silently selecting an installed compiler. Stage0 is checked for every run; suites needing project compilation fail early when stage1, its driver or its runtime object is absent.
- [x] Fast-forward the isolated compiler source worktrees from their respective committed `main` heads without touching dirty main checkouts: Stage0 `6a0628cc` → `11858f2e`, Stage1 `8e08cd33` → `2691a64c`. The compatibility manifest distinguishes current source revisions from older executable/runtime artifact revisions and marks freshness false until rebuilt. Uncommitted main-checkout edits remain intentionally unmerged.
- [x] Build the translator with the explicit local stage0 compiler and record the source/toolchain fingerprint, target, flags, runtime and Clang identity in `docs/execution_status.md` and `build/translator-build.fingerprint`.
- [ ] Run the fixture and upstream corpus checks serially with deadlines; separate expected skips from translator mismatches, frontend failures and compiler/backend failures.
  - [x] Re-audit compiler freshness after the initial 2026-10-05 inventory. The earlier 6a0628cc/8e08cd33 product snapshot is historical: isolated Stage0 and Stage1 sources now match committed `main` at `11858f2e`/`2691a64c`, while the checked-in executables/runtime remain from the older revisions. The compatibility manifest marks both stale; rebuild and bootstrap reproduction remain open.
  - [x] Keep the private Stage0 worktree synchronized with local `main` without changing the main checkout. Historical synchronization verified both at `6a0628cc48a7` with private executable SHA-256 `15254cdbf96c981b0c0cc31a65b95357761801aee2db08884e5a05b76c9c89a3`; this snapshot was superseded by the later isolated-source fast-forward to `11858f2e`. The executable remains from the older revision, as recorded in the compatibility manifest.
  - [x] Remove nine Stage0 parse failures by parenthesizing effectful calls used in postfix `return … if …` expressions; the fresh compiler then parses the translator and advances to its region/borrow analysis.
  - [x] Reconcile the private Stage1 compiler worktree with `main` while preserving its local state. Historical synchronization verified clean main/private checkouts at `8e08cd3397b1`; this snapshot was superseded by the later isolated-source fast-forward to `2691a64c`, and the main checkout remains untouched by translator work. A later check found a modified tracked `.DS_Store` in the private Stage1 checkout; it is preserved and the compatibility manifest now records the worktree as dirty rather than claiming a clean tree.
  - [ ] Independently reproduce a Stage1 seed from the refreshed private Stage0 compiler, then rerun translator fixtures/corpora. The private Stage1 executable/runtime were copied byte-for-byte from the clean Stage1 main checkout and freshness was verified when its source was `8e08cd3397b1680c61bfb76b70e1a76541522e3d`; their hashes are `f7d4dc3c2a2a126da19723abdcd806bf99f08a71cc8bf15a35c2f508e2e19b9d` (executable) and `b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897` (runtime). Those artifacts are now stale because the isolated Stage1 source advanced to `2691a64c`; the Stage0 executable is likewise from `6a0628cc`, not its refreshed `11858f2e` source. The compatibility manifest correctly marks both products stale and translator validation pending. A previous bounded `-O3` seed reached the physical-footprint safety threshold (4,672,374 KiB peak footprint / 3,051,056 KiB peak process-group RSS; 4,669,440 KiB threshold under the existing 6-GiB cap). Do not raise that ceiling; reduce bootstrap peak or wait for a safe bounded build window. The translator executable hash `8f24c7644167bd5b2c8680d97e0a4b945fb3957c28c54dd38637ea5b30a2b771` is historical and was compiled against the then-matching older Stage1/runtime; it does not verify current translator sources or refreshed compiler sources.
  - [x] Run `sh scripts/test.sh --suite fixtures --reuse-build` after unordered-map enum-key support. The isolated stage0 build was refreshed, frontend checks passed, all 12 manifest cases passed, and the C++ adapter fixtures completed; cJSON nullable-function executable parity was explicitly capability-skipped. Evidence and toolchain hashes are recorded in `docs/execution_status.md` (2026-09-14).
  - [x] Re-run the 13-case semantic manifest and focused C++ adapter checks against the current isolated stage1 product and matching runtime. The call-result/literal mixed-width regression is fixed generically; the complete fixture sweep reaches all 13 manifest passes, while the longer header-heavy tail remains host-timeout-prone and is kept separate from the bounded acceptance result.
  - [x] Run the scripted upstream smoke corpus against a rebuilt translator and record per-project translation, compilation, link, runtime and capability status. On 2026-09-30, inih, cJSON and Kilo all translated; inih compiled/linked and matched native output, exit codes and diagnostics for sample, no-argument and missing-file runs; cJSON compiled/linked and matched native smoke output with nullable-function support enabled; Kilo compiled/linked and matched the native no-argument exit/output/diagnostics. This suite does not run Wolf4SDL's interactive/gameplay path, which remains separately open in V07.
  - [x] Re-run the 21-case acceptance manifest serially with per-stage process-group RSS and output limits (rather than limiting only the manifest coordinator). All 126 translate/build/link/run stages passed with a 120-second stage deadline, a configured 1.5-GiB RSS cap and a 64-MiB combined stdout/stderr cap; no stage timed out, crashed, hit a cap, or failed monitoring. The run peaked at 77,248 KiB sampled aggregate RSS. Runner regressions cover a PID disappearing during a macOS footprint sample and a child crossing a small output cap.
- [ ] Record one evidence row per feature: source fixture, emitted artifact, compile/link result, runtime result and remaining limitation.
  - [x] Record the fresh fixture-suite result, generated/native C++ adapter parity and the cJSON capability skip in `docs/execution_status.md`; completing evidence for every planned feature remains open.

**Acceptance:** A new contributor can reproduce the baseline from recorded inputs; every claimed passing feature points to a fresh result.

### B02 — Split and strengthen the test driver [P0/P1]

**Location:** scripts/test.sh, scripts/test_support.sh, scripts/test_test_support.sh, scripts/build_cache.sh, scripts/test_build_cache.sh, scripts/run_fixture_manifest.py, testdata/fixtures/acceptance_manifest.json. **Depends on:** B01.

- [x] Move the canonical translator build/setup into `scripts/test.sh` and divide translation/behavior checks into sourced focused fixture, project-generation, control-flow and upstream suites.
- [x] Keep `sh scripts/test.sh` as the canonical full entry; add documented focused selections and a reuse-build mode fingerprinted from translator/compatibility sources, compiler, Clang, platform and build flags, with a built-binary hash check.
- [x] Represent native and Elisa build/link arguments as arrays in a fixture manifest; do not rely on one universal linker command for every platform. Three initial acceptance cases cover C, the C++-compatible subset, and readonly-pointer helper emission.
- [x] Capture exit status, stdout, stderr and selected produced files; support expected nonzero exit codes and binary outputs. Runner self-tests exercise independent streams, exit 42, object/executable capture, and native-versus-Elisa comparisons.
- [x] Report timeouts, crashes, skips, unsupported cases, missing tools, resource limits, monitor failures and pass/fail totals distinctly; validate manifest schema, deadlines and safe case names before running.
- [x] Enforce aggregate RSS/process-footprint and combined stdout/stderr limits on each owned manifest stage, not on the manifest coordinator; spool child output directly to files and kill/reap only the owned stage process group on a limit breach. A 21-case/126-stage run passed under a 1.5-GiB RSS and 64-MiB output cap; regressions cover a process exiting during footprint sampling and a child crossing an output cap.
- [x] On macOS, add an optional host-wide free-memory floor to bounded compiler/translator builds and every manifest stage. Refuse launch at or below the configured floor, sample while the owned process group runs, terminate only that group on a breach, and fail closed if the host sampler fails. `ELISA_SETUP_MIN_SYSTEM_FREE_PERCENT` defaults to 41% for local compiler setup and 60% for the canonical test driver; both values are configurable and inherited by child runners. Unit regressions cover environment propagation, preflight refusal, live-floor termination and sampler failure. The latest runner/manifest suites pass 12 and 20 tests respectively.
- [x] Route direct translator, Elisa compiler, Clang and Clang++ invocations in all four sourced shell suites through the bounded process-group runner, with configurable per-tool RSS ceilings and deadlines. Keep successful resource telemetry off child stderr so typed-IR dumps and exact diagnostics stay deterministic; failures still include resource-limit reports. Stage1 driver invocations retain their own process-group limits and inherit the test driver's host-memory floor. Fake-command regressions check argv boundaries, stdout/stderr fidelity and exit-code propagation.
- [x] Run compiler/translator integration probes under one aggregate process-group RSS/footprint cap and deadline so the Python harness, Clang JSON capture and nested compiler children share the same budget. The canonical test-driver self-test asserts every compiler-bearing probe is routed through the wrapper. Invoking an individual probe script outside `scripts/test.sh` remains the caller's responsibility.
- [x] Add a validated semantic-family taxonomy to the acceptance manifest and propagate it into each per-case result, including skipped and failed cases. Quality coverage can report pass/fail/unsupported outcomes by family and join older summaries with the selected manifest; regressions check complete classification, known tags, per-case propagation, malformed summaries, and family-level rates.
- [x] Attribute unexpected shell-suite failures to the sourced script, line and command on Bash hosts, while leaving other POSIX shells functional and suppressing reports for `!`/`set +e` expected failures. A focused self-test deliberately fails in a sourced input and verifies both exact attribution and expected-failure silence; `/bin/sh -n` and Bash syntax checks pass.
- [x] Forward the explicitly selected stage1 runtime object to the manifest runner so generated Elisa links use the same compiler/runtime pair. A runner regression verifies that the runtime is appended only to Elisa links, never native builds; all 19 selected cases pass with the isolated stage1 compiler and matching runtime.

**Acceptance:** Runner self-tests prove mismatched output, wrong exit status, crash, timeout, unsupported translation, missing tool and malformed manifests are attributed to their proper stage. The shared build-cache self-test proves stale source fingerprints, changed executable bytes and non-executable outputs cannot be reused; only a matching source fingerprint plus executable hash is accepted.

### B03 — Restore source-size and namespace discipline [P1]

**Location:** src/clang_ast.elisa, src/emit_* and src/lower_expr.elisa. **Depends on:** B01–B02.

- [x] Measure actual file lengths and split every production Elisa source file over 600 lines along responsibilities. AST capture/access and projection, type/record emission, expression emission, CFG building/emission, statement emission and switch/condition lowering now have bounded source modules.
- [ ] Introduce explicit module interfaces for frontend, IR, analysis, transforms and output while proving Elisa include/extend behavior in small compilable changes.
  - [x] Extract Clang declaration-kind classification, location-retention rules and macro-origin detection into `src/clang_ast_projection_schema.elisa`; `main.elisa` includes this schema boundary before recursive projection. The compact-projection schema and real-Clang frontend checks pass with the isolated Stage1 compiler. This establishes one narrow frontend boundary; the broader frontend/IR/analysis/transform/output interfaces remain open.
- [ ] Keep public symbols narrow, avoid cyclic module ownership and eliminate accidental reliance on include order.
- [x] Preserve existing output and behavior during each extraction; do not combine a large refactor with semantic rewrites. The full acceptance suite passes and the cJSON translation remains byte-identical after extraction.
- [x] Add a source-file length gate with an explicit generated-file policy; split the test driver into focused suites. The gate covers maintained `.elisa` files under `src/` and `cpp_lib/`; generated outputs under `build/` are excluded.

**Acceptance:** Every maintained translator source file is at most 600 lines and the existing semantic suite passes after extraction.

### B04 — Maintain an evidence ledger and steady commits [P1]

**Location:** proposed docs/execution_status.md and docs/decisions/. **Depends on:** B01.

- [ ] Link every work-item status to its implementation commit, tests, toolchain context and unresolved requirements.
- [ ] Use one reviewable commit per verified slice where practical; include the minimized regression with the fix.
- [x] Keep compiler fixes in their owning isolated repositories and record their commit IDs in the translator compatibility manifest. `docs/compiler_compatibility.json` records the isolated Stage0 and Stage1 source revisions, cleanliness, executable/runtime hashes, and Stage1 provenance; its translator-validation status remains explicitly pending. The manifest hash participates in the translator build-cache fingerprint and has a mutation regression. This records provenance, not current-source behavior compatibility.
- [x] Record architecture decisions for pointer/object immutability, C++ ABI wrappers and transactional output packaging in `docs/decisions/`; projection, typed IR, object lifetime and source mapping decisions remain open until their full semantic contracts are implemented.
- [ ] Update README support claims when behavior changes; never mark a whole work item complete from one happy-path fixture.

**Acceptance:** The ledger distinguishes implemented, tested and still-unverified work without relying on conversational history.

## 5.2 Clang frontend and compilation context

### F01 — Preserve compilation commands exactly [P0]

**Location:** src/cli.elisa, src/clang_ast.elisa; proposed frontend/process.elisa. **Depends on:** B02.

- [x] Retain compilation-database `arguments` arrays as structured JSON argv on each source entry; do not flatten them into command text and tokenize them again. Execute these arrays with `execvp`, copy each JSON slice into stable NUL-terminated argv storage, and apply the entry's working directory in the child process.
- [x] Capture direct-argv Clang stdout, stderr and exit status independently, enforce the AST byte budget while streaming stdout, and terminate/reap the dedicated process group when capture fails or exceeds the cap. A regression covers paths with spaces and the bounded-output failure path.
- [x] Replace shell transport for `command` strings with restricted POSIX-like tokenization and the shared direct-`execvp` process API. Preserve quote/escape token boundaries, support leading `NAME=value` environment assignments via `env`, and reject shell expansion/control syntax before launch. This is not a general shell parser.
- [x] Define and test the command-string grammar for supported POSIX hosts: whitespace-delimited argv, single/double quotes and documented backslash escapes; reject shell expansion/control syntax before launch and report invalid commands against the compile-database source. `arguments` arrays bypass command-string decoding. Windows command-line decoding is explicitly unsupported until the process layer has a Windows implementation.
- [x] Normalize known build-output/dependency-generation options that conflict with AST extraction (`-c`/`-S`/`-E`, `-o`, dependency output/target flags, serialized diagnostics, save-temps and time-trace outputs); preserve semantic argv words such as `-std`, `-x`, target, ABI, defines, includes and forced includes. A regression confirms translated output stays correct and no object/dependency/diagnostic/temp artifacts are created.
- [x] Preserve quoted paths containing spaces in both database forms; the command and argv fixtures resolve an include directory with spaces.
- [x] Expand explicit Clang `@file` response arguments before option normalization in both `arguments` and restricted `command` entries. Resolve relative and nested response-file names against the compile entry's working directory; accept empty files; tokenize with the documented restricted POSIX-like quote/escape grammar; cap recursion at 16 files, expanded words at 1,000,000, and cumulative response bytes at `--max-frontend-output-bytes`. Regressions cover nested files, quoted include paths, normalized output/dependency flags, both database forms, empty and missing files, byte-budget rejection, and a self-referential cycle.
- [x] Preserve response-expansion failure kind and offending file path through compile-database preflight. Report unreadable files, cumulative byte-budget overruns, nesting/argv limits and malformed response syntax with the response path and owning source; reject before Clang launch or project output. Regressions cover missing, malformed-quote, oversized and cyclic files.
- [ ] When dependency-aware project caching is implemented (F06), include response-file paths and their transitive nested contents in dependency discovery, cache keys and invalidation; response files are currently bounded and consumed but are not tracked as cached dependencies.
- [x] Define launcher behavior: execute argv[0] directly with `execvp`, with no implicit shell or inferred wrapper chain. Leading `NAME=value` command prefixes lower to `env`; explicit launchers remain ordinary argv and must be available on `PATH` and forward appended Clang options. Regression coverage proves shorthand and explicit `env` entries normalize identically and collapse to one translation.
- [x] Collapse duplicate entries with the same lexical source identity, working directory and decoded argv (or exact command string); reject differing compiler settings before writing any project modules. Regressions verify one module for identical entries and clean failure for conflicting defines.
- [x] Extend duplicate detection to canonical filesystem aliases for existing sources; preserve cwd and compiler settings as conflict keys. Regress equivalent aliases (one emitted module) and conflicting settings through aliases (rejected before output).
- [x] Compare `command` and `arguments` entries by normalized effective argv rather than representation, including expanded response files and normalized output/dependency switches; keep cwd significant because it changes relative include/response-file meaning. Regress equal commands as one module and different normalized flags as a pre-output conflict.
- [x] Apply independent stdout/stderr capture and child-status handling uniformly to `arguments` and tokenized `command` entries; propagate Clang failure even when it emitted partial JSON.
- [x] Stop injecting `_DEFAULT_SOURCE` or disabling fortify with unconditional `_FORTIFY_SOURCE` overrides in direct-input mode; a preprocessor regression protects this behavior.
- [x] Make database language/standard selection explicit and verify `-x c++` plus `-std=gnu++11` overrides a `.c` suffix while preserving `-D`; compile/link/run generated Elisa and compare its exit with native Clang. Document the direct-input standard fallback (C11 or GNU C++11 by suffix).

**Acceptance:** A matrix of direct inputs and databases reproduces native frontend contexts and never reports success after Clang failure.

### F02 — Bound AST acquisition and projection memory [P0/P1]

**Location:** src/clang_ast_filter.elisa, src/clang_ast.elisa, src/clang_ast_projection.elisa, src/clang_ast_dependencies.elisa. **Depends on:** F01.

- [x] Measure raw JSON bytes, retained projection bytes, parsed JSON values and arena payload, plus separate Clang/translator memory for the cJSON baseline; continue gathering corpora and reliable process-tree peak measurements.
- [x] Preflight projected JSON value count before DOM allocation; make the 1,000,000-value default configurable and verify rejection occurs before arena growth.
- [x] Stream Clang AST stdout to an auto-deleted temporary file under the configured byte budget; map it read-only only during projection and write projected JSON into caller-owned storage, avoiding simultaneous full-size raw and compact heap arrays. cJSON output is byte-identical; sampled process-tree RSS fell about 38% in repeated runs.
- [ ] Preserve a complete transitive dependency closure of referenced declarations, canonical types, layout, inline definitions and template specializations; source-directory membership alone is insufficient.
  - [x] Compute a one-pass closure over explicit Clang declaration-ID edges and nested declaration ownership, then carry an internal `elisaDependency` marker through the compact AST so the typed type collector does not discard ID-retained declarations based on their external source location. The real-Clang regression uses `LeafAlias -> HiddenAlias -> Hidden`, hides all three declarations from source-path heuristics, strips the desugared `Hidden` spelling from the source AST, checks the generated record's `sizeof` against native C, and compiles/links/runs with matching behavior using the latest upstream stage1 compiler.
  - [x] Recover this bounded ID-less C layout edge: for a by-value record field whose Clang type spelling has no declaration ID, map a uniquely named unqualified elaborated tag to its declaration ID before dependency closure; if a separate declaration with the same spelling exists, fail closed rather than choose a layout by name. A real-Clang regression strips the tag spelling from source-owned nodes, externalizes the record declarations, checks the complete field layout is emitted, injects an unrelated duplicate tag and verifies neither layout is selected, then compiles/links/runs generated Elisa against native C with the live-upstream Elisa compiler. This does not establish canonical type identity or broader C++ scoped-type handling.
  - [x] Resolve a bare unqualified class/record type spelling when the Clang AST lacks a declaration ID and the name index has exactly one explicit candidate. Exclude implicit injected-class-name declarations; block bare-name fallback when a typedef/using alias has the same spelling, while preserving explicit `struct`/`class` tag resolution; reject duplicate unqualified candidates. Real-Clang C and C++ regressions cover a C tag/typedef collision, an external C++ by-value field spelled only `Layout`, injected-class-name filtering, and ambiguity rejection; generated Elisa compiles, links and matches native execution with the latest upstream stage1 product.
  - [x] Follow a source call's declaration-only ID to an external-header inline definition through the generic `previousDecl` redeclaration edge. The real-Clang fixture pins `DeclRefExpr.referencedDecl` to the prototype ID, externalizes both helper declarations, removes their `isUsed` hints, verifies that the body-bearing definition is projected, then compiles/links and matches native C behavior using the local Stage1 compiler/runtime pair. This proves the observed C inline redeclaration shape, not C++ member/namespace canonical type identity.
  - [x] Retain main-source function declarations/definitions whose export macro leaves Clang without a repeated `loc.file` and with `isUsed` absent, by recognizing a source-owned `range.begin.expansionLoc` rather than guessing from the function name. `macro_exported_api.c` reproduces the metadata gap after a prior declaration; its otherwise unreferenced API function is emitted, compiled, linked with a separate C harness and matches native execution. This is generic source-provenance handling, not cJSON-specific retention. The full cJSON source now emits 120 definitions, but compile/link/runtime acceptance remains open because the selected Stage1 backends decline several bodies.
  - [x] Retain an external C++ class-template specialization reached through a source variable's `typeAliasDeclId` and the alias's `RecordType.decl` ID. The fixture externalizes the alias and template, removes `isUsed`/`isReferenced` hints, strips source-expression desugared type spellings, verifies the specialized field layout and preserved alias value type, then compiles/links/runs with native parity on the isolated Stage1 compiler/runtime. Projection extracts only ID-reached specializations from the `ClassTemplateDecl.inner` array instead of retaining the entire primary-template subtree. This covers an alias-backed class specialization only, not direct template-valued declarations, function-template instantiation or class member/template bodies.
  - [x] Lower direct external class-template value specializations with explicit type arguments, scalar non-type arguments and a tested subset of omitted defaults from global and named namespace scopes into concrete Elisa records. The projector uses ordered primary-template parameter declarations; boolean `0/1` values normalize only for `bool` parameters, and omitted suffixes match only when Clang provides a supported concrete default equal to the specialization argument. Omitted source spellings alias the canonical fully specified specialization, preventing `Buffer<>` and `Buffer<4>` from becoming distinct Elisa types. The direct fixture covers type/integer/bool arguments, signed values, fixed-array extents, integer-literal/type defaults and nonmatching explicit arguments; native/generated behavior agrees at Stage1 `-O0` and `-O2`. A compound default expression with no projected scalar value is explicitly verified to fail closed. This remains spelling-based, not canonical template identity: dependent or unsupported default expressions, enum/pointer/floating/structural values, packs, partial specializations, member templates and function-template bodies remain open.
  - [ ] Cover remaining dependency relationships: canonical record/type identity across qualified/scoped names, inline C++ member/template definitions, additional template-specialization shapes and Clang versions/schemas. General source type-name retention remains a conservative fallback, not proof of canonical declaration identity.
- [x] Define and enforce compact semantic projection schema v2 with translation decisions implemented in Elisa.
  - [x] Emitted roots carry `elisaProjectionVersion: 2`, and typed translation rejects missing, mistyped, fractional, duplicate or unsupported versions before declaration indexing/lowering. Keep raw Clang root validation separate, so the translator-owned marker is never required from (or trusted in) Clang input. A dedicated Elisa-level schema test covers all six cases: v2 accepted; missing, wrong type, fractional, duplicate, and unsupported versions rejected. This versions the existing projection envelope and dependency markers.
- [ ] Audit semantic-fact gaps; prototype a small Clang API extractor/binding only if JSON cannot supply required facts, keeping translation decisions in Elisa. Canonical type identity, omitted semantic facts and cross-version Clang contracts remain open.
- [x] Strictly scan raw Clang JSON before projection, including string escapes, primitive tokens, number grammar, container delimiters and depth; preserve malformed input for the normal parser instead of letting projection hide it.
- [x] Decode Clang JSON path strings consistently in every source-identity predicate; an end-to-end fixture translates, compiles, and behavior-compares a C file beneath a directory containing JSON-escaped quotes/backslashes and UTF-8. A 2026-09-29 regression was traced to a legacy main-source check comparing the raw escaped JSON value while the other predicates decoded it. It now delegates to the canonical JSON-aware matcher. The original path fixture again emits all four functions, compiles with the isolated Stage1 compiler and returns the same exit code (42) as native C. The broader fixture command reached its final switch-selector case but returned nonzero without a diagnostic; therefore the suite is not yet recorded green.
- [ ] Test omitted/inherited source locations across supported Clang schema variants; escaped-path coverage alone does not prove source-origin inheritance.
  - [x] On Homebrew Clang 23.1.1 / Darwin arm64, carry source-versus-external provenance across top-level declaration siblings and through nested `inner`/`type` nodes when `loc.file` is omitted. Treat an `includedFrom`-only location as external regardless of inherited source context; an explicit location resolving to the main file takes precedence. The real-Clang fixture puts a header in a separate include directory, verifies the `Hidden` typedef chain remains reachable through declaration IDs, and rejects an unused external alias, record and inline helper; its generated layout check compiles, links and matches native C with the latest upstream Elisa stage1 compiler. Other Clang schemas remain unverified.
  - [x] Preserve same-directory project-header definitions: `header_inline.cpp` emits both `triple_value` and `add_one_value` despite omitted `loc.file` entries. Latest-upstream Elisa compilation and native/generated execution both exit 0.
  - [x] Simulate a Clang schema with an `includedFrom`-only location on an external declaration after a main-file sibling; the classifier must keep the declaration external despite inherited source context. This covers the omitted-file provenance edge; additional installed Clang versions remain unverified.
  - [x] Preserve complete anonymous typedef record layouts from an implementation file included directly into the translation unit when Clang elides its file path on later siblings. Keep offset-only nested ranges in included-file provenance and do not let translation-unit-wide `isUsed` hints retain unreachable included functions. The updated real-Clang fixture checks that both layouts survive while `anonymous_unused_dependency` and its unused caller are omitted. Fresh translator rebuild stats: raw AST 259,142 bytes; projected AST 45,226 bytes; 2,245 JSON values. Generated Elisa compiled with isolated Stage1, linked against its matching runtime, and exited 0 alongside native C. The core-fixture assertion was added; a full suite remains pending.
  - [x] Localize and fix the two-unit project-mode crash generically. The 2026-09-29 macOS crash report and exact-binary disassembly identify `typed_project_function_has_arity` reading the global project-function darray after the first translation-unit region had been destroyed. Project tables now append through `arena_da_append` into a dedicated `translator_project_arena`, so their buffers survive per-unit reclamation without retaining ASTs. The existing three-unit `module_a`/`module_b` regression now translates, compiles with the local Stage1 compiler and matching runtime, and exits 0 like native C. The two-file cJSON project (`cJSON.c` + `cJSON_Utils.c`) now emits both Elisa modules (1,661 and 1,074 lines) and its manifest under a 1.5-GiB process-group cap; observed peaks were 649,728 KiB RSS and 804,962 KiB physical footprint. This validates project translation only, not execution of the large generated project.
  - [x] Exercise the same project state across four translation units, including extern-object compatibility, in both compile-database orders. The generated manifests match byte-for-byte; both projects compile with the isolated Stage1 compiler and matching runtime, and both exit 0 like native C.
  - [x] Validate the single-translation-unit cJSON smoke path after fixing the generic const-qualified function-pointer declarator parser. Fresh output is 85,379 bytes / 1,573 lines across 37 functions; it compiles and links with the isolated Stage1 compiler and matching runtime, and native/generated smoke output is identical (`{"name":"elisa","items":[1,true,null]}`). A direct generated-LLVM verification check reports no invalid-IR markers. This verifies the smoke translation, not all cJSON API behavior or the larger multi-translation-unit utility project.
  - [ ] Complete full cJSON corpus and multi-translation-unit project compile/link/runtime parity, including explicit `Parse_buffer`/`C_error` layout checks. Main-source export-macro retention now yields a 2,789-line standalone `cJSON.c` translation with 120 definitions, and the 1,605-line smoke still compiles and matches native C. Full compilation is still blocked: the pinned isolated Stage1 backend declines `cJSON_CreateStringArray`'s pointer-array index expression; the newer main-worktree product declines seven bodies involving index expressions/assignments. No partial object is emitted, and multi-translation-unit runtime parity remains unverified.
- [x] Test maximum-depth and over-depth ASTs plus missing declaration dependencies with bounded, source-qualified failures. `scripts/test_ast_depth.py`, direct/missing declaration-dependency regressions and the depth-256/depth-257 checks all pass on the source-fresh upstream Stage1 translator build recorded in `docs/execution_status.md`; over-depth/missing-dependency failures produce no partial Elisa and identify the source. Broader transitive closure limitations remain tracked below.
  - [x] Generate a valid AST exactly at the JSON nesting limit and one level beyond it. The boundary input translates; the over-depth input emits no partial Elisa and fails with a source-qualified invalid/over-depth diagnostic.
  - [x] Collect directly referenced declaration and type-declaration IDs from source-owned AST nodes before projection; preserve matching top-level declarations even when source-location heuristics and Clang's `isUsed` marker would drop them. A real-Clang regression removes a call-site signature, moves the declaration out of source provenance and removes `isUsed`; ID-based projection retains the declaration and recovers its external signature.
  - [x] Remove a source-defined function declaration and its reference type metadata from a real Clang AST. Lowering now fails without partial Elisa and names the missing declaration dependency instead of synthesizing `int (...)`.
  - [x] Compute and retain transitive closure for explicit declaration-ID references through a multi-alias type chain; assert the source AST has no spelling of the hidden record, retain every declaration through projection and typed collection, then compile/link/run and compare with native C using current upstream Elisa stage1.
  - [x] Keep the growing dependency-closure worklist independent of borrowed AST string-view lifetimes by queuing stable graph-node indices. The latest Stage1 ownership diagnostic caught the prior loop-carried `darray[sview]` pattern; direct, transitive-layout and inline-redeclaration closure regressions now pass with that compiler/runtime pair.
  - [ ] Extend ID-less layout/type edges beyond the verified unique unqualified C record-field case; cover inline definitions, templates/specializations, additional declaration kinds and compiler/schema variants.
- [x] Make dependency/source-fact walkers return the end cursor of the subtree they already traversed. Parent array/object loops reuse that cursor instead of calling the generic JSON skipper over the same child a second time; the projection pass also reuses first-pass top-level source-state facts. cJSON output and native/generated parity remain unchanged, while the generic primitive-value fallback still advances safely through non-object arrays.
- [x] Avoid retaining every `LinkageSpecDecl` wrapper in large C++ projections. Linkage wrappers are retained only when source/dependency evidence requires them; this removes 1,048 unused Wolf4SDL wrappers without a corpus-specific name rule and lets the generic projection pass reach emission under the configured value budget.
- [x] Keep the declaration type-index alias table allocation-free and owned by the index itself. A fixed open-addressed table avoids region-polymorphic borrows of nested darray-bearing fields during Clang JSON scanning; if the bounded alias table overflows, bare-name layout lookup fails closed instead of guessing. The refreshed isolated stage0/stage1 pair builds the translator and passes the declaration-closure and unqualified-layout regressions.
- [x] Avoid recursive semantic fallback scans over unrelated JSON fields in header-heavy ASTs. Enum-retention searches now inspect direct declaration metadata and recurse only through Clang's `inner` containment, and the fallback is skipped when the source walk found no enum evidence; dependency-ID closure remains the authoritative retention path. The generic `cpp_unordered_map_unsupported.cpp` real-Clang regression still reports all three unsupported policies with empty output, while its 113 MiB AST completes in about 13 seconds on the local arm64 host. This is a projection-cost optimization, not a C++ library special case.

**Acceptance:** Header-heavy fixtures preserve all needed semantics, produce equivalent IR and stay within a measured configurable memory budget.

### F03 — Canonical declarations, source origins and diagnostics [P0/P1]

**Location:** src/clang_context.elisa, src/clang_ast.elisa, src/clang_ast_filter.elisa, src/clang_ast_projection.elisa, src/cli.elisa; proposed frontend/symbols.elisa. **Depends on:** F01–F02.

- [x] Build one translation-unit-scoped, open-addressed declaration-ID index before semantic collection. Retain each declaration node, a complete record definition when present, its `previousDecl` edge and the resolved canonical ID; route declaration, record, typedef-alias, inline-function, external-signature and declaration-classification resolution through the index. Rehash at a bounded load factor and discard the index with the translation context/AST arena. The old repeated whole-AST ID/record search helpers are removed. Regress C control-flow/provenance fixtures, a 36-global C unit that forces table growth alongside a prototype/definition pair, a deterministic typed-IR assertion that the referenced definition is noncanonical and has a predecessor, and a multi-file forward declaration/definition project through stage1 compile and execution.
- [ ] Separate physical path, spelling location, expansion location, owning translation unit and source hash.
- [x] Match Clang AST source locations to compilation-database `file` paths by canonical filesystem identity using the compilation entry's working directory, and normalize matching projected `file` fields so later DOM-based ownership filters preserve declarations. Regress both `command` and `arguments` entries when the database path is absolute but an `@response` source operand and Clang location are relative.
- [x] Resolve the main translation unit's physical path once per AST projection and reuse it for raw-location identity checks. Preserve the database/source spelling for the main-file origin, and normalize only exact physical-file matches; same-directory membership may retain sibling project headers but must not rewrite their origin as the main file. Regress a symlink spelling in `file` against the physical source operand in both database forms.
- [x] Store canonical source identity for existing compilation-database entries and use it to collapse equivalent filesystem aliases or reject conflicting settings; preserve lexical fallback for unresolved paths. Regression coverage includes `..` aliases.
- [x] Validate the effective source operand after response-file expansion and argv normalization against the compilation-database `file`; recognize separate-argument compiler options so option values are not mistaken for sources. Reject missing/mismatched operands before writing project output. Regress direct and response-file source mismatches in both `command` and `arguments` forms.
- [ ] Carry canonical physical source identity into source-qualified diagnostic/origin records while retaining user spelling, macro spelling and macro expansion locations as distinct values. Diagnostics now store canonical physical paths alongside all three path spellings; full origin identity still needs declaration/source hashes, include ancestry and source-map records.
  - [x] Preserve Clang macro spelling and expansion filenames when explicitly present, plus their line/column coordinates, on unsupported-feature diagnostics; include both origins in the diagnostic and deduplication identity. Resolve explicit paths against the Clang working directory for physical identity while retaining raw display spellings, and reuse already-resolved identities for repeated file spellings in a translation unit. Preserve Clang's explicit immediate `includedFrom.file` edge and its canonical path as separate origin data; do not present it as a full include chain. Where Clang omits `file`, use the translation-unit spelling as the current fallback. Regress a translation-unit macro, a header macro expanded in two separate functions, compilation-database working-directory resolution, a translation-unit symlink alias, and a macro in a nested include. Reliable inherited-file reconstruction, transitive include ancestry, source hashes and full origin/source-map records remain open.
- [ ] Retain source names, linker/mangled names, internal/external linkage, visibility and language linkage as distinct fields.
- [ ] Deduplicate diagnostics by semantic issue and precise source origin without merging different macro expansions or units.
- [ ] Make missing referenced declarations a projection/lowering error with a dependency trail rather than guessing a type.
  - [x] Include the enclosing source function in a direct missing-function-dependency diagnostic (`main -> add`); the real-Clang regression removes `add` and its call-site signature and verifies the path, no partial Elisa and no guessed signature. Transitive/multi-hop dependency explanations remain open.

**Acceptance:** Forward declarations, repeated headers, extern C, static same-name functions and macro-origin diagnostics retain correct identities.

### F04 — Use a structured target-aware type model [P0]

**Location:** src/clang_target_abi.elisa, src/cli_target_abi.elisa, src/c_semantics.elisa, src/clang_type_shape.elisa, src/emit_types.elisa, src/emit_types_records.elisa, src/clang_typedefs.elisa and the typed expression emitters. **Depends on:** F03.

- [ ] Represent types structurally: builtins, pointers/references, arrays, records/unions, enums, functions, member pointers and template specializations.
  - [x] Preserve Clang's `qualType`, `desugaredQualType` and `typeAliasDeclId` independently in a region-bound `ClangTypeView`; route AST spelling/ABI queries and typedef-layout identity lookups through it. A standalone regression checks all three values and the no-desugared fallback, while scoped-alias, pointer-qualifier and anonymous-typedef-record programs compile and match native behavior. Recursive type nodes, qualifiers at each level and complete ABI/layout facts remain open.
  - [x] Add a generic structural declarator summary for outer pointer layers/base extraction, pointer-group qualifiers, callback and pointer-to-array groups, and nested template arguments. Route pointer-depth and pointer-qualifier queries through it, removing the container-name-specific pointer-count exception. A standalone harness covers nested template pointers, function-parameter pointers, per-layer qualifiers, callbacks, pointer-to-array types and template-aware base extraction; generated function-pointer, pointer-array and C++ pointer-mapped-value fixtures compile and match native execution with the local Stage1/runtime pair. This remains a spelling-derived summary, not Clang's recursive canonical type graph.
- [ ] Retain typedef spelling for readability separately from canonical identity used for semantic decisions.
- [x] Associate collected C `typedef` and C++ `using` aliases with Clang canonical declaration IDs and resolve namespace-qualified spellings before expanding; short unqualified collisions fail closed. The scoped `word` fixture covers distinct `u32` and `u64` aliases and passes native/generated runtime parity. This is a safety improvement, not yet a replacement for canonical structural types.
- [ ] Store qualifiers at each indirection level, address spaces, incomplete/complete state, target size/alignment and function calling convention.
- [x] Compare `const`, `volatile`, `restrict` and `_Atomic` qualifiers at each printed pointer depth before eliding a multi-level pointer cast. The `pointer_qualifier_layers.c` regression covers dropping an intermediate `const` and adding base-level `volatile`; the lowered Elisa representation still lacks per-reference-layer mutability, and complex declarators remain fail-closed.
- [x] Infer the current single Elisa reference-chain mutability conservatively: retain `mutable` when any pointee depth is writable, but emit an immutable reference chain when every pointee depth is `const`. The fixture checks `const int * const *` becomes a readonly `i32&&?` parameter while native/generated behavior matches. Mixed writable/read-only indirection layers still cannot be represented exactly.
- [x] Query bounded predefined-macro output from the same normalized Clang invocation used for parsing; validate `CHAR_BIT`, scalar widths, pointer width against the local Elisa backend, `__SIZE_TYPE__` and plain-`char` signedness, then carry those facts into typed lowering. Direct and compilation-database modes share the query, and unsupported/missing scalar ABI facts fail closed with a source-qualified diagnostic.
- [x] Apply target scalar facts to emitted scalar types, integer width/signedness, promotions/usual arithmetic, constant/switch reasoning, pointer-cast compatibility and unknown `__builtin_object_size` sentinels. The LP64 host and an LLP64 Windows-target fixture verify `long`, `unsigned long`, `size_t`, plain `char`, globals and record fields; native/generated builtin parity verifies `SIZE_MAX` handling.
- [x] Separate local binding mutability from pointee capability in Elisa. The compiler contract now accepts `mutable cursor: u8&?` (the pointer variable may be rebound, its pointee is read-only) versus `cursor: mutable u8&?` (the local binding is fixed, its pointee is writable), including both qualifiers together. The translator derives binding mutability from Clang's top-level pointer qualification and actual writes/rebinds, independently derives referent mutability from pointee qualification, and preserves `const T *`, `T * const`, `const T * const`, and unqualified `T *` distinctions. `pointer_qualifier_layers.c` and `const_bindings.c` assert the emitted Elisa spellings, contain no emitted C `const` keyword, and match native execution with the isolated compiler pair. Capture-heavy, project-wide and compositional per-reference-layer cases remain open under the surrounding type-model items.
  - [x] Keep multi-variable C `DeclStmt` groups scope-transparent during local write analysis and Elisa name emission. The generic regression combines mutable and unchanged siblings, a shadowing block, and two locals declared in a `for` initializer; it checks inferred mutability and native/generated runtime parity. Also continue scanning nested/comma assignment expressions after a different assignment target is encountered. The same path now compiles and runs the upstream Kilo smoke program; no Kilo names or corpus-specific logic are used.
- [x] Apply the C `const` mapping rule at the emission boundary: source `const` never becomes an Elisa `const` binding/type keyword. An ordinary C `const T` binding emits as Elisa's ordinary immutable binding; pointer-slot rebinding and pointee write capability are represented independently with Elisa's existing `mutable` positions (`mutable p: T&?` versus `p: mutable T&?`). The isolated stage0/stage1 compiler binding probes pass, including a fresh self-hosted stage1 parameter-rebinding probe; `const_cast.c` emits ordinary `readonly: i32&?`, and the latest cJSON translation contains no emitted C `const` qualifier while preserving the required readonly helper/cast behavior. `const_aggregates.c` additionally proves direct immutable array and record initializers and keeps only dynamically populated pointer-table storage mutable. A regression caught and fixed the related parameter-boundary case: `T * const p` now emits `p: mutable T&?`, retaining writable pointee capability while leaving the binding itself ordinary/immutable. The full binding/capture/project contract remains open under the parent item.
  - [x] Apply the same rule in CFG/goto hoisting: hoisting a declaration changes placement only, so a top-level C `const` object remains an ordinary Elisa binding while non-const hoisted locals retain the conservative writable form needed for later-block assignments. The fresh stage1 `control-flow` suite and focused `const_bindings.c`, `const_aggregates.c` and `const_cast.c` native/generated parity checks pass.
- [ ] Add compositional per-reference-layer capability to Elisa and both local compiler stages. The stage0 parser regression covers independently mutable inner/outer references and nullable state at both pointer levels; stage1 semantic/backend changes stop inner mutability from leaking across a readonly outer reference. The translator now emits layer-by-layer mutability and nullability for ordinary pointer chains, with native/generated parity coverage for `const T **`, `T * const *`, and readonly chains.
  - [x] Preserve an optional-reference element when indexing through a non-null reference (`Ref -> Optional`), so nested generic pointer calls retain the inner nullable layer. The `nested_optional_pointer_assignment` regression compiles and returns 42 with local stage1; the translator-emitted `pointer_qualifier_layers` object compiles and returns 0, matching native C. This closes the nested optional-pointer backend case, not the broader per-layer milestone.
  - [x] Preserve each nullable layer when indexing through nested C character pointers. `(*text)[0]` for `char **` now emits an outer and inner generic `elisa_nonnull` check instead of flattening the expression to `[0][0]`; the `generic_nonnull.c` fixture compiles and links with isolated Stage1 and both native/generated executables exit 0. This verifies that read shape, not all nested-pointer operations or nullability proofs.
  - [x] Preserve pointer-valued array elements when decomposing pointer-to-array types. Both contextual and fallback renderers now reuse their ordinary array-element lowering, retaining the inner pointer's mutability and nullability; `pointer_array_decay.cpp` asserts `mutable array[mutable Objstruct&?, 4]&?`, and the emitted program compiles, links and exits 0 with the matching Stage1/runtime pair, as does native C++. This closes the pointer-to-array element-pointer leaf, not all nested qualifier combinations.
  - [ ] Complete both isolated compiler stages' focused parser, semantic, backend and ABI parity gates; pointer-to-array qualifier combinations beyond the verified element-pointer leaf, callbacks and C++ reference shapes still need exact layer handling.
- [ ] Use Clang's resolved types/layout data instead of parsing nested qualified-type strings as the primary semantic model.
- [ ] Extend ABI modeling beyond this scalar subset: complete record/union size and alignment, bit-fields, address spaces, calling conventions, enum representation options and target-specific integer rules. The CLI currently rejects missing/unsupported scalar ABI facts rather than guessing; safe structural fallback policy remains open.

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

- [x] Record and test the supported Clang JSON root contract (`TranslationUnitDecl` object with array-valued `inner`) and report syntax-valid schema violations with a source-qualified compatibility diagnostic. The validator is intentionally narrow so optional nested fields remain compatible across Clang releases; fake-frontend regressions cover a non-object root, missing/wrong `kind`, and missing/wrong `inner`.
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
  - [x] Implement and wire a fail-closed pre-emission verifier for typed expression/statement references and child slices, function/extern/record/global ranges, switch/label targets, function-local statement ownership, and expression/statement reachability. Require every expression-argument, block-child and switch-case table slot to be owned by exactly one parent; reject overlapping and orphan slices. Validate the hidden `ArrayIndex.value` side-effect edge as an expression reference, and follow `Conditional.third` only when it is an expression edge (enum values and array-index access modes are metadata, not references). Require disjoint function and external-function parameter ranges plus record-field ranges; reject orphan parameters and fields. Reject cross-function shared statements plus orphan statements/expressions. Avoid creating dead runtime IR for compile-time `__builtin_object_size` modes and prune temporary condition/unselected-arm IR when a conditional condition folds safely. It reports the first broken invariant and IR index. Standalone tests cover malformed references/ranges, orphan and overlap cases, and enum-value metadata above 32-bit signed range; fixture tests pass. Type/declaration identity, complete CFG-edge, value-category and lifetime/scope verification remain open.
  - [x] Enforce C switch-case edge shape: each switch has at most one default edge; a default edge has no value-expression edge and is not marked constant; every non-default edge has a required, valid value-expression reference. Standalone IR tests accept a valid case-plus-default switch and reject duplicate defaults, a malformed default edge and a missing case value. Complete CFG-edge verification remains open.
  - [x] Validate control-transfer scope against the nearest lexical construct: `break` must target a loop, `SwitchBreak` must target a switch, `continue` must be inside a loop and carry that loop's exact `for` increment (or `-1` when appropriate), and a `for` increment edge must target an expression statement. Repeated statement nodes must have consistent loop/switch/increment context. Standalone tests cover legal loop and nested-switch continues, an inner `while` overriding an outer `for` increment, illegal/misclassified transfers, mismatched increments, and malformed `for` increment edges.
  - [x] Validate private-global `Name` edges against their indexed global: the index must be in range and point to a project-private object; the emitted source spelling must match the global entry; and the target must retain a nonempty canonical declaration ID. The focused verifier regression accepts the matching edge and rejects mismatched spelling and missing identity; a fresh bounded translator rebuild followed by the complete `fixtures` suite passed. Local/function binding IDs and full cross-table canonical identity verification remain open.
  - [x] Validate call-mode tags before emission: direct versus indirect callee shape, supported tag values, alignment of encoded overload/external-signature tags, and bounds of their respective signature-table indices. Standalone tests accept valid direct, indirect, and indexed calls and reject mismatched callees, unknown/misaligned tags, and out-of-range user/external signature indices. Canonical user-signature-to-definition identity and indexed-call result types are checked below; argument conversions and non-indexed call/return consistency remain open.
  - [x] Preserve fixed parameter counts and Clang's semantic `variadic` flag on indexed user-function signatures, then validate indexed user/external call arity before emission: fixed signatures require an exact count; variadic signatures require at least their fixed count; malformed negative counts fail closed. The versioned typed-IR dump records these fields (currently v11). Focused verifier tests cover fixed and variadic user/external calls, too few/many arguments and dump serialization. For recognizable indirect function-pointer types, validate fixed and variadic arity from Clang's nested type spelling; preserve C's no-prototype `(*)()` behavior while treating the same empty parameter list in C++ as exactly zero parameters. Nested callback parameters are counted structurally. The standalone verifier and rebuilt `control-flow` suite pass.
  - [x] Bind indexed C++ user-call signatures to Clang's canonical declaration identity and the exact lowered function index. Function, external and signature rows retain opaque IDs only in memory; lookup uses canonical IDs, with name/type fallback allowed only when the ID is unavailable and the candidate is unique. The verifier rejects missing or mismatched signature targets, compares the selected definition's full resolved function type and checks indexed user/external call result types; the v12 dump serializes the stable result type while recording identity presence without serializing unstable Clang IDs. Standalone same-name/same-type target and mismatched-result tests, real-Clang local C++ overload differential execution and the bounded translator rebuild pass. Project-wide reversed-order coverage is inconclusive because a later Clang target-macro query returned an empty result; argument conversions, non-indexed call/return consistency and broader C++ namespace/template/operator overloads remain open.
  - [x] Run `goto_out_of_loop_from_switch.c` through a freshly rebuilt translator and verify native/generated runtime parity. The `case 2` edge exits directly to the label after the loop; the C native and generated Elisa executable both returned 0 in the focused control-flow suite using the pinned local Stage1 compiler and matching runtime.
- [x] Add a deterministic, versioned typed-IR dump with stable ordering and source fields escaped independently of terminal syntax; verify repeated dumps match and the option leaves generated Elisa stdout byte-identical.
- [x] Add pass-selection controls for minimizing semantic regressions while preserving required verifier boundaries. Required typed lowering and verification remain shared; optional readability rewrites are gated by `--idiomatic`, while `--fidelity` retains source-level expression structure. A constant-fold regression compiles and runs both modes and checks that only idiomatic mode folds `(2 + 3) * 4` to `20`.

**Acceptance:** Invalid IR cannot reach source emission and a pass failure identifies the earliest broken invariant and source node.

### S02 — Preserve integer, enum and boolean semantics [P0]

**Location:** src/c_semantics.elisa, typed arithmetic lowering. **Depends on:** S01.

- [ ] Implement integer rank/promotions/usual conversions from the selected target, including char signedness, enum representation and pointer-sized integers.
  - [x] Preserve Clang's implicit arithmetic conversion targets (including integer promotions) and explicit scalar C/C++ casts in typed IR, then emit them through one scalar-conversion path. This prevents mixed expressions from reconstructing a different width/signedness after casts are discarded; the enum-alias boundary fixture and full acceptance manifest exercise the change.
  - [x] Preserve Clang's explicit enum base type and ordinary C enum integer type in typed IR; emit that Elisa scalar and use it for mixed enum/integer promotions. Native differential fixture covers an unsigned enum value above `INT32_MAX`.
  - [x] Resolve the selected C target's enum storage for `-fshort-enums` from the source enumerator range when Clang does not provide a fixed/common underlying type. The compile-database flag parser honors the last `-fshort-enums`/`-fno-short-enums` option; the generic `short_enum_abi.c` differential fixture covers unsigned/signed 8-bit and unsigned 16-bit representations, casts, function boundaries, `sizeof`, and record layout under native Clang and both local compiler stages (2026-09-28). C++ scoped-enum conversion restrictions remain separate. A fresh translator source rebuild against the current compiler pair is still open under V06 because the current stdlib has moved its JSON DOM behind region-indexed handles.
- [ ] Model unsigned wraparound, signed overflow policy, division/remainder and valid shift counts explicitly.
  - [x] Add a non-constant differential regression for runtime `u32` addition and multiplication wraparound. `runtime_unsigned_wrap.c` passes native/generated execution through the 21-case acceptance manifest (2026-09-30); its parameters keep both operations dynamic, and structural assertions confirm emitted `+` and `*` rather than folded results.
  - [x] Normalize compile-time integer conversions at unsigned target-value boundaries using the selected Clang ABI width, including `u64` raw-bit-pattern emission. `runtime_unsigned_wrap.c` covers `(T)-1` for `u8`, `u16`, `u32` and `u64`, plus dynamic `u32` arithmetic wraparound. The focused fixture passes native/generated compile, link, execution and parity; the full 31-case manifest passes 30 cases, with the sole remaining failure isolated to unrelated `c_void_pointer_boundaries` Elisa compilation (2026-10-05).
- [ ] Fold constants at their source width/signedness rather than host integer width; preserve implementation-defined behavior selected by the source target.
  - [x] Apply usual integer conversions before folding arithmetic/comparisons, normalize defined sub-64-bit unsigned arithmetic and bitwise results, decline signed overflow and host-overflow-risk folds, check C's promoted width before shifts, retain invalid counts and implementation-defined signed-negative right shifts, and fold defined unsigned shift wrap. Native differential fixtures cover unsigned add/multiply/not, mixed signed-unsigned comparison and shift wrap; retained-expression fixtures cover invalid and implementation-defined shifts.
  - [ ] Extend folding to the full uint64 bit-pattern domain for literals, defined casts, unsigned wraparound arithmetic, division/remainder, shifts, bitwise operators, and unsigned comparisons; re-emit upper-half results as unsigned Elisa values. Keep implementation-defined unsigned-to-signed narrowing, signed overflow, and `MIN / -1` or `MIN % -1` conservative at every supported signed width.
    - [ ] Verify high-half operands for unary negation, `&`, `|`, `^`, division/remainder, and unsigned `<=`, `>=`, `!=`, plus narrowing high-bit `uint64_t` constants to `uint8_t`, `uint16_t` and `uint32_t`, including generated Elisa shape and native/generated runtime parity. The fixture now includes those narrowing casts and output-shape assertions alongside signed `INT64_MIN`. The old translator trapped in `append_i64` when formatting the high-bit `&` result; the formatter now extracts negative magnitude in `u64`. Rebuild and toolchain-backed verification are pending a safe compiler window.
    - [x] Make signed `MIN / -1` and `MIN % -1` decline folding for every supported expression width, not only host `i64`. Add uncalled 32-bit probes and generated-shape assertions alongside the existing 64-bit cases; Elisa-output verification is still pending the safe compiler refresh.
  - [x] Normalize C `_Bool`/`bool` storage to Elisa `bool`, keep bool-to-bool stores from widening to integer storage, and emit folded boolean constants according to the actual folded value. Differential coverage checks assignment from integer zero and subsequent bool increments/decrements.
- [ ] Recover bool only when all values/uses prove a boolean domain and the ABI/storage representation is unaffected.
  - [ ] Preserve C enum integer semantics separately from Elisa's nominal/closed enum conveniences. A C enum object can hold any value representable by its selected integer type, not only a named enumerator; define a generic storage/conversion strategy that handles initialization, assignment, explicit casts, mixed integer expressions and compound bitwise updates without losing qualified symbolic constants.
  - [x] At typed value boundaries, convert through Clang's selected enum storage scalar and reconstruct the nominal Elisa enum. Preserve direct same-enum values, but convert integer initializers/assignments, record fields, scalar array elements, call arguments, returns and compound-update results; convert enum values to the destination integer width/signedness rather than assuming `i32`. `enum_integer_semantics.c` compares native and generated behavior for unnamed values, signed and unsigned enum representations, global/local records and arrays, calls, returns, explicit casts, and `|=`.
  - [x] Render `sizeof(enum-type)` from the collected Clang-selected enum backing type rather than the translator's integer fallback. This preserves bool/u8/u16/u32/u64-backed C and C++ enum object sizes; `cpp_enum_bool_storage.cpp` verifies the bool-backed `sizeof` case and the complete 19-case acceptance manifest passes with the refreshed isolated stage1 compiler/runtime.
  - [ ] Extend this coverage to typedef/namespace aliases and all supported integer destinations; model C++ scoped-enum restrictions separately and retain Clang's selected conversion semantics.
    - [x] Cover a two-level C typedef chain for an unsigned-backed enum across global storage, cast/return boundaries, bitwise compound assignment, and signed/unsigned destinations from char through long long, including `0xffffffffu` narrowing/promotion boundaries. `enum_typedef_aliases.c` passes native/generated execution with the latest local Stage1 compiler/runtime.
    - [x] Preserve namespace-qualified C++ scoped-enum identity through nested `using`/typedef aliases and pointer parameters; emit one enum with Clang's qualified name and selected underlying storage instead of alias-shaped duplicate enums or integer fallbacks. Verify both forbidden implicit conversions (scoped enum to integer and integer to scoped enum) are rejected by Clang before translation, and compare generated/native execution at high unsigned values. Evidence and the exact toolchain boundary are recorded in `docs/execution_status.md` (2026-10-01).

**Acceptance:** Boundary-value differential tests pass across supported target models and both output modes.

### S03 — Preserve evaluation and sequencing [P0]

**Location:** expression lowering, call lowering, proposed analysis/effects.elisa. **Depends on:** S01–S02.

- [ ] Model comma expressions, pre/post increment, compound assignments and short-circuit expressions with exact evaluation counts.
  - [x] Constant-fold `&&`/`||` when a constant left operand determines the result; short-circuit the constant evaluator before traversing the unreachable right operand and omit its runtime emission. Native differential coverage includes side-effecting calls on both skipped right-hand sides.
  - [x] Preserve one-time lvalue evaluation for scalar integer compound-assignment statements by emitting Elisa's compound operator when both operands are represented directly; native differential coverage verifies a side-effecting index call and `unsigned char` wraparound.
  - [x] Preserve tested compound-assignment values through concrete, source-unique helpers keyed by operator and operand types, so the lvalue is passed once and the helper returns the stored result; differential coverage checks indexed `unsigned char += 1` wraparound and an `if` condition using `+=`.
  - [x] Normalize compound-assignment RHS operands to the destination scalar ABI width and signedness at the emission boundary, including generated value helpers. The generic `compound_widths.c` regression covers `i32 += i16`, `i32 += u8`, `u8 += i32`, record fields and C unsigned wraparound; isolated stage1 compilation, linking and native/generated execution all pass. This prevents malformed LLVM overflow intrinsics from mixed-width Elisa operands.
  - [x] Preserve comma-operator left effects in `if`/`while` conditions, local initializers and return expressions by sequencing discarded operands before the final value; native differential coverage checks one-shot evaluation, repeated `while` tests (including termination), initialization and return.
  - [x] Detect `volatile` as a complete type-qualifier token regardless of order (including `const volatile T`) and fail closed when a discarded comma operand would otherwise lose a volatile read. A dedicated negative fixture requires a diagnostic and empty generated stdout; volatile loop-test and atomic sequencing remain separate open work.
  - [x] Preserve comma-operator effects at expression roots and beneath eagerly evaluated value operands in local initializers and returns, including call arguments and array indexes, by emitting discarded operands in a statement prelude while retaining the verified typed-IR graph. The generic walk handles ordinary binary operands, unary/cast/member/index expressions, call designators and arguments, the always-evaluated condition of a conditional expression, and the always-evaluated left operand of `&&`/`||`. Native/generated checks cover direct and nested calls, arithmetic in initializers/returns/call arguments, array-index commas, and side-effecting `&&`/`||` RHS calls whose execution depends on the left operand; generated-structure assertions verify extracted effects precede the retained value expression while conditional RHSs remain nested.
  - [x] Preserve comma effects in both arms of conditional expressions used as local initializers or return values. Lower each arm's prelude under its own `if` branch and assign the selected value to a deterministic internal temporary; keep conditional-condition effects before the branch. Native/generated tests cover selected true/false arms, effects nested beneath arithmetic, condition effects and both return paths. Explicitly diagnose conditional glvalues, record-valued conditional materialization and conditional comma effects in expression contexts that have no branch-prelude lowering yet.
  - [x] Preserve effectful comma prefixes in scalar short-circuit RHSs in value expressions and `if` conditions: materialize C's 0/1 result and keep RHS preludes under the selected `&&`/`||` branch. Native differential coverage checks skipped/taken `&&` and `||` paths plus a conditional expression nested in the RHS; generated-shape checks prove calls remain branch-local and precede the translated `if` body only through the condition result.
  - [x] Lower ordinary `while` tests with conditional statement preludes into a `while true` body that runs the prelude, checks the materialized condition, breaks when false and then executes the source body. This preserves per-test effects and routes `continue` through the next test; native differential coverage checks termination, skipped/taken RHS effects, prefix decrement and `continue`.
  - [x] Fail closed for volatile/atomic loop-test accesses until the IR can preserve their observable access order. Detect volatile object reads without confusing a pointer-to-volatile-pointee value with a volatile pointer object; recognize C atomic types, Clang atomic expressions/builtins and atomic member-call shapes. Reject `while`, `for` and `do-while` tests before moving them into statement preludes. The four negative fixtures require source-line diagnostics and empty stdout; the pointer-to-volatile-pointee control precedes the volatile rejection. Expression ranges are retained by compact AST projection version 2 so these lowering diagnostics do not degrade to `0:0`. Focused control-flow and acceptance-manifest evidence is in `docs/execution_status.md` (2026-09-30). This does not yet implement volatile/atomic sequencing or claim a dedicated `std::atomic` fixture.
  - [x] Fail closed for nested conditional-value contexts whose effects cannot be placed without changing C behavior. Unsupported cases retain source-qualified diagnostics and empty generated stdout for nested conditional-arm effects, volatile comma operands, record-valued conditionals, effectful aggregate call arguments and C++ conditional glvalues. The constant-decisive `&&`/`||` acceptance case still translates, compiles, links and matches native execution; the translator's IR verifier runs before emission. Verified by the focused control-flow suite and 22-case acceptance manifest on 2026-09-30; detailed evidence is in `docs/execution_status.md`.
  - [x] Lower scalar comma-effect preludes in `for` tests at the top of each iteration, followed by a false-condition break guard; preserve the original increment on fallthrough and `continue`. Native differential coverage checks repeated short-circuit effects, skipped RHS effects and `continue` paths.
  - [x] Lower scalar comma-effect preludes in `do-while` tests as a dedicated condition-prelude statement region. Both ordinary body fallthrough and `continue` enter that region before the condition branch; native differential coverage checks repeated test effects and `continue` on the first iteration.
  - [x] Represent a `for`-loop increment on its `continue` terminator instead of copying it into the body. Structured emission executes it once immediately before `continue`, while CFG emission follows its existing increment edge once. Differential tests cover a structured loop, a `goto`-forced CFG loop, and a `do-while` nested in a `for`.
  - [x] Lower effectful arguments to direct named C calls into per-argument preludes and values, then construct the call with its resolved return type and inline/external metadata. Choose deterministic source-order evaluation (a valid refinement for defined C calls) and materialize each effectful scalar argument as one complete value before beginning the next, including residual call/arithmetic effects, volatile scalar reads and branch-local comma effects. C++17 fixture coverage accepts either standard-permitted native order, rejects interleaving, and verifies translated calls plus external `abs`.
  - [x] Classify pointer-to-record arguments as scalar pointer values rather than by-value aggregates during sequencing checks, so effectful `struct T *` arguments can be materialized in order while true by-value record arguments remain fail-closed. `record_pointer_call_arguments.c` verifies a side-effecting record-pointer producer and scalar argument are each evaluated once before the call; the existing negative aggregate-argument case still rejects unsupported by-value materialization. cJSON's full smoke translation now passes its quality gate.
  - [x] Support effectful arguments to calls through a plain local/parameter C function-pointer variable, including the equivalent `(*callback)(...)` spelling. Capture the function value into a generated local before argument evaluation, retain the callable type for argument conversion, and materialize each effectful scalar argument as a complete value before moving to the next. Differential coverage checks conditional and ordinary side effects, exact counts, and generated callee/argument/call ordering. An effectful record argument is explicitly rejected until aggregate sequencing/lifetime semantics are implemented; reference arguments and member or genuinely computed indirect callees remain open.
  - [x] Propagate value-plus-prelude lowering through eager, non-assignment binary operands and the cast/parenthesis wrappers Clang inserts around them. Rebuild the binary typed-IR node with its Clang-derived result type while sequencing branch-local effects before its value use; C may choose either operand order here, so programs with conflicting unsequenced writes are excluded as undefined behavior. Native differential coverage exercises both ternary arms nested under addition inside translated calls.
  - [x] Lower scalar conditional-arm comma effects in built-in array-subscript base/index expressions while preserving the array element type and lvalue node. The native differential fixture verifies both branches select the correct index, execute only the chosen branch effect and evaluate once. Overloaded C++ `operator[]` is not part of this built-in subscript path.
  - [x] Propagate conditional-comma preludes through a member read's base expression while retaining the field name, dot/arrow mode and Clang-derived member type. Differential coverage reads both selected records through a conditional array index; compound-assignment targets are verified separately below.
  - [x] Lower scalar simple-assignment (`=`) places and values with conditional-comma preludes in statement and assignment-value contexts; evaluate the selected place effect before storing and preserve the assignment result. The native differential fixture checks conditional effects in both the LHS (indexed member place) and RHS, in statement and value contexts.
  - [x] Support effectful arguments to calls through a plain local/parameter C function-pointer variable, including the equivalent `(*callback)(...)` spelling. Capture the function value into a generated local before argument evaluation, retain the callable type for argument conversion, and materialize each effectful scalar argument as a complete value before moving to the next. Differential coverage checks conditional and ordinary side effects, exact counts, and generated callee/argument/call ordering. An effectful record argument is explicitly rejected until aggregate sequencing/lifetime semantics are implemented; C++ reference and member-function-pointer contexts remain open.
  - [x] Sequence calls through computed C function-pointer callees when scalar arguments have effects. Lower and capture the callee value before argument preludes, including a function-pointer member reached through a side-effecting pointer-to-record factory, a conditional function-pointer expression, and a typedef'd function pointer returned by a C function. Emit C function-pointer values as nullable Elisa function values (grouped `(fn(...))?`), preserve null returns, and assert non-null immediately before an indirect invocation after argument effects. `computed_function_pointer_call.c` and `function_pointer_return.c` check exact native/generated results and effect counts; generated-shape checks enforce callee-before-argument-before-call ordering. C++ member-function pointers, callback ABI/lifetime edge cases, and untested function-pointer declarator forms remain separate work.
  - [ ] Lower conditional glvalues and the remaining C++ reference/member-function-pointer call contexts with the source language's exact object identity, lifetime and ordering semantics.
  - [ ] Sequence effectful aggregate/record call arguments and conditional values only after assignment, aliasing, lifetime, copy/move and ABI preconditions are represented and verified; keep unsupported forms fail-closed meanwhile.
  - [ ] Model volatile and atomic sequencing explicitly in typed IR instead of treating accesses as ordinary pure values; the current volatile/atomic loop-test checks remain fail-closed guards, not a sequencing implementation.
  - [ ] Generalize value-plus-prelude lowering to every other remaining expression context. Add target-aware sequencing and do not materialize a context until its language-standard evaluation and lifetime rules are represented.
  - [x] Preserve scalar integer, floating and boolean pre/post increment/decrement values and updates across assignments, nested arithmetic, call arguments, returns and conditions with generated per-translation-unit helpers; differential coverage includes signed `int`, unsigned `char`, `float`, `_Bool`, an indexed lvalue with a side-effecting index, prefix assignment/call argument and postfix comparison.
  - [x] Keep `&&`/`||` RHS assignments inside their short-circuit operand, and preserve simple assignment stores and results when used as values via a source-unique generic helper; native differential coverage checks both skipped and taken logical RHS paths plus `identity(cursor = 9)`.
- [ ] Lower side-effecting conditions and arguments through explicit sequence points/temporaries when required by target-language evaluation rules.
- [ ] Preserve source-standard sequencing guarantees for C++ calls and assignments; avoid tests that assume a universal order for unspecified C evaluations.
- [ ] Separate pure, potentially trapping, allocating, volatile, atomic and externally observable operations.
- [ ] Do not duplicate, reorder or drop loads/calls merely because their rendered expressions appear identical.

**Acceptance:** Counter/trace fixtures detect evaluation-order/count regressions, including aliasing assignments and early-return expressions.

### S04 — Correct floating-point and literal representation [P0/P1]

**Location:** typed numeric lowering and literal writer. **Depends on:** S01–S03.

- [ ] Preserve target floating formats, exact constant rounding and implicit arithmetic conversions.
- [ ] Keep NaN, infinities, negative zero and signed-zero-sensitive expressions intact; do not apply algebraic identities valid only for real numbers.
  - [x] Lower Clang's generic `__builtin_nan*`, `__builtin_inf*` and `__builtin_huge_val*` identities without guessed platform-library declarations. The translator emits typed IEEE expressions, preserving `f32`/`f64` shape; `floating_edge_values.c` compiles and runs with native, isolated stage0 and refreshed isolated stage1 artifacts.
  - [x] Correct the isolated compiler backend's floating `!=` and float-to-bool predicates to LLVM unordered-not-equal (`UNE`, enum value 14), so NaN comparisons and truthiness follow C/IEEE semantics. A compiler-owned backend regression and the Elisa floating probe both pass at runtime on stage0 and stage1.
- [ ] Make fast-math or relaxed semantics explicit in compilation context and optimization eligibility.
- [ ] Preserve integer/float suffix intent, hexadecimal values and byte/code-unit values in character and string literals.
  - [x] Materialize integer/character literals at the selected ABI width only when a comparison directly crosses a call-result boundary. This fixes invalid LLVM such as `icmp ne i32 %call, i64 7` in C++ adapter methods while retaining clean idiomatic spellings for ordinary lvalue arithmetic and comparisons; the generic `cpp_unordered_map_find.cpp` fixture compiles, links and matches native execution with the current stage1 product.
- [ ] Diagnose unavailable long-double/extended formats until a verified representation or compatibility path exists.

**Acceptance:** Literal round-trip and numerical edge fixtures agree with the selected native reference under the same semantic flags.

### S05 — Preserve pointer values, arithmetic and aliasing [P0]

**Location:** src/emit_places.elisa, type and expression lowering. **Depends on:** S01–S04.

- [ ] Represent pointee type, nullable shape, allocation/object provenance, offset and qualifiers separately.
- [ ] Support array decay, address-of, dereference, pointer stepping, subtraction, one-past values and pointer-to-array scaling without accidental integer truncation.
  - [x] Lower ordinary array-to-element-pointer decay at target-typed initializers/assignments and call arguments as the address of element zero; preserve target pointer depth, mutability and nullable shape. `cpp_reference_cursor.cpp` verifies pointer initialization, reference-to-pointer updates, stepping to one-past and address equality against native C++.
  - [x] Retain pointer-to-array decay and scaling for multidimensional array arguments; `pointer_array_decay.cpp` verifies row references and native/generated execution.
  - [x] Scale pointer-address differences by the selected target size of known scalar, enum, and pointer pointees so C pointer subtraction returns element counts rather than byte counts. Treat GNU `void *` subtraction as byte arithmetic; fail closed with a source diagnostic when a composite pointee's layout is unavailable instead of silently emitting a wrong result. The native differential fixture checks positive and negative `int *` differences, byte/double/enum elements, and pointer-to-pointer elements; the negative record fixture requires an empty generated stdout. Pointer provenance/alias lifetime and complete pointer-bearing aggregate/ABI conversion remain open.
  - [x] Capture Clang's simple record-layout dump alongside the JSON AST and retain size, alignment, and field offsets for matched complete non-union records. Match by canonical declaration identity (with a conservative shared-source-location fallback for injected C++ names), not emitted Elisa names; accept both tag and typedef spellings, including anonymous typedef-backed records, and share metadata across aliases of the same declaration. Use the target size for pointer subtraction only when the record has no packed/alignment-sensitive fields, bit-fields, C++ bases or explicit member functions, and its AST field count matches Clang's offset list. Implicit compiler-generated C++ special members do not disqualify a record. Ambiguous, union, packed and unmatched layouts remain fail-closed. `record_pointer_difference.c` checks flat, nested and typedef-backed records, matches native execution, and emits `/ 8` and `/ 16`; the generic matching path also handles cJSON's typedef-spelled record layouts without cJSON-specific rules. This is pointer-difference metadata, not a claim that emitted Elisa records generally reproduce C ABI padding or external aggregate layout.
- [ ] Preserve null as a pointer value at ABI boundaries and keep pointer-depth information through void-pointer conversions.
  - [x] Emit generic object-pointer ↔ `void *` conversions through local initialization, return values, call arguments, record fields, pointer arrays, null values, and `void **` slots. The C fixture translates and generated-shape assertions retain the two-level nullable reference signature.
  - [ ] Verify end-to-end compilation/link/runtime parity for that boundary fixture. The latest saved Stage1 run fails to compile with a storage-dependency invalidation diagnostic (`manifest-unsigned-full/c_void_pointer_boundaries`, 2026-10-05); callback, project/external ABI, volatile, and deeper pointer-chain conversions also remain open.
- [ ] Audit C raw-pointer behavior against Elisa reference validity/alias/lifetime assumptions; add narrowly scoped compiler primitives when those contracts cannot express C.
- [ ] Test pointer arithmetic and equality within defined source behavior, and document target-specific policies for implementation-defined conversions.

**Acceptance:** Array walks, aliasing updates, pointer slots and 64-bit round-trips match native behavior without fabricated non-null guarantees.

### S06 — Records, unions, arrays and initialization [P0]

**Location:** src/emit_types_records.elisa, aggregate lowering. **Depends on:** F04, S01, S05.

- [ ] Preserve field order, padding/alignment requirements, packed records, anonymous members, unions and bitfield layout using verified target metadata.
  - [x] Use the captured Clang facts to emit target-sized `sizeof` constants for supported non-union records (including typedef-spelled anonymous records) and fixed arrays of those records, plus `_Alignof`/`alignof` constants for the same verified layouts. Resolve aliases through canonical declaration identity; fail closed when a record layout is unavailable or ambiguous instead of using Elisa's potentially different `size_of`. `record_sizeof_alignof.c` checks flat/nested record sizes 8/16, two-element array sizes 16/32 and alignments 4 against native C; `record_sizeof_unknown_union.c` and `record_alignof_packed.c` verify unsupported queries fail closed, and complete padding/offset emission is still open.
- [ ] Handle partial/designated/sparse/nested initializers, zero filling and initializer evaluation order.
  - [x] Lower C designated record and array initializers through Clang's typed initializer children, preserving field/index placement and zero-filling omitted members. The generic `designated_initializers` fixture emits a named `Pair` aggregate and a sparse five-element array, compiles and links with both isolated compiler stages, and its stage0 executable matches native C at runtime.
- [x] Convert Elisa's `u8`-backed string literals to Clang's target-specific plain-C-`char` pointer shape at external-call and pointer-array initializer/assignment boundaries. The inih variadic `printf` calls and Kilo's `char *` keyword tables compile with target-aware casts; the upstream differential suite verifies inih output and Kilo's no-argument behavior. This does not yet model arbitrary string encodings, wide strings or literal storage mutability.
- [x] Keep one record with six fields distinct from six array elements; emit positional or named Elisa aggregates only when the target parser and expected type establish the intended nesting. `record_and_six_element_array.c` asserts the named six-field record is emitted as `SixFields{...}` while the one-field record containing six elements is emitted as `SixElementArray{values: [...]}`; both compile/link with the isolated Stage1 compiler and match native C at runtime.
- [ ] Represent flexible-array members, zero/one-element trailing-array idioms and variable-length arrays with explicit size/lifetime contracts.
  - [x] Fail closed on the currently recognized unsafe forms: C flexible-array-member fields, zero-length array fields/local arrays, local VLAs with nonconstant bounds, and pointer-to-VLA parameter types. Generic regressions exposed incorrect `data: u8&` and `array[i32, count]` output; each now requires a source-qualified diagnostic and empty generated output. This is a safety boundary, not support for tail allocation/access, the one-element struct hack, all variably-modified function types, allocation extents or lifetime contracts; those semantics remain open.
  - [x] Probe Elisa's runtime-sized `darray` comprehension as a possible VLA representation. The isolated Stage1 compiler accepts and runs it, but it is not a transparent lowering: the comprehension initializes every element (C automatic VLAs are not initialized), and `darray` storage follows Elisa's allocation-region lifetime rather than the VLA's block-scoped automatic storage. Clang JSON provides `qualType: "int[count]"` but no bound-expression AST child for the local declaration. Keep the VLA diagnostic until the translator can retain a once-evaluated bound, checked byte-size/alignment, uninitialized storage and scope/lifetime obligations; do not convert a successful Elisa compile into a support claim.
- [ ] Preserve compound-literal storage duration and address identity; do not replace mutable storage with a shared constant.

**Acceptance:** Size/alignment/offset probes and runtime mutation checks pass; unsupported layouts produce exact diagnostics.

### S07 — Storage duration, initialization and teardown [P0/P1]

**Location:** global/local declaration lowering, project initializer emission. **Depends on:** S01, S06.

- [ ] Model automatic, static, thread-local and external storage independently of Elisa mutability.
- [ ] Preserve C zero initialization and constant initialization before runtime initializers.
  - [x] Map C object-level `const` to Elisa's ordinary binding spelling: `const T x` emits `x: T`, never a target-language `const` qualifier. Proven static scalar, array and record initializers are emitted directly on the `global` declaration, so immutable C globals are not created as zeroed mutable storage followed by a runtime assignment. `const_aggregates.c` covers scalar arrays, record fields and a separately initialized pointer table; only storage that the generated startup path must write is mutable. Dynamic or unsupported pointer/address initializers remain on the runtime path and produce a source-qualified diagnostic rather than silently weakening the source contract. The generic `const_bindings.c` fixture and two-unit project fixture compile and match native execution with the isolated optimized stage1 compiler; pointer-slot and pointee capabilities remain independently represented.
- [ ] Ensure function-local statics initialize once and preserve their persistent identity.
  - [x] Hoist C function-local `static` objects into stable module storage keyed by canonical declaration identity, remove the declaration shell from the function body, and preserve one persistent object across repeated calls. `static_local.c` checks three successive updates against native execution and asserts the emitted Elisa contains one `global mutable value` with no residual C `static` syntax. Cross-unit collision and dynamic C++ local-static initialization remain open under the parent item.
- [ ] Define project initialization entry points and idempotence without basename collisions or accidental repeated execution.
- [ ] Carry teardown/cleanup obligations into IR so later C++ support does not retrofit lifetime semantics into formatted text.

**Acceptance:** Cross-unit globals and repeated function calls observe correct initial values, persistent state and initializer counts.

### S08 — Variadics, atomics and low-level extensions [P1/P2]

**Location:** foreign ABI lowering, proposed compatibility primitives. **Depends on:** F04, S03–S07.

- [ ] Complete source-defined variadics with default argument promotions, va_start, va_arg, va_copy and va_end lifetime rules.
  - [x] Lower Clang's dedicated `VAArgExpr` generically to typed `va_arg[T](storage)` instead of treating it as a guessed external function. The translator preserves the Clang result type, emits one reusable generic `extern va_arg[T](storage: mutable void&) -> T`, and the Elisa backend lowers the primitive through LLVM's `LLVMBuildVAArg`; the variadic fixture compiles, links and returns the same result as native C with the isolated stage0 compiler.
  - [x] Lower Clang's `__builtin_va_copy` generically to `llvm_va_copy(destination, source)`. The backend resolves LLVM's overloaded `llvm.va_copy` intrinsic by the pointer type and emits a void call with a non-null empty instruction name, avoiding both an unresolved library symbol and LLVM's overloaded-intrinsic mangling trap. A direct backend probe emits `llvm.va_copy.p0` in the generated LLVM.
  - [x] Apply target-derived C default argument promotions at variadic call boundaries. Integer and enumeration arguments narrower than `int`, `_Bool`, and `float` are emitted as `i32`/`f64` values before the ellipsis; the generic fixture compiles, links, and runs successfully with both isolated compiler stages.
  - [ ] Add aggregate extraction, and explicit lifetime/cleanup diagnostics for every supported target ABI, including full `va_copy` lifetime rules.
- [ ] Verify actual platform va_list layout/ABI through compiler primitives and C interop probes.
- [ ] Preserve volatile access and atomic operation ordering using target-supported intrinsics or a verified runtime layer.
- [ ] Classify compiler builtins by intrinsic identity and semantics; do not infer ordinary external function signatures from a handwritten list.
- [x] Lower `__builtin_object_size` by its Clang intrinsic identity and mode semantics for fixed arrays, directly named record-array members, and unknown pointer values; diagnose unsupported provenance rather than inventing a size or emitting an external call. The regression is program-generic and covers all four modes, including record-tail extent and unknown-pointer sentinels.
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
  - [x] Thread unlabeled empty jump-only CFG blocks at emitted edges with a bounded walk, while preserving every labeled entry point and refusing cyclic or malformed chains. The generic goto/switch control-flow suite passes native/generated parity after this reduction; labeled blocks remain explicit state targets.

**Acceptance:** Reducible examples eliminate dispatch, irreducible examples retain correct bounded fallback and metrics expose residual region size.

### I04 — Improve switch-to-match lowering [P1]

**Location:** switch lowering and CFG transforms. **Depends on:** S02–S03, I01.

- [ ] Evaluate the selector once and preserve promotions, enum type and full-width case constants.
- [ ] Group labels sharing equivalent arms into or-patterns; form ranges only when the represented values and Elisa range semantics match exactly.
- [ ] Remove terminal switch breaks and temporary completion flags only when control-flow proofs establish they are redundant.
- [ ] Model fallthrough, declarations crossing labels, conditional breaks, enclosing-loop continue and nested switches explicitly.
- [ ] Choose a readable structured lowering or localized state region for complex fallthrough; cap duplicated arm tails.
  - [x] The current structured path evaluates the selector once in the emitted `match`, groups adjacent labels that share one lowered body into Elisa or-patterns, forms only consecutive dense integer ranges, preserves symbolic enum patterns and full-width unsigned case constants, and omits direct terminal switch breaks. `switch.c`, `switch_patterns.c`, `wide_switch_constant.c` and the generic side-effecting `switch_selector_once.c` fixture pass native/generated parity under the isolated stage1 compiler. Conditional-break and CFG-embedded switches retain localized completion/state handling; complex fallthrough and cross-scope cleanup remain open.
  - [x] Effectful selectors are materialized into a deterministic, collision-checked `__elisa_transpiler_switch_selector_<expr>` binding before both structured and CFG-local matches. This prevents the current Elisa backend from re-evaluating a selector once per arm while leaving pure selectors compact; the generic selector-once fixture asserts the emitted shape and native/generated parity.

**Acceptance:** Cases/default, sparse/dense labels, fallthrough chains and nested loop interactions agree with native C/C++.

### I05 — Recover source names and declaration placement [P1]

**Location:** name registry, declaration and CFG transforms. **Depends on:** F03, S01, I01.

- [ ] Allocate output identifiers from canonical binding identity and scope; preserve legal source spelling by default.
- [ ] Handle keywords, Unicode, shadowing, aliases and sanitized-name collisions deterministically.
- [ ] Name necessary temporaries from their role and related source expression, using stable suffixes only for real collisions.
- [ ] Move declarations toward first definition and narrow scopes only after dominance, lifetime and jump-entry checks.
- [ ] Eliminate redundant alias temporaries and phi-like variables when SSA/liveness analysis proves a direct expression is safe.
  - [x] Keep legal C identifiers that collide with Elisa keywords readable and consistent through one `safe_identifier` boundary (`match`/`module` become `c_match`/`c_module`), and restore declaration scope after nested blocks so shadowed source names remain distinct bindings. Generic `keyword_identifiers.c` and `nested_shadowing.c` fixtures compile and match native execution with the isolated stage1 compiler. Canonical identity-based project-wide collision handling and Unicode normalization remain open.
  - [x] Make mutability and pointer-slot rebinding analysis lexical-scope aware. A nested or `for`-initializer declaration that shadows an outer spelling no longer makes the outer binding mutable or rebindable. `for_scope_shadowing.c` proves the outer `index` emits as an immutable binding while only `index_shadow_1` is mutable, and native/generated execution agrees under isolated stage1.

**Acceptance:** Repeated names bind correctly and unnecessary hoisted locals/synthetic names decline on generic fixtures.

### I06 — Simplify expressions through verified rules [P1]

**Location:** src/emit_quality.elisa, proposed transform/expressions.elisa. **Depends on:** S01–S05.

- [x] Create explicit typed-IR rewrite rules for redundant casts, identity operations, constant conditions, boolean predicates and conditional expressions. The rules are selected through one idiomatic-mode gate and operate on structural nodes rather than rendered text; pointer/capability and effectful cases remain conservative.
- [ ] Require source-width, signedness, trapping and effect preconditions for every algebraic rewrite.
- [ ] Preserve cast operations that encode sign extension, truncation, const changes, pointer ABI or foreign conversion.
- [ ] Fold only the pure subexpressions proven safe; do not remove side-effecting evaluation under multiplication by zero or equivalent-looking branches.
- [x] Keep applied-rule counters and a diagnostic-only `--explain-rewrites` report for redundant casts, identity operations, safe integer folds, constant-condition pruning, boolean-predicate simplification and constant conditional-arm pruning. The generic integer-constant regression proves the report leaves generated stdout byte-identical and records only transformations applied after typed-IR safety checks; side-effecting and overflow counterexamples remain retained by the existing sequencing/integer fixtures.

**Acceptance:** Positive fixtures simplify while nearby overflow, NaN, volatile, alias and side-effect counterexamples remain semantically intact.

### I07 — Improve null, mutability and effect inference [P1]

**Location:** src/emit_analysis.elisa, src/emit_expr_facts.elisa, src/emit_effects.elisa. **Depends on:** S03, S05, I01.

- [ ] Track facts by storage/place identity through branches and loops, with explicit alias and call invalidation.
- [ ] Infer immutable bindings independently from immutable pointees; C pointer constness has multiple levels.
  - [x] Map ordinary C object `const` to Elisa's ordinary immutable binding model. Keep pointer-slot rebinding and pointee write capability separate, so no C `const` keyword or redundant `mutable` qualifier is emitted for an immutable object binding. `const_bindings.c` emits ordinary `scalar: i32` and immutable parameter bindings while distinguishing mutable and readonly pointees; native, isolated Stage0 and fresh Stage1 executions all return 0.
  - [x] Treat writable address exposure as a binding-capability fact: a directly unassigned C object passed through `&object` to a writable pointer is emitted with a mutable Elisa binding, while `const` pointees remain read-only. The pointer-qualifier regression compiles and runs against the isolated latest stage0 compiler.
- [ ] Narrow optional pointers inside proven dominated regions and reuse the narrowed value without repeated assertions.
  - [x] Keep guard-derived pointer facts from eliding the checked conversion inside generated `trusted Unsafe.StaleRef` regions, where Elisa does not retain the branch-local non-null proof across the boundary. A generic `const int *` early-return fixture requires `elisa_nonnull_readonly(value)[0]`, then compiles, links and matches native execution with the local Stage1 compiler/runtime; readonly-pointer, array-decay, record-pointer and sequencing fixtures also pass. The fact/narrowed-value optimization outside these regions remains open.
- [ ] Audit generic nonnull helper contracts, including the existing zeroed-on-null behavior; do not manufacture a valid non-null reference from null.
  - [x] A null input now fails fast with `panic(...)` instead of returning fabricated `zeroed` storage. The helper remains demand-driven and generic; its direct conditional panic is accepted by the isolated stage1 backend, while the unsupported nested `trusted:` form is not emitted.
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
  - [x] Derive stable disambiguators from canonical physical source identity for colliding module stems or sanitized initializer stems; reject duplicate physical inputs and detected disambiguator collisions before translation writes output. A four-unit fixture covers both duplicate basenames and distinct filenames that sanitize to the same initializer stem. Normal and reversed compilation-database orders produce the same collision-safe module names, with every manifest initializer call resolving to its matching module definition; both generated projects compile and match native execution.
- [ ] Respect internal linkage and anonymous scopes.
  - [x] Preserve C file-scope `static` function identity in project output with stable translation-unit-derived Elisa names; direct calls and function-pointer references are covered by two translation units defining different `helper` functions, and a shared header contributes a `static inline` helper to both units. Normal and reversed compile-database orders produce the same private symbols, and both generated executables match native C.
  - [x] Preserve C file-scope and block-scope `static` object identity, including data declared by shared headers. The translator keys references by canonical declaration identity and emits private names derived from translation-unit and declaration identity; a two-unit fixture covers same-spelled file globals, block statics, and a shared-header static object. Both compile-database orders produce the same six private global names, and both generated Elisa projects compile and match native execution. Collision-registry integration across all declaration kinds remains open.
  - [x] Model C++ anonymous-namespace functions and objects as translation-unit-local identities. The project walk carries anonymous-namespace scope into function/global lowering; a two-unit C++ fixture gives both units the same private function and object names, checks deterministic private-name sets in normal and reversed compile-database order, and compiles/runs both generated projects against native C++.
  - [x] Model namespace-scope C++ `const` objects without `static` as translation-unit-local identities, while honoring an earlier external declaration and Clang's effective language mode. Language mode is derived from the active Clang predefined macros, so a `.c` source compiled with `-x c++` is handled as C++; non-inline const objects receive stable unit/declaration-derived names. A three-unit normal/reversed project checks same-spelled private objects, a shared object declared `extern` before its definition, and native/generated runtime parity. Const-qualified function-pointer declarators and broader C++ linkage families remain an explicit boundary.
- [ ] Merge compatible external redeclarations and diagnose incompatible ones.
  - [x] Add a bounded cross-translation-unit C function compatibility guard keyed by Clang's linker name. It resolves typedef aliases and ignores top-level parameter `const`/`volatile`/`restrict` for plain scalar and pointer parameters; it treats zero-parameter `()` and `(void)` spellings consistently, preserves pointee qualifiers, reports incompatible declarations before publishing project output, and fails explicitly if its bounded registry fills. Normal/reversed compile-database tests cover compatible typedef and qualifier variants plus incompatible integer/pointee-qualifier declarations; generated compatible projects match native execution. This is not yet structural canonical type identity: nested declarators remain exact-spelling comparisons and C++ ABI attributes/calling conventions are not fully modeled. Object declarations have a separate bounded check; the single canonical emitted-declaration registry remains open.
  - [x] Track explicit user-owned `extern` object declarations across translation units by Clang linker name. Desugared object types must agree; an incomplete outer array bound is compatible with a complete bound while two differing fixed bounds remain incompatible. Normal/reversed project fixtures compile and run with matching native behavior for compatible scalar and `T[]`/`T[N]` declarations, and reject `int`/`long` objects and `[3]`/`[4]` arrays before manifest publication. Limit exhaustion is diagnosed. Ordinary non-`extern` definitions/tentative definitions, structural record/qualifier identity beyond exact desugared type strings, and broader C++ object linkage remain open.
    - [x] Preserve a file-scope `extern` object declaration that also has an initializer as a definition instead of dropping it from project globals. A two-unit C fixture checks direct and function-mediated reads, compares the project manifest under reversed compilation-database order, and compiles/runs both generated projects against native C. A separate C++ project diagnoses duplicate initialized `extern` definitions in both database orders before publishing a manifest. Non-`extern` definitions, C tentative-definition coalescing, inline-variable ODR equivalence and full cross-kind declaration unification remain open.
- [ ] Merge each compatible project-wide external declaration into one canonical emitted declaration/export record; the current check prevents known C function conflicts but does not yet establish this full registry contract.
- [ ] Use stable ordering independent of compilation-database enumeration where semantics permit.
  - [x] Sort project translation units by canonical physical source path before translation, module inclusion and initializer emission, falling back to compilation directory and source spelling when canonical resolution is unavailable. The project identity and external-declaration fixtures compare manifests and generated modules byte-for-byte across normal and reversed compilation-database orders; both orderings compile and match native execution. This establishes deterministic unit order for the current supported project semantics; constructor-priority extensions and source-order-sensitive initialization policies still require explicit modeling.

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

- [x] Generate all files into a transaction-specific staging generation and publish a manifest only after every selected unit has translated, passed typed lowering/diagnostics, and been written successfully. Publication renames validated staged modules first and the staged manifest last; the translator does not claim to perform a full Elisa compile before publication.
- [x] Avoid publishing a mixed old/new project when one unit fails; retain previous usable output with explicit failure status. Exact per-output backups make publication recoverable, and a generic regression proves a later Clang failure leaves prior modules/manifest unchanged and removes all transaction staging files. A backup-path NUL regression was fixed so reruns actually replace old modules.
- [x] Resolve runtime and cpp_lib dependencies through explicit `--cpp-lib-dir DIR --elisa-std-dir DIR` output configuration. The generated project emits direct includes for the selected runtime, collections and include-free compatibility core; a relocation regression copies the complete generated project away from the translator output directory and compiles/runs it with the isolated latest stage1 compiler. The no-option repository-local wrapper remains a documented development fallback, while fully vendored release assets remain open.
- [x] Emit only required generic helpers and compatibility fragments, deduplicated across project units. Project aggregation now tracks the exact nonnull, readonly-nonnull and variadic runtime requirements of each translated unit; regressions prove unused helper families are omitted and required helpers are emitted once.
- [x] Record output ownership and remove obsolete generated files only from a validated prior manifest, never by broad directory deletion. Publication snapshots the previous generated manifest before replacement, validates its generator marker, accepts only safe single-component `.elisa` module names, removes only modules listed there and absent from the new source set, and preserves user-owned files. A two-generation regression covers stale modules, malformed/non-generated ownership boundaries and the user-file sentinel.

**Acceptance:** Projects move outside the repository and still compile; failed regeneration cannot look like complete successful output.

### P05 — Use a structured Elisa writer [P1]

**Location:** src/emit_format.elisa, target IR and source writer. **Depends on:** S01, I02–I08.

- [ ] Render precedence and associativity from target expression structure instead of cleaning arbitrary parentheses afterward.
- [ ] Format signatures, calls, aggregates and nested expressions with stable indentation and width policies.
- [ ] Preserve literal bytes, escapes, multiline strings and source-comment content exactly where required.
- [ ] Attach comments to declarations/statements using origin/trivia ownership; keep licenses and conditional/macro context useful.
- [ ] Round-trip emitted output through the selected Elisa parser and reject invalid target constructs before publication.
  - [x] Add a bounded determinism gate: translating the same source twice must produce byte-identical Elisa and diagnostics, alongside the existing safe-rename metamorphic check. Generated artifacts in the fixture/project suites are compiled by the selected isolated compiler, so invalid emitted syntax is rejected by the acceptance workflow.

**Acceptance:** Formatting is deterministic/idempotent, literals remain identical and nested operator fixtures parse to the intended target structure.

### P06 — Provide source maps and actionable translation reports [P1/P2]

**Location:** diagnostics, emitter origins and proposed reports/. **Depends on:** F03, S01, P04–P05.

- [x] Emit generated-span to source-span mappings with source hashes, macro origins and synthesized-node reasons. The complete opt-in source-map CLI suite verifies macro spelling/expansion, generated-byte correlation, include edges, hashes, synthesized control-flow statements, origin-free translation units, collisions, rollback and deterministic single-file/project output using a source-fresh translator built against the refreshed isolated Stage1 product. Exact compiler source HEAD, dirty-file list and binary/runtime/translator hashes are in `docs/execution_status.md`; broader B01/V06 provenance and reproducibility work remains open.
  - [x] Serialize opt-in `--source-map-json PATH` output with final generated byte offsets, primary/spelling/expansion ranges, immediate include edges, synthesized reasons and FNV-1a-64 source-content hashes. Single-file output and bounded aggregate project maps stage and publish in the module/manifest transaction; `scripts/test_source_map.py` passes end to end with the refreshed isolated compiler. Project-unit assertions use canonical source identity rather than positional order, and repeated project translation confirms byte-identical aggregate JSON. Root translation-unit hashes are included even when a unit emits no origin spans, and project-output collision checks resolve symlink targets before publication.
    - [x] Seed the source table with the canonical translation unit before collecting mapped AST origins, so macro-only/empty-origin inputs still have a content identity and count against the source-byte budget. End-to-end single-file and project macro-only checks pass with the refreshed translator.
    - [x] Compare resolved project-map output targets against generated module and manifest paths as well as the lexical output path. End-to-end symlink-collision assertions confirm refusal preserves both the symlink and project files.
    - [x] Correlate a known macro expansion origin with the generated byte span containing its returned value; generated ranges, source offsets and source-content hashes pass end-to-end assertions.
  - [x] Retain optional per-expression/per-statement Clang source origins in typed IR, including half-open source ranges, separate macro spelling/expansion ranges, filenames and explicit immediate include edges; mark lowered synthetic nodes with a reason. The refreshed-compiler source-map suite verifies origins and synthesized control-flow spans.
  - [x] Capture nested statement-emission spans and copied origin metadata; map offsets through final formatting and cover macro-expanded returns, CFG/synthesized statements and deterministic single-file/project output in `scripts/test_source_map.py` with the refreshed isolated compiler.
- [ ] Report unsupported constructs with source location, semantic category, relevant type and the missing translator/compiler capability.
  - [x] Validate versioned diagnostics JSON for the Clang node's qualified type, semantic category, distinct required-capability field, exact half-open source byte range, and source coordinates when Clang elides `line`. Focused C and CRLF regressions verify exact line/column and source slices; the AST projection schema, full source-map CLI suite and Clang-failure suite pass with a freshly built translator. Native and translated `simple.c` compile/link and both exit 42. Toolchain hashes and the compiler-source caveat are recorded in `docs/execution_status.md`; rewrite explanations are now separately checked, while the full translator roadmap remains open.
- [x] Support a rewrite explanation mode that shows the proof category for a simplification and why a desired rewrite was declined. Opt-in stderr events now carry half-open source ranges and identify applied proof categories or declined reasons; the regression verifies both conditional-lowering paths, effectful/volatile declines, and byte-identical generated Elisa stdout. The focused explanation test, diagnostics JSON test, complete source-map CLI test, and native/generated acceptance case pass with a freshly rebuilt isolated Stage1 compiler pair; exact toolchain hashes are recorded in `docs/execution_status.md`.
- [x] Keep source-map generation generic, deterministic and useful to diagnostics, debugging and downstream tooling. The opt-in schema is exercised across single-file and multi-unit C inputs, macro/header origins, no-origin units, deterministic repeats, and transactional collision/failure cases.

**Acceptance:** Users can trace a generated statement, ABI wrapper or residual state region to its original source and understand blockers.

## 5.6 C++ language support

### C01 — Audit real C++ requirements and resolve names [P1]

**Location:** src/cpp_compat.elisa, frontend identities, corpus inventory. **Depends on:** F03–F04, S01.

- [ ] Inventory Wolf4SDL and other candidate units by Clang node/type/operation families and runtime use, including rare paths.
- [ ] Support namespaces, aliases, using declarations, extern C and overload resolution using Clang's resolved targets.
- [x] Preserve Clang-selected calls among local C++ overloads and declaration-only overloads resolved across project translation units. Synthetic Elisa aliases retain each Clang linker identity, avoid collisions with the translated implementation's source-level overload set, and keep numeric promotions/conversions explicit. Local and project fixtures exercise same-arity integer, float, double and long overloads plus short-to-int promotion; project output is invariant under reversed compile-command order and matches native execution. Namespace-qualified identities, library overload families, and overload sets involving references, templates or operators remain open.
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
  - [x] Bounded direct external class-template path: retain source-used specializations, qualify named namespaces, associate layouts with Clang declaration IDs, skip primary-pattern/injected-name records, and reject identity/name collisions. Keep canonical full-argument Elisa types while registering verified omitted-default source spellings as aliases. Verified for scalar fields, fixed arrays, explicit/defaulted integer and type arguments at `-O0`/`-O2`; constructors, dependent nested layouts, partial specializations and canonical C++ type identity remain open.
- [ ] Recover Elisa generics only where type/value parameters, constraints, overload behavior and operation semantics map faithfully.
- [ ] Support non-type parameters, defaults, partial/explicit specialization and parameter packs in staged independently tested increments.
  - [x] Bounded direct-class-specialization slice: preserve Clang's scalar decimal integer argument values, including negative values; recover boolean argument intent from the corresponding `NonTypeTemplateParmDecl` type and map Clang's `0/1` representation back to `false/true`. Accept direct integer-literal defaults and concrete type defaults only when the omitted source spelling and specialization arguments agree; retain one canonical emitted type with source-spelling aliases. A real-Clang negative fixture proves compound defaults without a directly projected scalar value fail closed. Dependent/unrecognized defaults and other non-type forms remain unsupported until separately modeled.
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
- [x] Distinguish an unqualified user-defined `unordered_map` template from the supported `std::unordered_map` spellings. A regression asserts that it does not inject the translator's `cpp` adapter.
- [ ] Declare supported methods, overloads, template policies, exceptions, complexity expectations, lifetimes and ABI boundaries per adapter.
- [ ] Use ordinary Elisa names such as find, clear and size with overloads/uniform call syntax in module cpp.
- [ ] Emit adapter requirements only for reachable translated operations and report unsupported policy combinations before code generation.

Partial implementation evidence: current matching accepts `std::unordered_map` and
the tested `std::__1`, `std::__ndk1` and `std::__cxx11` spellings. The scanner
walks all projected AST descendants and parses top-level template arguments
while accounting for nested templates, parentheses, brackets and braces. This
is still spelling-based: canonical declaration/specialization identity,
aliases and reachable-operation-based injection remain required.

**Acceptance:** An unrelated same-named user type never triggers a standard-library adapter and unsupported operations have exact diagnostics.

### L02 — Complete unordered_map semantics incrementally [P1]

**Location:** cpp_lib/unordered_map.elisa and its generic lowering. **Depends on:** L01, C02–C04.

- [ ] Audit dict semantics against key equality/hash, default construction, value/reference stability, allocation and destruction requirements.
- [x] Make operator[] insert the supported scalar or nullable object-pointer mapped value on a miss; boxed fields preserve C++ zero/value initialization for the verified subset, including default-null pointer insertion.
- [x] Verify scalar mapped values remain readable after a 64-key insertion sequence forces repeated dictionary growth/rehash.
- [x] Verify enum keys use the default equality/hash path for hit, miss and non-inserting count operations.
- [x] Implement and verify non-inserting `contains`/`count`, key-based `erase`, `clear`, `size` and `empty` for the supported key/value subset.
- [x] Implement `find` and iterator/end comparison for the verified scalar subset, including hit/miss behavior, `first`/`second` reads and translated writes to `second`.
  - [x] Resolve supported iterator locals from their initializer before the generic class-template fail-closed check; only structurally recognized `unordered_map::find` results are exempt. The C++17 hit/miss fixture compiles and matches native execution; unrelated template-valued locals remain rejected.
- [x] Fail closed on address-taking or C++ reference binding to iterator `first`/`second`; the current adapter reads these projections by value and cannot preserve an element reference.
- [ ] Add insertion/emplacement APIs and complete source-visible iterator/reference semantics, including address-taking and reference binding to mapped values.
- [ ] Fail closed on unordered_map specializations with additional hash/equality/allocator template arguments rather than silently dropping policy types.
  - [x] The generic scanner rejects any recognized specialization whose top-level template-argument count is not exactly two; the existing real-Clang regression confirms the custom-hash case produces the policy diagnostic and no Elisa output.
  - [x] Extend the regression input with custom equality and an explicit nested allocator argument. A bounded Clang C++11 syntax check passes; this confirms the test cases are well-formed, not that translator diagnostics are correct.
  - [ ] Run the translator assertion for the expanded cases, requiring at least three policy diagnostics and empty Elisa output. The translator-level check remains pending a fresh build; the cached executable predates current Elisa source inputs.
- [ ] Preserve standard-required reference/iterator validity across insert/rehash/erase, using an appropriate storage design instead of assuming dict guarantees.
- [ ] Test allocation failures, key/value copy/move/destruction and actual Wolf operations without Wolf-specific branches.

Verified boundary (2026-09-14): integer and enum keys, integer/floating mapped
values and nullable object-pointer mapped values are accepted. Native-vs-Elisa tests cover
insert-by-index, read (including 64-key growth/rehash and readback), default-null pointer insertion, non-inserting
`contains`/`count`, `empty`, key-based `erase`, `clear` and `size`. The adapter
boxes values in an entry and projects `.value` only at recognized map
subscripts. A C++20 compilation-database project also translates `contains`
calls through the translator-owned adapter and matches native execution; the
adapter is imported once by the project manifest. This exercised generic UFCS
against the compiler's existing `set.contains` overload and exposed a stage1
receiver-selection bug. The isolated stage1 compiler now validates the fully
resolved receiver type after inferring generic arguments and passes hidden
store/arena ABI parameters consistently with direct generic calls. Its generic
`Index` field and dictionary-field regressions pass after a fresh, memory-capped
seed rebuild, as do fresh translator `projects` and `fixtures` suites. The
header-heavy C++20 case currently needs an explicit 256 MiB Clang-output cap;
the default 128 MiB cap rejects it cleanly, so calibration for header-heavy
units remains open. On 2026-09-29 the full fixtures suite caught that the
pointer default path was storing the zeroed-box address rather than its value;
the adapter now reads element `[0]` from the box. Native and translated
`unordered_map<int, const char*>` both exit 0 for a missing-key/null check, and
the complete fixtures suite passes with the isolated stage1 compiler/runtime.
This verifies only the supported scalar and nullable object-pointer subset.
Extra policy arguments, non-scalar class
mapped values, function-pointer values and pointer keys still fail closed.
The C++11 `find` lowering also now unwraps only same-type, one-child
`CXXConstructExpr` nodes, which Clang inserts around returned iterators. A
focused native-vs-Elisa fixture passes hit/miss comparison against `end`, key
and mapped-value reads, and mapped-value assignment; its generated Elisa
compiles and runs with the isolated stage1 compiler. The compatibility
iterator stores its owner and key, and `second()` reads by value while
translated assignments use `set_second()`; taking an address or binding a C++
reference to `second` is explicitly rejected with focused diagnostics (as is
reference escape for `first`). Insertion/emplacement APIs, custom hash/equality
policies, class/value construction, complete iterator/reference semantics,
collision-specific probing, allocation failures and broader
iterator/reference invalidation behavior remain unsupported or unverified.

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
- [x] Add recursive-call effect-propagation parity coverage: `recursive_global_effects.c` requires a `Global` effect to propagate through a branching self-recursive function and compares native/generated execution. The full 28-case acceptance manifest passes with the matched isolated Stage1 compiler/runtime pair; broader ABI and project matrices remain open.
- [ ] Compare exit status, exact binary/text outputs and meaningful state traces; normalize only documented nondeterministic fields.
- [ ] Use C/C++ harnesses to test translated library APIs without requiring every fixture to be a standalone main.
- [ ] Exercise optimized and debug Elisa builds where supported; compiler optimization defects must not be hidden by testing only O0.
- [ ] Classify source undefined behavior, implementation-defined behavior, translator mismatch and compiler/backend failure before interpreting differential results.

**Acceptance:** Intentional wrong lowering and ABI mismatches are caught by independent tests, with minimized reproducible artifacts.

### V02 — Property, metamorphic and fuzz testing [P1]

**Location:** proposed tests/property and tests/fuzz. **Depends on:** S01, V01.

- [ ] Generate bounded well-defined programs for integer operations, pointers, aggregates, sequencing and control flow.
- [ ] Compare semantic results before/after each rewrite where a small interpreter/oracle is practical.
- [x] Use a deterministic safe-renaming metamorphic check to detect name-dependent lowering. The bounded regression translates equivalent identifiers, normalizes the emitted Elisa names, requires byte-identical output, and separately verifies truncated C fails with empty generated stdout and a Clang diagnostic.
- [ ] Fuzz AST/projection parsers with malformed/truncated/oversized input and enforce allocation/time limits.
- [ ] Retain deterministic seeds and automatically minimize mismatches into permanent focused regressions.

**Acceptance:** Fuzz/property runs produce replayable failures and remain bounded; no translation rule depends on a target program's names.

### V03 — Measure idiomatic output quality honestly [P1]

**Location:** scripts/quality_report.sh, structured transformation report. **Depends on:** I01–I08, P05, V01.

- [ ] Measure residual dispatcher regions/states, duplicated code, unnecessary locals, proven redundant casts, assertion pressure and unsafe scope.
- [ ] Compute metrics from IR/rewrite records so source identifiers, comments and strings do not create false matches.
  - [x] Normalize generated-text pressure indicators by typed-IR expression, statement and function counts; report `n/a` for zero denominators. The report labels these emitted-text scans as heuristics and can include selected/pass/fail/unsupported/skipped/other outcome counts from a fixture-runner summary. An offline fake-translator regression covers ratios, zero denominators, complete coverage and malformed outcome data. Replacing the remaining text scans with structural facts is still open.
  - [x] Add record-kind-derived typed-IR counts and normalized rates for cast and sequence expressions, branch/loop/switch nodes, and loop/control nodes per function. The versioned dump's source-bearing fields are hex encoded, so these counts cannot be inflated by source identifiers, comments, or string literals. Fake-translator tests cover exact counts, zero denominators, and IR-lookalike rendered text that inflates only the explicitly heuristic text metric; this does not yet cover duplication, unnecessary locals, null-assertion provenance, or unsafe-scope structure.
  - [x] Fail closed when the quality reporter receives an unknown typed-IR version or a missing, duplicate, or malformed required count field, rather than reporting absent structural data as zero. It also checks expression/statement record totals and sequential IDs against the header to reject truncated, duplicated, or reordered node records. Fake-translator tests cover these malformed-dump cases.
- [ ] Normalize readability metrics by function/control complexity and report correctness/unsupported coverage alongside them.
- [x] Add normalized pressure rates for casts, null assertions, unsafe markers, synthetic/fallback names, lines and residual goto/label nodes; optionally report acceptance-run completeness and outcome fractions alongside them. These are comparison signals, not correctness scores or release acceptance gates.
- [x] Classify acceptance coverage by semantic family so a passing aggregate cannot conceal a weak area. Joining the saved 31-case run with the validated manifest taxonomy reports the single `c_void_pointer_boundaries` failure in ABI (7/8), pointers (7/8), and nullability (2/3), while integer semantics remains 4/4. This is old recorded evidence analyzed offline, not a fresh compiler run.
- [ ] Maintain curated before/after examples with reviewer notes for cJSON plus unrelated fixtures and projects.
- [ ] Gate only justified regressions; never reward dropping unsupported code, stripping licenses or compressing lines.
  - [x] Extend `scripts/quality_report.sh` with typed-IR and rewrite-record metrics (expression/statement/function/global counts, switch cases, goto/label counts and every applied readability-rule counter). The report still keeps rendered-output pressure metrics for casts, assertions and unsafe markers, but structural counts no longer depend on source identifiers, comments or string contents. The cJSON quality regression asserts nonzero IR counts and a valid rewrite counter.

**Acceptance:** Reports distinguish real semantic cleanup from text-count changes and every claimed improvement retains correctness evidence.

### V04 — Advance real corpora to verified acceptance [P1]

**Location:** testdata/upstream and corpus suite. **Depends on:** V01–V03, P01–P04.

- [ ] Pin upstream revisions, source licenses, translation commands and native build/link contexts.
  - [x] Record exact nested-repository commits for cJSON/Wolf4SDL, exact vendored Git subtree IDs for inih/Kilo, available license texts, the current small-corpus native/generated commands, and the local Wolf compile-database context in `testdata/upstream/README.md`. The original upstream commits for inih/Kilo were not retained, and the current Wolf compile database targets a separate machine-local SDL3 checkout rather than the vendored SDL2 Makefile; therefore the parent pin/build-context gate remains open.
- [ ] Keep inih, Kilo and cJSON as continuous regressions covering normal inputs, malformed inputs and relevant failure paths.
- [ ] Inventory every Wolf unit and dependency; progress from translation to compile, link, startup and deterministic runtime checks.
  - [x] Record the pinned vendored Wolf4SDL file/unit counts and native Makefile's SDL2 context, and distinguish them from the machine-local SDL3 compile-database fixture. Full dependency closure and per-unit translation/build status remain open.
- [x] Translate the bounded Wolf4SDL `wl_menu.cpp` project unit generically after projection filtering and ABI-signature recovery: 6,447 Elisa lines / 305,346 bytes, 140 external declarations, 113 functions, 44 records and 40 globals. The isolated optimized stage1 compiler emits valid objects at both `-O0` and `-O2`; three explicit backend-declined function bodies remain, so this is compile/object acceptance rather than a working Wolf executable.
- [ ] Debug Wolf crashes against native behavior with bounded reproductions, separating file lookup, ABI, memory and backend failures.
- [ ] Keep proprietary game data outside version control and generic CI; support explicit local data paths for authorized manual gameplay tests.
- [ ] Add independent projects that challenge each new semantic family so acceptance cannot overfit existing corpora.

**Acceptance:** Each corpus has an honest stage/status matrix; compile-only success is never reported as a working game or equivalent library.

### V05 — Bound memory and profile throughput [P0/P1]

**Location:** driver, AST pipeline, scripts and benchmarks. **Depends on:** B01, F02, V04.

- [ ] Start with one heavy Clang/compiler job; measure peak RSS for parent and children plus system memory pressure.
  - [x] Run one bounded cJSON translation with process-level attribution and contemporaneous host-memory sampling. The pre-fix 512-MiB limit stopped the translator at 574,496 KiB sampled live RSS after its Clang child exited; the process group was reaped without a crash. This is a capped failure sample, not a successful baseline or calibrated peak, and must be repeated after the latest retention fixes.
- [x] Reserve RSS polling headroom to limit overshoot: stop at `cap - min(cap / 8, 64 MiB)` rather than waiting for a sampled value to exceed the cap. The four bounded-runner tests pass with the safety-threshold behavior; the same 512-MiB cJSON probe then stopped before the nominal cap. This is conservative polling protection, not an OS-enforced hard limit.
- [x] On aggregate-limit failures, print an owned-process RSS breakdown to distinguish Clang from translator growth without raising the cap. The focused regression asserts the diagnostic includes member RSS; a direct live-process probe confirmed the `ps` parsing on macOS. A pre-fix cJSON breakdown showed the translator alone consuming the sampled RSS after Clang exited; repeat on the rebuilt translator to see whether the provenance fix changes the profile.
- [ ] Set configurable input/projection limits, per-process deadlines, worker count and retained-unit/cache budgets.
  - [x] Bound the translator object-build and link process groups with configurable aggregate RSS and wall deadlines. `scripts/run_bounded_process.py` starts a dedicated POSIX session, samples the group (including ordinary descendants), and signals only that owned group; four self-tests cover status/output preservation, descendant termination, RSS breach and invalid limits. The default build bound is 2 GiB / 600 seconds, configurable through documented environment variables. Whole-suite aggregate memory, translation worker count and retained-unit/cache budgets remain open.
  - [x] Add a configurable monotonic deadline to every Clang frontend child invocation, defaulting to 600 seconds and capped at 86,400 seconds. Direct input and both compilation-database command forms are covered, including invalid values, no partial publication, and process-group descendant cleanup. Total-input, worker-count and retained-unit/cache budgets remain open.
- [x] Release translation-unit arenas when their data is no longer referenced; retain only required project summaries. The normal project path destroys each `source_translation` region after writing its staged module. Persistent cross-unit symbols, signatures and field summaries now use `translator_project_arena` via `arena_da_append` (their copied text is in `perm_arena`), avoiding both stale table pointers and retention of the Clang AST/lowered IR. The three-unit call-across-units fixture, four-unit extern-object project in both input orders, and two-unit cJSON translation all complete; compile/runtime evidence is recorded above where applicable.
- [ ] Profile hot paths before optimizing, including repeated AST searches, type-string scans, JSON copies and global string storage.
  - [x] Profile and reduce repeated JSON traversal in the dependency/source-fact and top-level projection passes, and remove unneeded linkage wrappers from large C++ projections. A cJSON run with the isolated self-hosted stage1 compiler remains 2,836 lines / 149,947 bytes with identical native/generated output. The bounded Wolf4SDL `wl_menu.cpp` run now completes in 185.23 seconds at roughly 335 MiB peak translator RSS and emits 6,447 lines / 305,346 bytes; the previous 1,000,000-value guard failure is gone without raising the guard.
  - [x] Add opt-in frontend phase/function counters and bound recursive global-effect analysis with shared expression/function depth marks. Full `cJSON.c` translation now completes at 130,912 KiB peak RSS / 147,505 KiB physical footprint and emits 2,789 lines / 150,429 bytes; before the fix, output emission recursing through `cJSON_Compare` reached 933,440 KiB sampled RSS and was stopped by the 1-GiB guard. The upstream smoke suite now keeps this full-file translation under a 512-MiB / 180-second bounded regression. This closes that recursive effect-analysis memory regression, not the remaining V05 profiling, total-input-budget or worker-budget work.
  - [x] Repeat the full `cJSON.c` translation after the deadline change using the isolated latest Stage1 compiler pair. It completed under the existing 512-MiB / 180-second process-group bound in 19.35 seconds at 123,040 KiB RSS / 131,329 KiB physical footprint, producing 2,787 lines / 150,184 bytes with `cJSON_Compare`, `cJSON_Parse`, and `cJSON_PrintUnformatted` present. This validates large-unit translator stability, not backend acceptance of the emitted file.
- [ ] Increase concurrency only when aggregate memory remains within a calibrated host budget; prioritize avoiding swap storms.
- [x] Terminate only owned Clang process groups on timeout, reap the child, and preserve bounded diagnostics/reproducers. The 1-second fake-Clang regression verifies source-qualified errors and descendant cleanup for direct, `command`, and `arguments` launches; frontend stderr remains capped at 1 MiB.

**Acceptance:** Repeated large-unit/project runs show bounded retained memory and documented latency/throughput without exhausting the host.

### V06 — Track and fix Elisa compiler capability gaps [P1]

**Location:** isolated stage0/stage1 worktrees; translator compatibility tests. **Depends on:** B01, V01.

- [ ] Probe every required Elisa feature through small compiling/running examples: slices, aggregate syntax, nullable functions, varargs, indexing, raw-pointer operations and foreign exports.
- [ ] Minimize backend traps, invalid LLVM, pointer truncation, layout mismatches and optimizer miscompilations before changing compiler code.
- [x] Fix a generic malformed-LLVM case caused by mixed-width compound assignments: `i32 += i16/i8` and `i8 += i32` now receive explicit destination-ABI scalar conversions in direct statements and value helpers. The fresh Wolf unit compiles at stage1 `-O0` and `-O2` with no invalid-IR diagnostic; three function bodies are still explicitly declined by the backend for field/index-expression capability gaps.
  - [x] Add a translator-side ABI boundary for integer/character literals used in comparisons with call results. The generated C++ map adapter no longer feeds a raw wide Elisa literal to an `i32` call result; ordinary variable-based expressions retain their readable uncast spelling.
- [x] Make the generated-translator link boundary runtime-consistent: an explicitly selected stage1 product links with only its matching runtime object, while the default stage0 build retains its profile-hook path. The cache fingerprint includes the selected runtime hash and link mode, preventing a stale mixed-runtime translator from being reused.
- [ ] Implement compiler fixes in isolated worktrees, add compiler-owned regressions and record dependency commits here.
- [x] Integrate current main-worktree gains by inspecting commits and dirty state, preserving local fixes and verifying the resulting compiler identity. The isolated Stage1 branch merges latest committed main `bb5a13cf` in `9e1ddcbc`, resolving the single escape-analysis overlap by retaining the newest `rows`/origin analysis together with the isolated `Expr.Move` and container-root safeguards. The main worktree's 36 tracked edits and 11 untracked test/fixture files were imported without modifying the main checkout; shared untracked files match byte-for-byte, and the isolated export-alias marker-pair guard remains as an additional local fix. Recovery stashes are retained. The guarded source-fresh reseed did not complete; its exact stop condition and unchanged product hashes are in `docs/execution_status.md`.
- [x] Refresh the dedicated local stage0/stage1 compiler worktrees from the current main worktrees without disturbing unrelated compiler checkouts: stage0 is fast-forwarded to `e42bbdfe`, and stage1 is created at `98261837`. The local stage0 build and matching stage1 executable/runtime identities are recorded in `docs/execution_status.md` (2026-09-28).
- [ ] Migrate translator Clang-JSON access from the stdlib's now-private `JsonValue`/`JsonMember` representation and raw child-copy helpers to its public region-indexed `JsonValueHandle[r]` API. Keep AST views tied to the parse arena and avoid duplicating the full JSON tree, so this compatibility update does not regress large-translation-unit memory use.
  - [x] Replace the translator's raw DOM-facing access with region-indexed handles. A 2026-09-29 source audit found no `JsonValue`/`JsonMember` type use or child-copy helper in `src/`; `emit_program` parses directly into `ast_arena`, adopts `parsed.value` with `json_handle_from_result`, and stores the same-region root in `TypedContext`. AST helpers are region-parameterized and JSON-backed text returns `sview @r`; the stdlib handle accessors wrap existing arena nodes rather than cloning arrays/objects. The refreshed Stage1 build and fixture suite pass; quantitative large-unit memory comparison remains open.
- [x] Rebuild the translator from current source with the refreshed local compiler pair, then run the short-enum ABI fixture and focused translator suites; do not treat an older translator executable as evidence of a fresh source build. The latest Stage1 source-fresh product/runtime rebuilt the translator; frontend-failure and timeout regressions passed, and the cJSON source translated under a bounded memory/time guard. Exact identities and the remaining single backend decline are recorded in `docs/execution_status.md` (2026-10-01).
  - [ ] Build/test a source-fresh Stage1 product from merge `e8f7469e` plus the current imported main-worktree edits, then rebuild the translator against that exact pair. The `-O3`, two `-O2`, and `-O0` seed attempts were safely stopped at nearly the same physical-footprint boundary (no crash/artifact leak); changing bootstrap optimization alone did not lower the peak. Pause further seeds pending the user's choice between a carefully higher bounded ceiling in an idle window and source-level bootstrap-memory reduction. Details are in `docs/execution_status.md`.
- [ ] Test translator and generated outputs with both compiler stages as their support permits; keep stage1 decline visible until it is actually resolved.
  - [x] Cross-check the current C const-binding output with native C, isolated Stage0 and refreshed Stage1. It preserves ordinary immutable Elisa bindings and separately encodes pointee mutability; the three executions agree.
- [ ] Require a full translator/corpus compatibility check before switching the default local compiler.

**Acceptance:** Missing language features are implemented or accurately tracked with reproducers; default toolchains have recorded translator compatibility evidence.

### V07 — Packaging, CLI UX and reproducible releases [P1/P2]

**Location:** CLI, README, proposed docs and release scripts. **Depends on:** P04, V01, V04–V06.

- [ ] Provide explicit options for language/standard/target, compilation configuration, output policy, diagnostics, budgets and compiler/runtime paths.
  - [x] Expose `--frontend-timeout-seconds N` with validation, a 600-second default, an 86,400-second maximum, and help/README documentation. Other language, target and compiler/runtime selection options remain open.
- [ ] Remove development-time dependence on the default sibling compiler-worktree path.
  - [x] Replace source-level fixed worktree includes with an ignored `src/.compiler_std` link targeting `ELISA_STAGE1_STDLIB` (defaulting to the selected stage1 worktree); setup/test refuse conflicting paths, validate the required runtime/JSON/collections modules, and fingerprint the selected standard-library Elisa sources. A shell regression covers spaced paths, creation, idempotence, conflicting links, non-symlink collisions and missing/incomplete roots.
  - [x] Confirm include expansion and a fresh translator build with a non-default isolated Stage1 standard-library root. A temporary source copy linked to a separate copied `elisacore_std` tree compiled and linked with the latest local Stage1/runtime; the resulting binary passed `--help` and translated the simple C fixture. This validates include resolution and a fresh build, not relocation of a packaged release.
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

The `cpp` compatibility module remains in this repository. External-function declarations remain Clang-derived. Compiler work is limited to implementing and validating Elisa capabilities required by correct translation; it does not expand this document into a general Elisa compiler roadmap.

## 9. Initial implementation slices from the inspected state

1. **Establish the translator baseline:** inventory current work, compiler provenance and fresh verification results, then complete B01's execution ledger.
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
