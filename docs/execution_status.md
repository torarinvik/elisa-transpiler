# Translator implementation evidence

This ledger records fresh results for work in `IMPLEMENTATION_PLAN.md`. A
feature is not complete merely because a handler exists or translation exits
successfully; generated Elisa must also be compiled, linked, and exercised
where applicable.

## Latest isolated compiler source synchronization — products pending safe rebuild — 2026-10-05

The dedicated Stage0 worktree was fast-forwarded from `6a0628cc48a7` to the
committed Stage0 `main` head `11858f2e6347b63cb4e9bf674f299471d2f3404f`;
the dedicated Stage1 worktree was fast-forwarded from `8e08cd3397b1` to the
committed Stage1 `main` head `2691a64c7522c94eee0d5b0b930d1995c7376a3c`.
Both private worktrees were clean before synchronization and are clean at the
new revisions. The corresponding main checkouts contain uncommitted edits;
only their committed heads were incorporated, and those working changes were
left untouched.

The local Stage0 executable and Stage1 executable/runtime still match the
previous source revisions (`6a0628cc` and `8e08cd33` respectively). The
compatibility manifest records both the current source revision and each
artifact's source revision, marks freshness false, and keeps translator
validation pending. Do not use these products as current-source verification;
rebuild Stage0 and Stage1 from the refreshed worktrees, then rebuild the
translator and rerun focused plus serial acceptance tests.

No compiler was launched for this synchronization. A fresh host sample fell
to 38% free memory with a Stage0 debug compiler process active; the shared
Stage1 seed lock was absent, but the 60% build floor was not met. The bounded
build gate remains closed.

The later provenance audit found the private Stage1 checkout at `2691a64c`
has a modified tracked `.DS_Store`. That unrelated file was not reverted. The
compatibility manifest now marks Stage1's source worktree dirty, and its
provenance test checks that the recorded cleanliness matches `git status`
instead of assuming that a previously clean checkout stays clean. Do not
describe this checkout as clean; compiler products are already stale relative
to its source revision.

## High-half unsigned narrowing regression — unverified — 2026-10-05

Extended the generic `integer_constant_semantics.c` fixture to cast high-bit
`uint64_t` constants into `uint8_t`, `uint16_t` and `uint32_t`, and added
emitted-shape assertions for the expected normalized values. This specifically
checks modulo-width normalization when the evaluator carries the source value
as a negative raw `i64` bit pattern. `git diff --check` and the affected shell
suite's syntax check pass. No native/generated compile or execution result is
claimed: while checking compiler availability, a separate Stage1 seed held
the shared build slot and system-wide free memory was 55%, below the test
driver's 60% floor. The expanded regression remains pending a safe compiler
window.

## Compiler compatibility provenance and cache invalidation — in progress — 2026-10-05

Added `docs/compiler_compatibility.json` with the isolated Stage0 and Stage1
source revisions, clean-worktree assertions, executable/runtime SHA-256
identities, artifact source revisions plus Stage1 build-recipe/source-tree
hashes, and the target triple. The
manifest explicitly says current translator-source validation is pending; the
recent formatter change and acceptance fixtures have not yet been built and
rerun against this pair. `scripts/test.sh` now folds the manifest hash into
the translator input fingerprint, and `scripts/test_build_cache.sh` verifies
that changing the manifest changes that fingerprint. The new three-test
`scripts/test_compiler_compatibility.py` validates the manifest shape, guards
against reporting pending validation as verified, and checks the pinned
revision/cleanliness/artifact hashes when the isolated local worktrees exist.
The three manifest checks, cache mutation regression, shell syntax, and
`git diff --check` pass without launching Elisa.

At the implementation snapshot, host free memory was 42% and another Stage1
seed build held the shared lock, so compiler-backed validation remained
paused. The manifest is a provenance record for the latest audited local
compiler worktrees, not a claim of successful Stage0-to-Stage1 reproduction or
translator behavior compatibility. Fresh snapshots after these small
self-tests ranged from 34% to 48% free memory; the latest is 36%. The shared
lock has been repeatedly reacquired by separate compiler tasks. Its current
owner is live seed-script PID 41020 with Stage0 compiler PID 41114 (about 2.3
GiB RSS); an unrelated Stage1 build is also active. No compiler process was
started by this task. The safe-build gate therefore remains closed.

## Quality-report normalization and acceptance coverage — partial — 2026-10-05

Extended `scripts/quality_report.sh` to use an explicitly selected local
translator (`ELISA_TRANSLATOR_BIN`), normalize generated-text pressure counts
against typed-IR expression/statement/function counts, and optionally attach
the fixture runner's outcome summary. Zero denominators print `n/a`; coverage
reports selected/result totals, whether all selected cases have recorded
outcomes, pass fraction, and each distinct result category including
unsupported, skipped, timeout, crash, resource-limit, monitor-error and
missing-tool counts. The raw emitted-text metrics are explicitly labeled as
heuristics because patterns inside string literals can still contribute; this
does not complete the plan item for structural-only measurements or duplicated
code/unnecessary-local analysis.

Added structural counts from typed-IR record kinds for Cast and Sequence
expressions, If/For/While/DoWhile/Switch statements, and normalized cast,
sequence, control-node, and loop-node rates. These use the stable `expr` and
`stmt` record kinds rather than searching emitted Elisa. The fake-translator
regression verifies exact structural counts/rates and zero-denominator `n/a`
output, and demonstrates that IR-lookalike text in generated output can inflate
the explicitly heuristic text count without changing structural counts.
`sh scripts/test_quality_report.sh`, shell syntax checks, and
`git diff --check` pass without invoking Elisa. V03 remains partial: source-text
pressure scans are still heuristic, and duplicate-code, unnecessary-local,
null-assertion provenance, and unsafe-scope structural metrics are not yet
implemented.

The quality reporter now requires the exact `typed-ir-v13` dump header and
exactly one counts record with each denominator it consumes (`exprs`, `stmts`,
`switch_cases`, `functions`, and `globals`). Unknown dump versions and absent,
duplicate, or malformed required count values fail with an explicit error
instead of silently becoming zero-valued readability measurements. It also
checks that expression and statement records have sequential indices and that
their totals match the counts header, rejecting truncated, duplicated, or
reordered structural input. The fake-translator suite exercises these failure
cases; these checks validate reporter input integrity and do not replace
translator/IR correctness tests.

`sh scripts/test_quality_report.sh` passes with a fake translator, checking
normalization, zero-denominator behavior, outcome reporting and rejection of
unknown result categories. The acceptance manifest now assigns every case to
one or more validated semantic families; the runner carries those tags into
per-case pass/fail/skip records. The coverage reporter also joins an older
summary to the manifest taxonomy when its saved results predate tag
propagation, and verifies summary counts agree with result statuses.

Offline analysis of the saved `manifest-unsigned-full` 31-case result (not a
new compiler run) reports 30/31 overall, ABI 7/8, pointers 7/8, nullability
2/3, and integer semantics 4/4. The one failed fixture is
`c_void_pointer_boundaries`, making the failing semantic families visible
instead of hiding them in the aggregate. `scripts/test_fixture_manifest.py`
now passes 20 tests, including complete family classification and propagation
into normal/skipped results; `scripts/test_quality_report.sh` passes the
family-join and family-rate regression. These tests use no Elisa compiler and
do not validate fresh real-corpus metrics. The quality test is included in the
canonical `scripts/test.sh` preflight.

## Host-wide build safety and Stage1 translator compile — in progress — 2026-10-05

On macOS, `scripts/run_bounded_process.py` can read the system-wide free-memory
percentage before launch and while an owned process group is running. It
refuses a preflight at or below the floor, terminates only its owned group if a
live sample reaches the floor, and fails closed if monitoring is unavailable.
The local compiler-setup default floor is 41%, while the canonical `test.sh`
entry point defaults to 60%; both are configurable through
`ELISA_SETUP_MIN_SYSTEM_FREE_PERCENT`, and the bounded runner inherits that
variable when no command-line floor is supplied. Local compiler setup applies
the gate to Stage0 builds, Stage1 seeds and runtime builds; `test.sh` gates the
translator object/link build and the manifest runner gates each fixture stage.
These host limits supplement—not replace—per-process-group RSS,
physical-footprint, output and deadline limits.

## Direct shell-suite process bounds — implementation in progress — 2026-10-05

Added a shared `test_run_bounded_process` helper and routed direct translator,
Elisa compiler, Clang and Clang++ commands in the four sourced shell suites
through it. Per-tool RSS limits and deadlines are configurable with
`ELISA_TEST_TRANSLATOR_*`, `ELISA_TEST_ELISA_*` and
`ELISA_TEST_NATIVE_*`; on macOS they inherit the test driver's 60% free-memory
floor unless explicitly overridden. `run_bounded_process.py` gained an
opt-in quiet-success report mode so runner telemetry does not contaminate
captured typed-IR dumps or successful compiler diagnostics, while nonzero
commands and limit breaches still report resource evidence. Stage1 shell-driver
calls retain their existing internal process-group limits.

The compiler-bearing Python integration probes in `test.sh` now run inside an
aggregate bounded process group as well. This covers each harness's Python
memory (including captured Clang AST JSON), translator calls, native Clang
builds and Elisa object compilation together. The cap and deadline are
configurable via `ELISA_TEST_PYTHON_PROBE_MAX_RSS_KB` and
`ELISA_TEST_PYTHON_PROBE_TIMEOUT_SECONDS`; a wiring regression fails if a
compiler-bearing probe is later added to the canonical driver without the
wrapper. This bounds canonical test runs; running those Python files directly
still bypasses the outer harness limit.

`sh scripts/test_test_support.sh`, `python3 scripts/test_run_bounded_process.py`,
shell syntax checks and `git diff --check` pass with fake children. No Elisa
compiler or translator acceptance command was run for this change: at the
latest snapshot another compiler process was active and host free memory was
53%, below the test driver's 60% floor, so the memory-sensitive end-to-end
suites remain pending.

Validation on 2026-10-05: `scripts/test_run_bounded_process.py` passes 12 tests,
including environment-default propagation, preflight refusal when the sampler
fails, threshold refusal and termination after a simulated live memory drop.
`scripts/test_fixture_manifest.py` passes 18 tests, including preflight refusal
on monitor failure and owned-stage termination. Stage1
freshness regressions, shell syntax, Python byte-compilation, source line
limits and `git diff --check` also pass. A source-fresh Stage1 product from
commit `8e08cd3397b1680c61bfb76b70e1a76541522e3d` compiled
`src/main.elisa` to `build/transpiler.o` using `-emit obj -O0`; the object SHA-256
is `d23591ccf2e728ca1142d228b48c8a5ac454b1ecc7ba0490c8172bf8e59703ce`. The
bounded run peaked at 313,616 KiB process-group RSS and 284,354 KiB physical
footprint, with host free memory bottoming at 51%. This compile verifies the
recent explicit C ABI pointer-erasure boundary in `clang_process.elisa`.

Continuation self-tests on 2026-10-05: `python3 scripts/test_fixture_manifest.py`
passed all 18 tests, `python3 scripts/test_run_bounded_process.py` passed all
12 tests, and `sh scripts/test_build_cache.sh` passed its fingerprint/hash/
executable checks. These tests use fake or small child processes and do not
exercise Elisa translation. At the latest host snapshot, the shared seed lock
was absent and no Elisa compiler process was visible, but system free memory
was 54%, below the 60% floor for the pending source-fresh translator rebuild.
Subsequent memory samples ranged from 46% to 53%; the latest is 48%, with the
shared seed lock absent and a separate Docker compiler validation active (PID
45738). A local Stage0 compile observed immediately beforehand has exited. The
translator rebuild remains gated until a fresh sample exceeds 60% and no
competing compiler work is active.
The next check showed 43% free, no shared seed lock, and an unrelated Linux-host
Stage1 compile (PID 48039, about 382 MiB RSS). The prior Stage1 processes had
finished; this new process again leaves the translator rebuild below the safe
threshold.

The object was then linked against the matching private Stage1 runtime using
the bounded runner, a 512-MiB RSS cap and a 60% host floor. Linking exited 0;
the resulting arm64 executable `build/elisa-c-transpiler` has SHA-256
`8f24c7644167bd5b2c8680d97e0a4b945fb3957c28c54dd38637ea5b30a2b771`. Link
peak process-group RSS was 2,640 KiB and host free memory remained 75%.

`runtime_unsigned_wrap` exposed that C's `(unsigned int)-1` was emitted as
`-1` in a `u32` initializer. The generic target-value emitter now normalizes
compile-time integer values modulo the unsigned destination width, including
the raw-bit-pattern case for `u64`. Its fixture covers max values for `u8`,
`u16`, `u32` and `u64` plus dynamic `u32` addition and multiplication
wraparound. The focused fixture passes native/generated compile, link,
execution and parity. The full 31-case manifest now passes 30 cases, with only
`c_void_pointer_boundaries` failing during generated Elisa compilation. The
manifest's lowest host free-memory sample was 63%; the focused object and
executable hashes are respectively
`de5b0d4d11aceccc124e3abd8d0aad5461fe771e2daf59a732424b10aa5f917c` and
`ecbdc62c24bd0acc9975e6850174509eea1f33c037ef5f113dae43ddb11f3b88`.
JSON validation, source line limits, diff checks and all 30 runner tests pass.

Follow-up on 2026-10-05: expanded `integer_constant_semantics.c` with uint64
unary negation, high-bit AND/OR/XOR, high-half division/remainder, a defined
u32-to-u64 cast, and `<=`, `>=`, and `!=` comparisons. Added generated-source
shape assertions for those folds in `scripts/test_suites/core_fixtures.sh`.
`git diff --check`, the shell syntax check, and source line-limit check pass;
translator emission, Elisa compilation, runtime parity, and the exact generated
shapes remain unverified until a safe toolchain window. At an earlier snapshot
the host was below the Stage1 build floor (41% free):
`${TMPDIR}/elisac-stage1-global-seed.lock` contains PID 41862, whose live seed
script has Stage1 compiler PID 41900 at about 1.04 GiB RSS; a separate Docker
compiler validation is also active. Do not launch Stage1 work until those jobs
finish and memory remains above the 60% floor. Subsequent snapshots below
supersede this one.

Later the same day, a bounded translation of the expanded integer fixture using
the already-built (pre-fix) translator stopped with `EXC_BREAKPOINT` in
`CTranslator.append_i64`. A bounded LLDB run localized it to signed negation of
`INT64_MIN` while formatting the high-bit `u64` AND result; the process group
peaked at 113,504 KiB RSS / 72,562 KiB physical footprint, with host free memory
bottoming at 44%, and exited normally after LLDB captured the stop. The generic
`append_i64` implementation now computes negative magnitude in `u64`, avoiding
that overflow. The fixture additionally requires exact signed-minimum emission.
Static checks pass, but the translator binary predates this source fix, so the
new source has not yet been compiled or exercised. A previous 58% host sample
had no seed lock and a Docker compiler validation active. The latest check is
53% free: the correct shared seed lock was held by PID 90705 (Stage1 compiler
PID 90748, about 1.10 GiB RSS), and a separate Stage0 compile (PID 90440, about
1.67 GiB RSS) was active. Those processes have since exited and the lock is
currently absent. A fresh 30-second memory poll ranged from 50% to 55% free,
ending at 53%, while two unrelated Linux-host Stage1 compiles remained active.
A new continuation snapshot is 44% free with the shared seed lock held by PID
5015 (Stage1 compiler PID 5060, about 1.92 GiB RSS); another Linux-host Stage1
compile (PID 4688, about 1.24 GiB RSS) and a local Stage1 compile (PID 9355,
about 443 MiB RSS) are also active. The compiler-build floor remains unmet.
After the 30-second recovery poll, memory ranged from 48% to 51% free and ended
at 49%. A new seed attempt has since reacquired the shared lock (PID 23472;
compiler PID 23511, about 1.70 GiB RSS); another Stage0 compiler (PID 23955,
about 1.70 GiB RSS) is active as well. No translator or Elisa build was started.
That seed later completed and released the lock, but the newest sample remains
below threshold at 52% free while a separate Linux-host Stage1 compile (PID
37136, about 586 MiB RSS) is active. The 60% floor still prevents our build.

The `c_void_pointer_boundaries` failure is now reproduced in the saved October 5
acceptance run: translation exits 0, but the pinned Stage1 compiler exits 1
with `view "restored" cannot be used: storage dependency facts were invalidated
by darray push of slot`. The generated Elisa contains no `darray.push`; `slot`
is a pointer into a fixed two-element array. The saved generated source SHA-256
is `1a392a149abd1a64d3c058b5a2db05dc11a3b27b444c739ff14f9f8c5fe7c9a0`, and
the result record SHA-256 is
`4412204768874fc1f289f72cfcbee88e291621a1dc3a6d91e8a6583f8651538a`. The
compiler identity for that run matches the pinned Stage1 commit and executable
in `docs/compiler_compatibility.json`.

Read-only tracing of that Stage1 source identifies a narrower candidate than
the earlier `void`-is-nonscalar hypothesis: `param_growth_summary.elisa`
routes `Stmt.Return` values through `pgs_expr(..., escape=true, ...)`; for a
user call, `pgs_user_argument` treats `escape` as `pgs_place_grows`, so returning
the mutable alias from `identity_slot` can enter the callee's relocation/growth
summary despite the body performing no write. Separately,
`storage_callee_param_may_relocate` classifies a mutable reference to opaque
`void` as potentially relocatable. This points to a missing distinction between
“mutable alias escapes” and “callee grows/replaces storage”; it is a source-level
hypothesis, not yet a compiler fix. A reduced compiler regression and a fresh
compiler build/test are required before changing the summary semantics. No
fixture-specific rewrite is being used to hide the failure.

The bounded runner initially refused a translator rebuild at 58% host free
memory. Once compiler load subsided and a fresh lock/freshness check passed,
the translator object compiled at `-O0` with 321,696 KiB peak RSS / 292,402
KiB peak physical footprint and a 63% minimum host-free reading; linking and
the 31-case run also stayed above the 60% floor. The authoritative shared
seed lock is `${TMPDIR}/elisac-stage1-global-seed.lock` on this Mac, not
`/tmp/elisac-stage1-global-seed.lock`. A fresh process check found that lock
owned by a live Stage0 seed (PID 55794; compiler RSS 1,145,184 KiB) and host
free memory at 53%. The earlier `/tmp` directory check was not a valid lock
check. The latest snapshot shows the actual seed lock free and no Elisa
compiler process visible, but host free memory is still 55%, below the 60%
floor. No further compiler probes should start until a fresh check clears
that floor.

## Translation-result region ownership — implementation in progress, partially compiler-verified — 2026-10-03

The result-lifetime recovery now makes `TypedTranslation` and generated source
spans explicitly live in the CLI's per-translation-unit region. The CLI
consumes output, diagnostics and optional source maps before that region exits;
the nested Clang JSON arena is still freed before returning from translation.
Source-map text is interned into the result region so repeated file/include
paths are not copied once per generated span. Diagnostic views are copied into
the region that owns their containing array. Project-map output is assembled
directly in its state-owned buffer rather than escaping a short-lived local
array. Compilation-database JSON handles now name their parser region
explicitly, and its source accumulator uses a `while` loop while adding units.

Static checks pass: `bash scripts/check_source_line_limits.sh`, shell syntax
checks and `git diff --check`. A bounded Stage1 probe first exposed arena
region-fact invalidation from freeing the AST on parse/schema error branches;
the translator now has one common `arena_free` after all AST uses. The next
probe then isolated a backend decline on a nested `copied.as_cstr()` call in
the region-copy helper. Splitting that conversion into a local binding cleared
the decline. The translator object compiled (peak 417,488 KiB RSS / 570,274
KiB physical footprint), linked with its matching runtime, and translated
`testdata/fixtures/simple.c` into a two-file Elisa project. Stage1 compiled
the generated project, it linked with the same runtime, and the executable
returned the expected value 42. A separate single-file source-map smoke
produced valid JSON with nine mappings and one hashed source record. Build-cache,
test-attribution, fixture-manifest, bounded-process and local-stdlib-link
harness tests also pass. The larger upstream cJSON source translated to a
3,099-line, 188,281-byte module at 132,672 KiB peak RSS. Compiling its project
manifest with this Stage1 candidate still declines seven function bodies at
function-pointer aggregate initialization and pointer-index/assignment sites
(`elisa_init_cJSON`, `cJSON_InitHooks`, `utf16_literal_to_utf8`,
`cJSON_CreateStringArray`, the two comment-skipping helpers, and `minify_string`).
That is an Elisa backend/codegen boundary, not a failure to translate cJSON;
the emitted project object was not produced.

The full `scripts/test_source_map.py` suite now passes against that same
source-fresh translator binary. It validates source and project-map JSON,
final generated-byte bounds, macro expansion-to-output correlation, spelling
and expansion origins, synthesized control-flow span reasons, immediate include edges, FNV-1a-64 source hashes,
translation units with no mapped spans, symlink/output collision refusal,
transaction rollback, and byte-for-byte deterministic single-file and project
maps. The suite uncovered test assumptions that project-map unit order matched
the command-line argument order; project units are now selected by canonical
`translation_source`, avoiding an accidental API constraint. The suite accepts
`ELISA_TRANSLATOR_BIN` so it can run against an explicitly selected local
product without replacing the default build artifact. Under the 512-MiB /
180-second process-group guard it passed with 17,296 KiB peak aggregate RSS and
11,201 KiB peak physical footprint. Translator binary SHA-256:
`8ee2c63e812d1a579b2cbeb2e0233bd3f626a1c2ce0b2d5e08fcd7dca58f8049`. The
compiler pair was isolated Stage1 HEAD `78560716d410903a517d9caaf746e7190fd8bfb7`,
compiler SHA-256
`83a67d979653969334bb9522fb55f718624633df6e18ed9e7365dd73c463f1db`, and
matching runtime SHA-256
`424aaf9f49da71988809232ce658234ce97acf470ff02ab663e92f6fa09b1442`.
This closes the source-map CLI verification against the latest committed
compiler product, but does not include compiler-main's separate uncommitted
changes or close P06's rewrite-explanation and complete diagnostic-report
obligations. A follow-up host check found the seed-lock directories clear, but
unrelated Stage0/Stage1 compile and test processes had resumed and system-wide
free memory was 42%; no compiler seed or refresh was started.

A follow-up probe against the source-fresh translator found a specific P06
diagnostic gap: the record-valued conditional reported its source, type and
missing capability, but its source range was `-1/-1`. Raw Clang JSON showed a
valid range; the projection classifier had dropped it because
`ConditionalOperator` and `BinaryConditionalOperator` do not use the `*Expr`
suffix. The generic classifier now retains both kinds, and a rebuilt
translator confirmed the exact half-open range. The focused Elisa schema
harness asserts both kinds are expressions, while
`scripts/test_diagnostics_json.py` checks the source slice and human/JSON
diagnostics; the core fixture suite expects the precise missing capability.
That test then exposed Clang's location elision: the conditional carries an
offset and column but no `line`. The translator now lazily recovers the line by
counting LF/CRLF/CR line breaks in the effective source file, with a
per-translation-unit forward scan cursor, and the regression requires exact
line and column values. Compiler-backed validation passed:
`testdata/ast_projection_schema_test.elisa` compiled, linked and ran;
`scripts/test_diagnostics_json.py` passed on both the original LF fixture and
a CRLF copy; the full `scripts/test_source_map.py` and
`scripts/test_clang_failure.sh` suites passed; and native versus translated
`simple.c` both compiled/linked and exited 42. Source line limits,
shell/Python syntax checks and `git diff --check` pass. The translator object
build peaked at 321,376 KiB RSS / 292,129 KiB physical footprint under a 1-GiB
process-group cap. The source-map suite used a 512-MiB cap; the Clang-failure
suite needed a 1-GiB cap because its nested frontend probes can exceed the
lower wrapper limit.

This fresh isolated build used Stage1 seeded from compiler commit
`0bc93f57c9a5aabbc4d0128719983c65c77d0a38` on branch
`s1/append-only-store`, a direct descendant of compiler-main HEAD
`9533908052d2dbfb00afc3460fdef658ce7a32d0`; it linked the matching runtime.
Stage1 binary SHA-256:
`b95ebcf58e2d942b510be711538719aa5285ed2406b0b4c0973e284ba9cf6978`;
runtime SHA-256:
`424aaf9f49da71988809232ce658234ce97acf470ff02ab663e92f6fa09b1442`;
translator SHA-256:
`332a3fe480d609d65822d6f1dac459577fdca243a4cec352de98221bf6773f7d`.
The build used an isolated copy of the translator source linked to that
compiler snapshot's standard library; the workspace `.compiler_std` symlink
was not changed. This product includes the compiler commit above, but not
subsequent uncommitted compiler-main or scratchpad changes. It verifies this
diagnostic work against a freshly seeded latest-available local product, not
against those still-dirty compiler edits.

The Stage1 binary used is from the isolated compiler worktree at committed
HEAD `78560716`, which matches compiler-main's committed HEAD. Compiler-main
also has uncommitted parser, semantic and backend changes that are not in this
binary, so this verifies the latest committed compiler revision, not those
dirty working-tree changes. Refreshing a compiler from that dirty tree remains
unverified; the shared seed lock and concurrent build load made that refresh
unsafe during this pass. The isolated translator snapshot is
`build/translator-stage1-probe.4NtI4X`.

## P06 origin records — implementation in progress, not compiler-verified — 2026-10-02

The optional expression/statement origin side tables now retain primary
half-open byte ranges plus distinct Clang macro spelling and expansion ranges,
including the source filename and Clang's explicit immediate `includedFrom`
edge. Nodes introduced by lowering without their own Clang node inherit the
parent range and carry a synthesized-node explanation. The normal translation
path still leaves origin capture disabled, so this work does not add per-node
origin allocations to ordinary runs.

The statement emitter now also records nested generated byte spans and returns
their source metadata in the translation result. Source file and include-edge
spellings are copied out of the Clang JSON arena before return. An opt-in
formatter path carries source byte positions through whitespace normalization
and line wrapping, then remaps spans to final Elisa byte offsets. The CLI now
exposes this path through `--source-map-json`; it remains unverified until the
fresh translator and formatter-parity harness are compiled and run.

The focused diagnostic-origin harness now also checks macro spelling versus
expansion offsets, filenames and the immediate include edge. Static validation
passed (`check_source_line_limits.sh`, shell syntax checks, and `git diff
--check`). The Elisa harness and translator were not compiled or run: the user
selected waiting for a safe Stage1 build window; competing compiler jobs are
still live, and system-wide free memory has ranged from 49% to 56% during this
work.
At the time of this entry, source-content hashes, source-map serialization/CLI
support and end-to-end map assertions were still unimplemented; P06 was not
complete at that earlier checkpoint.

Update later on 2026-10-02: opt-in `--source-map-json PATH` enables the existing
origin capture, serializing deterministic JSON with generated byte spans,
three source-origin ranges, immediate include edges, synthesized reasons and
streaming FNV-1a-64 hashes for origin files and every root translation unit,
including units with no emitted spans. Single-file output is
staged beside its destination and published with rename. Project mode accepts
a map path in `--output-dir`, aggregates one source map per translation unit,
bounds total source bytes and JSON output, and includes the map in project
backup/rollback/publish alongside modules and manifest. End-to-end
determinism, macro-origin, hash, path-collision and failed-translation
preservation checks were added to the core fixture suite; compiler-backed
execution remains pending.
Static source-line, shell-syntax and diff checks pass. These Elisa changes have
not been compiled or exercised: no compiler process or seed lock is currently
visible, but free memory is 48% and swap use is about 9.8 GiB, so compiler work
is still deferred until the system has recovered enough headroom. P06 remains
open pending compiler-backed validation and review of project-wide map output.
The compiler audit also found divergent dirty checkouts: main is at
`bb5a13cf` and the isolated Stage1 worktree at `e8f7469e`, with six main-side
commits not yet present on the isolated branch and 47/30 dirty paths
respectively. The isolated compiler therefore cannot yet be called the latest
main compiler; reconcile those changes without discarding either worktree's
local edits before the required compiler-backed validation.

The latest host check on 2026-10-02 found the global and worktree-local seed
locks clear and no Elisa compiler process, but only 36,645 of 1,572,864 pages
free (about 2.3%); an unrelated native maze smoke process remained live. No
compiler build was started. The source-map and integer-folding edits in this
turn pass static checks, but their Elisa compilation and end-to-end regressions
remain pending.

A subsequent check found only 7,178 free pages (about 0.46%); the same native
maze smoke process (PID 43223) was still live after 1:30:42, while both Stage1
seed locks remained clear and no Elisa compiler process was present. Compiler
refresh and generated-Elisa validation remain deferred at this lower headroom.

A read-only Git merge-tree preview of isolated Stage1 `e8f7469e` with compiler
main `bb5a13cf` finds one committed-history content conflict in
`src/semantic/check_local_view_return_escape.elisa`; the other committed paths
auto-merge. The dirty-path comparison found 22 main-only paths, five
Stage1-only paths, and 25 shared paths; 24 shared working files are byte-equal,
while `src/backend/codegen_export_aliases.elisa` differs. No compiler index or
checkout was modified; this conflict and the differing local file still need
careful reconciliation before a fresh product can be built.

## Clang frontend monotonic deadlines — 2026-10-01

Every direct-file and compilation-database Clang child now shares a configurable
absolute monotonic deadline across stdout capture and process completion. The
default is 600 seconds; `--frontend-timeout-seconds N` accepts positive decimal
values through 86,400. Darwin uses `CLOCK_MONOTONIC` (id 6); the implementation
also tries the Linux `CLOCK_BOOTTIME` id before falling back to Linux
`CLOCK_MONOTONIC` (id 1). Polling wakes at most every 100 ms, so continuous
stdout cannot extend the deadline. On expiration the translator sends SIGKILL
to the dedicated Clang process group, reaps its direct child, discards partial
AST output, and reports the source path. Clang stderr remains captured through
the existing 1-MiB diagnostic cap.

The first end-to-end probe exposed a result-contract bug: the child-wait helper
returned `1` to mean “reaped”, while its caller compared that sentinel to the
actual PID. The caller now converts the sentinel to the PID only on successful
reap; this was why Clang capture falsely failed despite successful polling.
`scripts/test_clang_timeout.py` covers direct input and both compilation
database forms (`command` and `arguments`), rejects timeout value zero, checks
source-qualified diagnostics and empty stdout/project output, and uses a fake
Clang grandchild marker to verify process-group cleanup. It passed against a
fresh translator object compiled by local Stage1
`elisac-stage1-callbackfix-final-v3-o1` and linked with its matching runtime.
The standalone simple-C translation, focused timeout regression, full
`scripts/test_clang_failure.sh` frontend suite, `git diff --check`, and source
line-limit gate all passed. These checks exercise the Darwin implementation;
the alternate Linux clock-id path still needs an actual Linux host run. The
same freshly built translator then translated the full
`testdata/upstream/cJSON/cJSON.c` under the existing 512-MiB / 180-second
process-group guard: 19.35 seconds, 123,040 KiB peak RSS, 131,329 KiB peak
physical footprint, and 2,787 lines / 150,184 output bytes. The emitted file
contains `cJSON_Compare`, `cJSON_Parse`, and `cJSON_PrintUnformatted`; this
validates the new capture path on a large unit, not backend compilation or
runtime parity. Translator binary SHA-256:
`e14d1f7635677d545b70b9416f22da960a6402d69391d935c5136ad29fea7292`.

## Non-default Stage1 standard-library include path — 2026-10-01

To verify actual include expansion rather than only the link-selection shell
logic, a temporary copy of translator `src/` was compiled with its
`src/.compiler_std` link pointed at a separate copy of the selected isolated
Stage1 `elisacore_std` tree. The local Stage1 compiler
`elisac-stage1-callbackfix-final-v3-o1` and its exact matching runtime built
and linked that copied source successfully; the resulting binary printed help
with `--frontend-timeout-seconds N` and translated
`testdata/fixtures/simple.c`. The build process peaked at 359,840 KiB RSS /
454,945 KiB physical footprint under a 1.5-GiB / 300-second bound; the final
link peaked at 832 KiB RSS / 3,521 KiB physical footprint. The temporary tree
is under ignored `build/nondefault-stage1-stdlib.*`; its translator binary
SHA-256 is `9a6b43c561550b1878e01a6eaabaa0978ee082bc9ed9abf484e3c83204e224e0`.
This proves compiler include resolution against a non-default standard-library
path. It does not prove the full translator can be packaged and run outside
this workspace.

## Stage1 compiler source refresh audit — 2026-10-01

The Stage1 main checkout had one committed change beyond the translator's
isolated compiler worktree: `d8b5d305` (“Keep refinement scope names
region-safe”). That commit was merged into
`../elisa-transpiler-worktrees/transpiler` as merge commit `a9ef46ce`. Its one
content conflict was resolved by retaining the isolated branch's stable local
copies of both place-root names; the main branch's `later_root_name` diagnostic
value is retained as well. The merge changed the semantic refinement checker
and did not overwrite the isolated worktree's prior edits.

The Stage0 isolated worktree remains eight commits ahead of its clean main
checkout. The Stage1 main checkout currently has 36 modified tracked paths and
11 untracked paths; those in-progress changes were deliberately not copied into
the isolated compiler worktree. The isolated Stage1 worktree still has its own
pre-existing local edits. The verified Stage1 product/runtime hashes recorded
above therefore identify the product used for the completed translator
deadline/cJSON checks, but that product predates merge `a9ef46ce` and is stale
relative to the refreshed Stage1 source. A fresh seed is pending: at audit time
another Stage1 `-O2` build was active and macOS reported only 56,634 of
1,572,864 pages free (about 3.6%), with substantial swap activity. No competing
compiler build was started, and no main-checkout uncommitted files were
modified. The refreshed Stage1 source must be reseeded and its matching runtime
reverified before it is used for further acceptance claims. A later read-only
check found that the other build had exited but free pages had fallen to 7,423
(about 0.5%), with no compiler process remaining; the seed remains deferred
until host memory pressure recovers.

## Stage1 product verification before latest-main merge — 2026-10-01

After the preceding audit, the competing compiler process exited and the
isolated Stage1 worktree was reseeded once under a 4-GiB inner RSS ceiling and
a 5-GiB / 600-second owned-process-group ceiling. The seed completed and left
no live seed process or lock. Its source is Stage1 worktree HEAD
`a9ef46ceea8f05495f84ffa1fe108b1094ad3946`, plus the worktree's pre-existing
local edits (`src/backend/codegen_expr_cast.elisa`,
`src/parser/parser_extern_params.elisa`,
`test/parity/extern_fn_struct_ref_smoke.sh`, and
`test/repro/extern_nullable_fn_param.elisa`). No `.elisa`/`.elisai` source was
newer than the emitted product at verification time. Stage0 came from isolated
worktree HEAD `e42bbdfe8a1b8123c3c4bfd096d64eb4c97c8b11`, binary SHA-256
`24d761b47f987db09c0b76abc32492fc515ecc667b8ff07c7b381c1521a63002`.

The freshly seeded Stage1 product SHA-256 is
`90883a468a821b9f1a27bf9479f66fd0da3e8fca873f7d241585a56a699c744a`; its
seed object SHA-256 is
`8c93a3232d337e0598e6856413dd5c87486ebf7e67f8396a28dc13abea5ab226`. The
matching runtime was built separately from that exact product under a 2-GiB /
300-second bound; its SHA-256 is
`6a8d933dc5d9e77d491de34225ca21b7a37c117182e1e0e14d3a3e20ff6afc5e`. The
runtime build peaked at 83,008 KiB RSS / 47,906 KiB physical footprint.

Using this pair, the current translator source built under a 1.5-GiB / 600-
second bound (386,944 KiB peak RSS / 452,737 KiB physical footprint); the
translator executable SHA-256 is
`b05029936fb84d3138277eadb605ce13eb0aa40d96c6d078baab967916109b6f`. The
full frontend-failure suite and `scripts/test_clang_timeout.py` both passed,
including direct Clang, compile-database `command`/`arguments`, and descendant
cleanup cases. Full standalone cJSON translation passed the 512-MiB / 180-
second bound at 118,848 KiB RSS / 132,721 KiB physical footprint, emitting
2,789 lines / 150,429 bytes (SHA-256
`0ca0335a2fd964bf93c7e9104f79a857f202dbc40a9f8621c6ec095b497d4afd`) with
`cJSON_Compare`, `cJSON_Parse`, and `cJSON_PrintUnformatted` present.

Compiling that emitted file with the same refreshed Stage1 product under a
2-GiB / 300-second bound still fails closed: exactly one body is declined,
`cJSON_CreateStringArray` at its pointer-array index expression. No object was
written; peak RSS was 43,664 KiB and peak physical footprint 18,449 KiB. This
is an improvement over the seven declined bodies observed with the newer main-
worktree product, but it is not full cJSON backend acceptance. The main
compiler checkout's 36 modified tracked paths and 11 untracked paths remain
unmerged; they were not silently copied into the isolated worktree. The
translator compiler binary/object/runtime and emitted cJSON file are kept in
ignored `build/` artifacts for inspection.

## Latest committed Stage1 main merge and bounded reseed — 2026-10-01

The isolated Stage1 branch was further synchronized with the current Stage1
main commit `3ad04d3a` (“Close six escape gaps found by an adversarial
stage0/stage1 sweep”), which was 25 commits ahead of the prior merge base
`d8b5d305`. Git's merge preview reported no conflicts; merge commit
`e8f7469e69e0e4cedaee7af1908ac7da0d5ee402` now contains main as an ancestor.
This brings in committed backend and semantic work including large-aggregate
`memmove` lowering and newer escape-analysis/backend-decline fixes. The
isolated worktree's pre-existing local edits remain intact. Main's uncommitted
tracked/untracked work remains separate and untouched.

The user's request to include the latest main-worktree gains also covers its
uncommitted source/tests. Those were audited as 36 tracked paths plus 11 new
test/fixture paths. A plain patch did not fit the later Stage1 source, but a
read-only three-way check succeeded for every tracked edit. The edits and new
files were then imported into the isolated Stage1 worktree; its pre-existing
translator-specific edits and untracked regression remain intact, its index
was returned to clean, and `git diff --check` passes. The main compiler
checkout was not modified by the import. The next source-fresh seed therefore
includes both the committed merge and this current in-progress compiler work.

The first reseed of this newer source at `-O3` was contained by the process
guard rather than the OS: its 5-GiB / 600-second process-group runner stopped
at the aggregate physical-footprint safety threshold of 3,885,413 KiB before
the stage0 object finished. The runner terminated the owned process group and
reaped the child; no final compiler, object, or runtime was published, and both
seed locks were released. Memory pressure recovered to 45% free afterward.
After the other task released the host-wide seed lock, an `-O2` retry started
with a 3-GiB Stage0 RSS cap and a 4-GiB process-group cap. The bounded runner
stopped it at its conservative aggregate physical-footprint threshold of
3,190,757 KiB (peak RSS 2,776,192 KiB), before the seed finished. This was a
guard stop, not a compiler crash; the process group, lock, and temporary
product/object/runtime were cleaned up. Memory pressure returned to 48% free.
The host currently has unrelated Elisa compiler jobs consuming multiple GiB,
so the next retry waited for a compiler-idle window with at least 45% memory
free (an evidence-based threshold: the previous isolated attempt remained
stable down to 41% free). With a 5-GiB process-group cap, 4-GiB Stage0 RSS cap
and 15-minute timeout, the next `-O2` seed was again stopped by the process
group's conservative physical-footprint guard: 3,898,341 KiB footprint versus
the 3,883,008-KiB stop threshold (peak RSS 2,923,344 KiB), at about 5 minutes.
The owned process group and seed locks were cleaned; no product/object/runtime
was published. This is a repeatable peak in this source's EDIR code generation,
not an OS/compiler crash. A subsequent `-O0` bootstrap (same 5-GiB aggregate
cap / 4-GiB RSS cap) reached the same boundary: 3,888,709 KiB physical
footprint against a 3,883,008-KiB stop threshold (peak RSS 2,231,120 KiB) at
about 5m40s, before a product was published. It ran while other independent
compiler jobs were active; system free memory fell to 33%, so this task's owned
group was stopped and the runner cleaned up. The lock was then acquired by a
separate seed; that owner's lock and work remain untouched. A different build
optimization level has not materially reduced peak physical footprint. The
next options are an explicitly higher bounded ceiling during an idle window or
a source-level reduction to bootstrap memory; do not start another seed until
the user selects the resource tradeoff.

## Recursive effect-call analysis memory bound — 2026-10-01

The translator's `Global` effect inference followed call edges recursively to
a fixed depth. A recursive callee reached through multiple branches was
revisited along every path, and each nested statement traversal allocated a
new expression-depth table sized to the complete function IR. This made the
work and transient allocation grow rapidly on large recursive functions. The
generic fix shares expression-depth marks and per-function maximum remaining
depth marks for one effect query; a function is revisited only if a later path
reaches it with more remaining depth. This bounds cycles without dropping the
existing depth-limited effect search.

`--frontend-stats` now optionally reports phase, function start/completion,
typed-IR counts and emitted byte counts to stderr. Ordinary translations do
not enable these diagnostics and retain their previous output channel and
format. The new counters located the cJSON corpus spike after all 113
functions had lowered and passed IR verification, inside emission of the
self-recursive function; the issue was not AST projection or AST-arena size.

Before the fix, that trace reached `cJSON_Compare` with only 143,252 emitted
bytes, then hit the bounded runner at 933,440 KiB sampled RSS / 999,554 KiB
physical footprint. After the fix, the same full-file translation completed:
23,665,267 raw Clang JSON bytes, 4,472,535 projected bytes, 271,844 projected
JSON values, 27,467,200 parsed-arena bytes, 12,474 indexed declarations, 6
records, 27 fields, 4 globals, 113 lowered functions, 6,457 expressions and
1,848 statements. The pre-format output was 147,562 bytes; final output is
150,429 bytes / 2,789 lines. The bounded process peaked at 130,912 KiB RSS
and 147,505 KiB physical footprint (about 7.1x lower sampled RSS than the
guarded pre-fix run). This is translation/resource evidence only: the full
cJSON Elisa still has known backend-declined function bodies and was not
accepted as a compiled/running program here.

The upstream smoke suite now retains this as a bounded full-file translation
regression: it requires the representative `cJSON_Compare`, `cJSON_Parse` and
`cJSON_PrintUnformatted` definitions and a nontrivial output size, with default
limits of 512 MiB RSS and 180 seconds. The exact suite command was separately
validated with the diagnostic translator and completed at 135,936 KiB sampled
RSS / 147,313 KiB physical footprint.

The generic `recursive_global_effects.c` fixture verifies that `Global`
effects still propagate through branching recursion; native and generated
executables agree and return zero. The full 28-case acceptance manifest passed
with the isolated Stage1 executable SHA-256
`4f6457d89d13185e6839c3baf8a04e93b83573d5c47c69220905dff4a31698f` and its
matching runtime SHA-256
`6a8d933dc5d9e77d491de34225ca21b7a37c117182e1e0e14d3a3e20ff6afc5e`.
The focused frontend diagnostics suite and the source-file line-limit gate
also pass. A complete `scripts/test.sh --suite fixtures` run was not obtained
in this slice; an earlier attempt stopped on transient Clang target-macro and
compile-database failures, while the corresponding bounded direct probes and
focused frontend suite subsequently passed.

## Runtime-sized darray probe is not VLA support — 2026-10-01

The isolated Stage1 compiler/runtime pair recorded below compiled and ran a
minimal runtime-sized comprehension:

```elisa
values: mutable darray[i32] = [zeroed for index in 0..<count]
```

This verifies only that Elisa can construct a runtime-count collection. It is
not a valid general lowering for C VLAs: the comprehension writes `zeroed` to
every element, while a C automatic VLA has uninitialized storage; the
collection uses region-backed allocation rather than C's block-scoped
automatic storage; and source `sizeof` must use the bound evaluated when the
VLA is declared, not a later read of a potentially mutated bound variable.
Clang JSON's local `VarDecl` exposes the type spelling `int[count]`, but no
typed expression node for `count`. Full VLA translation therefore remains
fail-closed pending a bound-expression contract, checked size/alignment,
uninitialized dynamic storage and scope/lifetime handling. No C VLA fixture is
promoted to supported by this syntax probe.

## Clang record-layout capture for pointer subtraction — 2026-10-01

The direct-file and compilation-database Clang paths now request
`-fdump-record-layouts-simple` together with the JSON AST. The bounded stdout
capture separates the leading layout dump from the AST before JSON validation
and projection, so the normal AST pipeline remains unchanged. Typed lowering
stores matched record size/alignment and field offsets in a side table. The
first consumer is intentionally narrow: pointer subtraction can use a
complete, non-union record size only when its Clang field-offset count matches
the collected fields and the declaration has no packed/alignment-sensitive
attributes, bit-fields, C++ bases or explicit member functions. The Clang
layout parser accepts either tag spellings or typedef spellings, so it also
handles anonymous records exposed through typedefs; this is generic type/layout
matching, not a cJSON-specific rule. Layouts are associated by canonical Clang
declaration identity rather than emitted Elisa name, allowing aliases of one
record to share facts without conflating same-named declarations. Injected C++
record names may use their shared source location as a conservative identity
fallback. Compiler-generated implicit special members do not disqualify a C++
record, but explicit methods remain conservative. Union, packed-record,
ambiguous and unavailable layouts remain a source diagnostic with no emitted
Elisa. General record padding, field-offset emission and foreign aggregate ABI
are still open under S06/P03.

The `record_pointer_difference.c` fixture checks a padded `{ char, int }`
record and a nested/typedef-backed record with a trailing fixed array. It
compiles, links and matches native execution; generated Elisa divides byte
address differences by the Clang sizes (`8` and `16`). The separate
`record_sizeof_alignof.c` fixture verifies Clang-derived `sizeof` and
`_Alignof` values for flat and nested/typedef-backed records (`8`/`4` and
`16`/`4`) and their two-element arrays (`16` and `32` bytes; alignment `4`)
against native C. Elisa emits those record constants as target-sized integer
literals, rather than using Elisa's potentially different aggregate
`size_of`. The typed-IR dump is now v13 and reports deterministic record-layout
rows without exposing Clang's process-specific declaration IDs. The five
focused executable manifest cases for scalar/enum/pointer
pointees, record pointer differences, record size/alignment,
record-versus-array aggregate shape, and `void *` conversions pass
native/generated runtime parity. Both union and packed-record pointer-difference negative fixtures fail
closed with empty generated stdout. Separate `sizeof(union ...)` and
`_Alignof(packed struct ...)` probes also fail closed with the corresponding
diagnostic and empty generated stdout. A one-source compile-database
translation passes the target-ABI output-shape checks; the scalar
typedef-array `sizeof` emission shape also remains unchanged.

## cJSON smoke and fixture-suite checkpoint — 2026-10-01

The generic layout changes were checked against the cJSON smoke translation
without adding any cJSON-named or source-specific handling. The translator
emitted the 1,605-line Elisa smoke program, the isolated Stage1 compiler/runtime
compiled it, and its executable stdout matched the native C executable
byte-for-byte (`{"name":"elisa","items":[1,true,null]}`). The quality report
recorded 3,990 IR expressions, 1,063 statements, 117 casts, 495 nonnull
assertions, 9 integer-fold rewrites and zero invalid-IR markers.

The complete `fixtures` test suite was rerun with the cached translator and
the pinned local Stage1 compiler/runtime: all 26 manifest cases passed with no
timeouts, crashes or resource-limit failures, and the core fixture suite
passed, including fail-closed unknown-union pointer subtraction and
variable-length `sizeof` bound evaluation. Frontend/schema, bounded-AST,
metamorphic, declaration-closure and C++ record-layout checks also passed. The
suite reported one expected capability skip: the selected Stage1 backend
declines a separate `offsetof` call-expression probe. The standalone source
line-limit check and `git diff --check` pass as well. This checkpoint does not
claim that the entire upstream or project suites have been rerun.

## Macro-expanded exported function retention — 2026-10-01

Clang may omit a repeated `loc.file` on a later declaration in the main source
file. For export-macro functions, `range.begin` then carries the main-file
`expansionLoc.offset`, while `isUsed` can be absent. The previous projection
discarded such a declaration and could turn references to a public function
into an unresolved external. The generic source classifier now recognizes a
source macro expansion when its expansion path matches the main source, or
when Clang omits both the file and `includedFrom` under main-file provenance.
It does not inspect library names or cJSON declarations.

`macro_exported_api.c` reproduces the exact missing-file/`isUsed: null` shape
after a preceding source declaration. The translator now emits the otherwise
unreferenced `exported_api_value` definition; a separate native C harness and
the generated Elisa object both link and return success. The regression is
wired into the core fixture suite. A source-fresh translator build with the
pinned isolated Stage1 pair peaked at 473,504 KiB RSS / 445,522 KiB physical
footprint under the 1-GiB cap. The first full fixture run stopped at its cJSON
quality command when Clang transiently failed processing `cjson_smoke.c`; a
direct quality-report retry passed. A second serial run with the cached build
completed the entire `fixtures` suite: all 26 manifest cases passed, the core
fixture script reached and passed the macro-export link test, and the runner
reported no crashes, timeouts or resource-limit failures. The backend's
`offsetof` call-expression capability skip remains expected.

After the fix, standalone `cJSON.c` translation emits 2,789 lines / 150,429
bytes with 120 function definitions, including `cJSON_Delete`, `cJSON_Parse`
and `cJSON_PrintUnformatted`; the prior output had left these as externals or
omitted them. This exposes, rather than fixes, remaining backend limitations:
the pinned isolated Stage1 product declines `cJSON_CreateStringArray` at its
pointer-array index expression. The newer main-worktree compiler product
(SHA-256
`c9120725bde202e70ea9ff94c9b87ab2026770eb5b29e95bfc1bc285f76eb9cf`, with
runtime SHA-256
`4a25cda85e118d59355bc437cb4e6ca15cbd96212d861198dc003bb3a3d733cb4`)
declines seven bodies involving index expressions/assignments; it emits no
partial object. Both runs were bounded and stayed below 50 MiB RSS. The
single-file cJSON smoke remains 1,605 lines / 37 functions, compiles with the
pinned isolated Stage1 compiler, and still matches native stdout exactly. Its
quality report is unchanged at 3,990 expressions, 1,063 statements and zero
invalid-IR markers.

The translator was freshly rebuilt with the isolated Stage1 binary
`../elisa-transpiler-worktrees/transpiler/bin/elisac-stage1-callbackfix-final-v3-o1`
(SHA-256
`4f6457d89d13185e6839c3baf8a04e93b83573d5c47c69220905dff4a31698f`) and its
matching runtime (SHA-256
`6a8d933dc5d9e77d491de34225ca21b7a37c117182e1e0e14d3a3e20ff6afc5e`). The
latest bounded source build peaked at 461,088 KiB RSS / 434,465 KiB physical
footprint under the 1-GiB RSS cap. Source line
limits, manifest JSON, shell syntax, and `git diff --check` pass. After the
array-safety guards, seven focused native-parity manifest cases, the
layout/variable-array fail-closed probes, scalar typedef-array `sizeof` shape,
and the compile-database target-ABI shape passed. The full fixture/project
suites, cJSON and upstream suites were not rerun.

## Nested aggregate shape distinction — 2026-10-01

The new generic `record_and_six_element_array.c` fixture places two similarly
sized initializers side by side: six scalar fields in `SixFields`, and six
elements nested in the `values` array field of `SixElementArray`. Generated
Elisa preserves the distinction as `SixFields{first: ..., sixth: ...}` versus
`SixElementArray{values: [...]}`. The acceptance case checks both emitted
shapes and compiles, links, and matches native C at runtime with the pinned
Stage1 compiler/runtime pair. No source-specific translator handling was
added. This closes the matching S06 shape regression, not the broader flexible
array, VLA, compound-literal-lifetime, or aggregate-ABI work.

## Flexible, zero-length, and variable array safety boundary — 2026-10-01

`flexible_array_member_probe.c` exposed that an incomplete trailing C array was
being emitted as an Elisa reference field (`data: u8&`), which changes the
record's size and ABI. Record collection now diagnoses flexible-array members
at the source field and suppresses generated Elisa instead of publishing that
misrepresentation. Similar guards now reject zero-length record members and
local zero-length arrays, local VLA bounds that remain nonconstant in Clang's
type spelling, and pointer-to-VLA parameter types. Their probes require a
source-qualified diagnostic and empty generated output; the checks are wired
into the core fixture suite. Seven positive native-parity manifest cases
covering fixed arrays, designated initializers, record layouts, and pointer
decay still pass after these guards. This does not claim support for tail
allocation/access, the one-element struct hack, all variably-modified function
types, allocation extents, or lifetime contracts; those remain open.

## Indexed call result-type verification — 2026-10-01

Typed user-overload and external-signature rows now retain an explicit result
type extracted from the same resolved Clang function type used by lowering.
Before emission, indexed user calls must agree with both the exact lowered
definition's function type and the selected signature's result type; indexed
external calls must agree with the selected external result type. A mismatch
is a verifier error, not an Elisa cast inferred from output text. The stable
typed-IR dump was advanced to v12 and includes the result type.

The standalone verifier compiled and ran with the pinned local Stage1 compiler
and matching runtime. New negative cases reject a mismatched user-call result,
a selected definition with a different function type, and a mismatched
external-call result; dump checks confirm stable result-type serialization.
The freshly rebuilt translator passed the complete `control-flow` suite, and
the `cpp_overloads` acceptance case compiled and matched native execution. The
build remained under the 1-GiB cap (369,248 KiB RSS / 425,922 KiB physical
footprint). This validates indexed call-result integrity only; implicit
argument conversions, non-indexed calls, and return-statement conversion/type
verification remain open. Validation used the pinned isolated Stage1 binary
and runtime whose hashes are recorded in the canonical-call section below.

## Indirect function-pointer call arity — 2026-10-01

The typed-IR verifier now validates fixed and variadic arity for recognizable
indirect function-pointer calls directly from Clang's function-type spelling.
Its generic splitter tracks nested function declarators, arrays and C++ template
arguments, so commas inside callback parameter types do not inflate the outer
arity. It treats C's `(*)()` as an old-style no-prototype type (no fixed arity
constraint) and C++'s `(*)()` as a zero-parameter prototype; `(void)` is zero
parameters in either language. Unrecognized forms remain outside this focused
check rather than being guessed from emitted source text.

The standalone verifier harness compiled and ran with the pinned local Stage1
compiler and matching runtime. It covers fixed-call under/over-arity, variadic
minimum arity, nested callbacks, C's unspecified-parameter form and C++'s
zero-parameter form. A fresh translator rebuild followed by the complete
`control-flow` suite passed, including real indirect-call and function-pointer
fixtures. The bounded translator build peaked at 454,144 KiB RSS / 425,377 KiB
physical footprint under a 1-GiB cap. The installed Elisa compiler was not
used; the exact isolated Stage1 product and runtime hashes are recorded in the
canonical-call section below. The cJSON/upstream and project suites were not
rerun during this slice.

## Canonical declaration-bound call signatures — 2026-10-01

Indexed user-function signatures now retain the canonical Clang declaration ID
and the exact lowered `TypedFunction` index. `TypedFunction` and `TypedExtern`
rows also retain declaration identity. C++ call lowering resolves the
`DeclRefExpr` target through the translation-unit declaration index and stores
the selected signature index in the call IR. Name/type fallback is used only
when Clang supplies no declaration ID and exactly one candidate matches; an
ambiguous fallback is rejected. The pre-emission verifier checks that every
indexed user signature points to an in-range function with the same canonical
ID and matching fixed-arity/variadic metadata. The v11 dump records only
whether an ID exists, not Clang's unstable opaque ID text.

The standalone typed-IR verifier compiled and ran successfully with the local
Stage1 compiler/runtime. In addition to the existing direct/indirect/external
and arity cases, it constructs two user functions with the same name and type
but different declaration IDs, proves the second signature selects the second
function, and rejects a mismatched signature-to-function identity. A real
Clang C++ overload fixture passed native/generated differential execution.
`control-flow` passed in full. The `fixtures` run rebuilt the translator and
passed all 21 acceptance-manifest cases plus frontend, AST-depth, metamorphic,
declaration-closure and C++ adapter checks before stopping at the cJSON quality
report: Clang failed while processing `testdata/upstream/cJSON/cjson_smoke.c`.
An isolated retry was deliberately bounded at 1 GiB and stopped at 854,914 KiB
physical footprint / 787,728 KiB RSS; the cJSON quality and upstream suites
were therefore not verified in this run.

The project suite's first run passed through its local and cross-unit C++
overload checks, then stopped because a reversed-order external-declaration
case received an empty Clang target-macro result for `mutable_pointee.c`. A
bounded retry failed earlier on the same symptom for `beta.cpp` in the
reversed anonymous-namespace project. Both files translate individually, and
direct Clang macro queries for the checked sources return the expected ABI
macros; the multi-unit query failure remains unresolved, so project-wide
verification is inconclusive rather than green.

The translator rebuilt from current source with a 1 GiB build cap and peaked at
453,984 KiB RSS / 424,946 KiB physical footprint. Verification used the
isolated local compiler product
`../elisa-transpiler-worktrees/transpiler/bin/elisac-stage1-callbackfix-final-v3-o1`
(SHA-256 `4f6457d89d13185e6839c3baf8a04e93b83573d5c47c69220905dff4a31698f`)
and its matching runtime (SHA-256
`6a8d933dc5d9e77d491de34225ca21b7a37c117182e1e0e14d3a3e20ff6afc5e`). The
compiler worktree includes current main commit `3fa4a7e5` as an ancestor and
is two local commits ahead; its selected binary includes the isolated
callback/parser/backend fixes. The installed compiler was not used. Source
line limits and `git diff --check` pass.

Argument conversions and return-type consistency still need semantic records;
broader namespace/template/operator overloads and stable project-wide
verification remain open.

## Indexed call arity verification (prior v10 baseline) — 2026-10-01

Typed user-function signatures now retain their fixed parameter count and
Clang's `variadic` declaration flag. External signatures already retained the
same facts. Before emission, the typed-IR verifier requires an exact argument
count for fixed signatures and at least the fixed count for variadic ones; a
malformed negative count is rejected. This is generic metadata-driven logic:
it does not name or special-case any upstream program. The typed-IR dump schema
was v10 at this verification point and included the new user-signature fields;
the declaration-identity update above advances the dump to v11.

The standalone verifier harness compiled and ran successfully with the local
Stage1 compiler and its matching runtime. It covers fixed and variadic calls
through both user and external signature tables, too-few and too-many fixed
arguments, missing required variadic arguments, and serialization of the
signature metadata.

Fresh bounded verification results with the isolated Stage1 compiler/runtime
pair described in the following entry:

- `scripts/test.sh --suite fixtures --reuse-build` passed against a fresh
  translator rebuild, including 21 native/generated acceptance cases, the
  core fixture suite, and C++ overload/map coverage. No crashes, timeouts, or
  resource-limit events occurred. The existing `offsetof` executable-parity
  backend skip remains.
- `control-flow`, `projects`, and `upstream` suites also passed with the same
  arity enforcement, covering structured/CFG calls, cross-unit calls, cJSON,
  inih, and Kilo. The standalone harness was rerun after adding the final
  negative-metadata guard and passed.
- The translator rebuild peaked at 452,384 KiB process-group RSS / 424,274 KiB
  physical footprint. The final fixture-suite test process peaked at 133,968
  KiB RSS / 64,547 KiB physical footprint under a 1-GiB group cap.

The first fixture-suite attempt stopped once at the inline-dependency closure
check because target macros were empty; that check passed immediately in
isolation and in the subsequent complete fixture runs. Argument type
conversions, return-type consistency, canonical declaration identity, and
indirect-call arity inference remain open.

## Nullable C callbacks and refreshed local Stage1 verification — 2026-10-01

The translator/compiler boundary now handles nullable C callback parameters
without special-casing an upstream program. The Stage1 extern-parameter parser
recognizes the parenthesized `(fn(...) -> R)?` type form while requiring the
inner token to be the literal `fn`, so ordinary parenthesized reference types
are not misclassified. Optional function-value casts use the backend's
`optional_is_niche` ABI rule, matching the existing nullable-pointer
representation. In the translator, a zero-argument Elisa function is retained
as a direct callback for a C `(void)` prototype instead of being needlessly
converted through an opaque pointer.

The isolated compiler worktree has a regression fixture that passes a nullable
function value through an extern parameter and has a C stub invoke it. The
generated executable observes the mutation and exits with the expected status.
The translator and compiler were tested with the explicit local Stage1 product
`../elisa-transpiler-worktrees/transpiler/bin/elisac-stage1-callbackfix-final-v3-o1`
and its matching runtime object
`../elisa-transpiler-worktrees/transpiler/build/runtime/elisacore_runtime.callbackfix-final-v3-o1.o`.
The compiler worktree is at `230dbf03284917c7be7a04695b9753d3769dea93`;
the selected product includes the uncommitted parser/backend changes described
above.
The selected product SHA-256 is
`4f6457d89d13185e6839c3baf8a04e93b83573d5c47c69220905dff4a31698f3`, and the
matching runtime SHA-256 is
`6a8d933dc5d9e77d491de34225ca21b7a37c117182e1e0e14d3a3e20ff6afc5e`.
The installed compiler was not used.

Fresh results with that pair:

- `scripts/test.sh --suite upstream --reuse-build` passed: inih and cJSON
  native/generated parity matched, and Kilo compiled and matched its no-argument
  native behavior. Kilo's C `atexit` callback now needs only the explicit ABI
  cast `(editorAtExit).cast[void&]`.
- `scripts/test.sh --suite control-flow --reuse-build` passed.
- `scripts/test.sh --suite projects --reuse-build` passed, including the C++
  `unordered_map::contains` adapter and compiling its generated project after
  relocating it away from the translator repository. This pass propagated the
  selected Stage1 product and runtime through all nested compiler-wrapper calls.
- `scripts/test.sh --suite fixtures --reuse-build` passed: all 21 selected
  native/generated acceptance cases and the core fixture suite passed with no
  crashes, timeouts, or RSS-limit events. The one reported skip is the known
  Stage1 backend decline for executable parity of the compiler-builtin
  `offset-of` expression.

The test driver now resolves repo-relative compiler/runtime overrides before
child scripts change directories and exports the selected Stage1 pair to those
scripts. The fixture-suite translator rebuild peaked at 415,216 KiB
process-group RSS / 419,217 KiB physical footprint. During the C++ map-heavy
cases, the translator itself stayed below 140 MiB RSS; system free memory
remained roughly 49–56%.

This validates the callback path and the listed suites, not full Wolf4SDL
compatibility. SDL declarations, platform ABI details and any remaining
backend-declined constructs in Wolf4SDL still require their own focused
translation/compile/runtime evidence.

## Computed C function-pointer callees — 2026-09-30

Call lowering now accepts computed C function-pointer designators when the
call's scalar arguments require statement preludes. It lowers the callee via
value-plus-prelude lowering, appends any callee effects first, captures the
function value in a generated local, and only then emits argument effects and
the call. The existing plain variable and `(*callback)(...)` path remains
special-cased so its function-pointer type is retained rather than the
dereferenced function type. A non-function-pointer computed callee still
fails closed.

`testdata/fixtures/computed_function_pointer_call.c` covers a function-pointer
record member reached through a side-effecting pointer-to-record factory and
a conditional function-pointer expression. It also checks a comma-effectful
conditional scalar argument on both selected and skipped branches. The
control-flow suite asserts generated callee-before-argument-before-call order;
the native and generated executables both return 0, with exact factory and
argument effect counts. The fixture compiled with the local Stage1 product
and was linked only with that worktree's matching runtime.

The adjacent typedef-return case is now supported as well. C function-pointer
values are emitted as grouped nullable Elisa function values, `(fn(...))?`,
including local captures and function return types; an indirect invocation
emits an explicit non-null assertion after its argument effects. The expanded
`function_pointer_return.c` returns either a callback or `NULL`, immediately
calls the selected callback with a side-effecting argument, and separately
checks the null return. Native and generated executables both return 0, and
the focused suite checks the generated type plus callee/argument/call order.

An initial focused run used `elisac-stage1-rebuild5`; the freshness wrapper
later correctly rejected that product after compiler sources advanced. That
stale-product gate has since been resolved by integrating compiler `main` and
building `rebuild6` from the refreshed isolated worktree. The current compiler
identities and full-suite evidence are recorded immediately below.

## Refreshed Stage1 compiler integration and translator verification — 2026-09-30

The isolated Stage1 compiler worktree now contains compiler `main` through
`3fa4a7e590c3ae5919b759a85dc8f1e105246c8b`. Merge commit
`230dbf03284917c7be7a04695b9753d3769dea93` preserves its branch-local
view-return escape fix while forwarding the newer mainline provenance
arguments. The merge-base audit reports zero mainline commits missing from the
worktree. The pre-existing `.DS_Store` modification was left untouched.

The product was freshly seeded with `-O3` using only the isolated local Stage0
binary (worktree revision `e42bbdfe`, binary SHA-256
`915d12bba8a4c2a89eb826d61d741f952ec3be718cf023b84f51f71ffaf28ba1`). The
seed had a 2.5-GiB RSS guard and completed successfully without a machine-level
crash. The fresh Stage1 product is
`../elisa-transpiler-worktrees/transpiler/bin/elisac-stage1-rebuild6` (SHA-256
`a02ef40490c822d81cfa5c65343d6e6a848b139d27edf8a79d7e375979791958`); its
runtime, built by that product and recorded separately to avoid replacing
older test artifacts, is
`../elisa-transpiler-worktrees/transpiler/build/runtime/elisacore_runtime.rebuild6.o`
(SHA-256
`6a8d933dc5d9e77d491de34225ca21b7a37c117182e1e0e14d3a3e20ff6afc5e`).

The translator was rebuilt from the current `src/` with that explicit Stage1
product and matching runtime. The bounded object build peaked at 364,528 KiB
process-group RSS / 419,905 KiB physical footprint. The executable is
`build/elisa-c-transpiler`, SHA-256
`ee90ddeed7ef2632ebb3d322410d631029d99d790047318afbba8134aff8fd6e`.
Subsequent `--reuse-build` runs confirmed its source/toolchain fingerprint and
binary hash still match.

Verification with the fresh local compiler pair:

- `scripts/test.sh --suite fixtures --reuse-build` passed, including all 21
  selected native/generated acceptance-manifest cases, the compact AST schema,
  Clang type-view and declarator-shape checks, and the complete core fixture
  script. There were zero manifest crashes, timeouts, resource-limit events or
  unsupported cases. The existing, explicitly reported backend skip remains:
  executable parity for the compiler-builtin `offset-of` call expression is
  declined by Stage1.
- `scripts/test.sh --suite control-flow --reuse-build` passed, including
  `function_pointer_return.c`; the callback-return fixture compiles, links and
  matches native execution.
- `scripts/test_short_enum_abi.sh` passed against native C, isolated Stage0 and
  fresh Stage1, covering `u8`, `i8` and `u16` enum storage.
- The `idiomatic_patterns.c` test now matches the intended safety contract:
  pointer reads inside generated `trusted` regions retain explicit generic
  non-null checks because Elisa does not carry the branch-local proof through
  that boundary. The test had incorrectly demanded unchecked `value[0]` even
  though the emitter and plan deliberately preserve the check.
- The const-binding fixture confirms the requested mapping: C `const` objects
  become ordinary immutable Elisa bindings, with no C-style `const` token or
  redundant `mutable` on the binding. Pointer-slot rebinding and pointee
  mutability remain separate capabilities. Its emitted Elisa compiled and ran
  with native C, isolated Stage0 and fresh Stage1; all three returned 0.

This closes the fresh-build and focused-suite prerequisite for V06, not the
whole compiler/corpus gate. Full upstream-corpus compatibility, additional
cross-stage coverage and the remaining backend-declined constructs remain
open; the JSON-handle migration's quantitative large-unit memory comparison
also remains to be recorded.

## Volatile/atomic loop-test rejection and expression diagnostic ranges — 2026-09-30

Loop-condition lowering now fails closed before moving a condition into a
statement prelude when the condition contains a volatile object read or an
atomic access. The check distinguishes the volatile pointer object from its
pointee: reading `pointer` where its type is `volatile int *` remains accepted,
while loading an `int * volatile` object is rejected. It recognizes Clang's
`AtomicExpr`, atomic-qualified types (including typedef desugaring), C atomic
builtin/API call shapes and atomic-typed C++ member-call subtrees. This is a
conservative rejection boundary, not volatile/atomic lowering support.

The first focused run exposed that compact AST projection discarded expression
ranges, turning a real unsupported-loop diagnostic into the unknown `0:0`
location. Projection version 2 retains `loc`/`range` data for expression nodes;
the validator now accepts that version. Four isolated negative fixtures cover
a volatile scalar `while`, a typedef'd `_Atomic` `for`, `__atomic_load_n` in a
`do-while`, and a volatile pointer slot. Each requires exactly one diagnostic
at the loop-test source line and zero generated stdout. The pointer-to-volatile
control case appears before the first rejection and therefore also verifies it
is not falsely diagnosed.

Validation used the isolated local Stage1 product
`elisac-stage1-rebuild5` (SHA-256
`53e1caa10cf289830c34e7a7960b4ae1884b3c9d29debc798db49d0ebaa9f20d`) with its
matching runtime object (SHA-256
`6a8d933dc5d9e77d491de34225ca21b7a37c117182e1e0e14d3a3e20ff6afc5e`). The
translator build peaked at 554,560 KiB RSS and 530,993 KiB physical footprint.
`sh scripts/test.sh --suite control-flow` passed, then the full acceptance
manifest passed 22/22 cases across 132 stages with no timeout, crash, resource
limit, monitor error, skip or missing tool. The maximum stage sample was
63,728 KiB RSS / 3,937 KiB physical footprint; maximum combined output was
16,089 bytes. The manifest outputs and measurements are preserved under
`build/manifest-tests-2026-09-30-expression-ranges-v2/`.

The same fresh control-flow run also passed the fail-closed conditional-value
regressions: nested conditional-arm comma effects, a discarded volatile comma
operand, record-valued conditional materialization, effectful aggregate call
arguments and a C++ conditional glvalue all reject without generated stdout
and retain the source path in their diagnostics. The manifest's
`short_circuit_constant` case still compiles, links and matches native runtime
behavior, so the unsupported-context checks did not disable decisive
short-circuit pruning.

The default isolated Stage0 binary did not parse the current translator source
(`expected else, got IDENT("can")`) and stopped at 92,896 KiB RSS; no source
output was emitted. The passing run explicitly selected the local Stage1
product/runtime above. Its known compiler-source freshness limitation and
separate wide-integer backend issue remain documented below; these results
establish translator behavior with this exact local binary, not a refreshed
Stage1 compiler build or C++ `std::atomic` acceptance.

## Per-stage fixture resource limits and bounded output capture — 2026-09-30

The manifest runner now applies the configured aggregate process-group RSS
limit independently to every translate, native-build, Elisa-compile/link and
execution stage. This closes a test-harness blind spot: wrapping the manifest
coordinator did not include its detached child sessions in the coordinator's
RSS sample. Child stdout/stderr are spooled directly to stage files rather
than accumulated by `communicate()` in the coordinator, and a per-stage
combined-output limit (default 64 MiB, configurable with
`ELISA_FIXTURE_PROCESS_MAX_OUTPUT_BYTES`) bounds the subsequent in-memory
checks/comparisons as well. macOS physical-footprint sampling uses the same
owned process group; monitor failures are a distinct failing outcome, and only
the owned stage group is terminated and reaped on a limit breach.

`scripts/test_fixture_manifest.py` includes deterministic regressions for two
failure boundaries: it makes a child finish between the process-list and
footprint samples and verifies ordinary completion, and it makes a child
exceed a small output cap and verifies resource-limit classification. All 15
fixture-runner tests passed, as did all 6 shared bounded-process tests. The
full 21-case acceptance manifest then passed serially using
`--max-rss-kb 1572864`, `--max-output-bytes 67108864` and a 120-second
per-stage deadline: all 126 owned stages passed, with no timeout, crash, cap
hit, monitor error, skip or missing tool. The maximum sampled stage-group RSS
was 77,248 KiB and the largest combined stage output was 16,089 bytes. This is
bounded acceptance-corpus evidence, not proof that every long-running corpus,
arbitrary Clang invocation or concurrent whole-system workload fits the same
budget.

Run artifacts and per-stage measurements are under
`build/manifest-tests-2026-09-30-bounded-output-cap-final/`; the summary reports
21/21 passes. The known Stage1 wide-integer literal backend trap remains
outside this manifest and is not claimed fixed by this result.

## C declaration-group mutability and upstream smoke corpus — 2026-09-30

Clang can place multiple C declarators such as `int i, prev_sep, in_string;`
inside one `DeclStmt`. The translator had represented that grouping wrapper as
a lexical scope, so write analysis forgot the bindings before later sibling
statements; Kilo consequently emitted reassigned locals as immutable. The
typed IR now marks only these generated wrappers as C declaration groups,
keeps them scope-transparent in write analysis and Elisa name emission, and
validates that the marker contains at least two declaration children. Empty
filtered declaration statements remain ordinary empty blocks. The write scan
also continues through a non-matching assignment so independent and nested
targets in comma/post-increment expressions are all discovered.

`multi_declarator_mutability.c` checks mutable versus unchanged sibling locals,
a nested shadowing block, and two variables introduced by a multi-declarator
`for` initializer. The `control-flow` suite compiled and linked it; both native
and generated executables returned 0. The full scripted `upstream` suite then
passed: inih translation/compile/link and sample, no-argument, and missing-file
output/status parity; cJSON translation, structural checks, compile/link and
smoke-output parity (the nullable-function capability probe succeeded); and
Kilo translation, compile/link and no-argument exit/output/diagnostic parity.
This Kilo check does not exercise interactive editing/gameplay, and Wolf4SDL is
not part of this smoke suite.

The final translator artifact was rebuilt with the explicitly selected local
Stage1 product/runtime pair under the 1.5-GiB process-group cap:
translator SHA-256
`4b9c3a1707221575f8cb24d604f04dfc99b1646ef6c3afbd1ae6e2b11afba961`, build
input fingerprint `e9e76a8b19390c8b06b61378a8c384fc2e3508943d854922167c07d1fc8faca4`,
Stage1 SHA-256
`53e1caa10cf289830c34e7a7960b4ae1884b3c9d29debc798db49d0ebaa9f20d`, and
matching runtime SHA-256
`6a8d933dc5d9e77d491de34225ca21b7a37c117182e1e0e14d3a3e20ff6afc5e`.
The selected Stage1 executable predates the source-level wide-integer literal
fix documented below; these successful translator/corpus checks therefore do
not claim that compiler fix has been seeded into a fresh Stage1 binary.

## Wide integer match literals and refreshed compiler trap — 2026-09-30

The latest isolated Stage1 binary (`elisac-stage1-rebuild5`) trapped while
lowering the translator's valid `u64`-maximum switch arm. Its macOS crash report
identified `Backend.parse_int_literal`: the helper accumulated decimal digits
in checked `i64`, so `18446744073709551615` trapped before LLVM emission. The
same implementation also negated `i64.min`, another checked-overflow trap.

The compiler worktree now parses the magnitude in `u64`, checks each decimal
step against `u64.max` before multiplying, preserves positive `u64` bit patterns
when returning the backend's `i64` representation, and constructs `i64.min`
without negating it. Two backend behavior regressions cover `u64.max` and
`i64.min`. The updated backend emitter was built by the isolated refreshed
Stage0 compiler; both cases compiled to LLVM/object, linked, and returned 42
(combined probe returned 84). The exact direct `i64.min` initializer also
passed.

A full new Stage1 seed was attempted to a separate `rebuild6` path. The
bounded-process guard stopped the owned seed at about 2.31 GiB aggregate
physical footprint (below its 3 GiB RSS setting); no rebuild6 product or
runtime was published, and the owned process group exited. This is a build
resource stop, not a compiler verdict. The previously built Stage1 binary
still contains the old parser and must not be used to claim this regression is
fixed there. Rebuilding a matched product/runtime pair and rerunning the
translator fixture suite remains open under V06/V05.

## Nested `char **` read preserves nullable layers — 2026-09-30

The `char **` nested-character-index shortcut emitted `elisa_nonnull(text)[0][0]`
for the C expression `(*text)[0]`. That flattened two distinct operations:
loading the nullable `char *` from the pointer slot, then reading a character
through that pointer. Stage1 consequently loaded the character from the address
of the pointer slot. The nested-index emitter now emits
`elisa_nonnull(elisa_nonnull(text)[0])[0]`, retaining a generic checked
conversion at both nullable C pointer layers. This is general pointer lowering;
there is no cJSON-specific case.

The core fixture asserts the new emitted shape. With the isolated Stage1
compiler/runtime pair, `generic_nonnull.c` translated, compiled and linked;
both the native and generated executables exited 0. The full fixture suite
passed its 21-case acceptance manifest on its first run and reached an existing
stale `cpp_reference_cursor` type assertion; that assertion was updated to the
emitted layered type. On subsequent full-suite attempts, all manifest cases
except one passed, but different inputs intermittently failed during Clang
translation with only the generic “Clang failed while processing” diagnostic;
direct reruns of those exact inputs succeeded. Other large Elisa compiler
builds were active and system memory pressure was high, so this is recorded as
an incomplete suite run, not attributed to the source fix or counted green.
The broader core suite has not completed after the assertion update. A direct
compile of the cursor fixture with the previously built Stage1 product then
failed with `view "ptr" cannot be used: storage dependency facts were
invalidated by darray push of ptr`; the emitted signature is now checked
accurately, but this C++ reference-to-pointer case remains unverified at
runtime.

## Isolated Stage1 source refresh and guarded seed attempts — 2026-09-30

The isolated Stage1 compiler worktree was four commits behind the compiler's
main worktree. It was fast-forwarded from `98261837ddc8ba0596c3bf9b0c5906475bf289b7`
to `54360bf68398b4da8d63b82a3ad2979667798aa2`, then updated with the main
worktree's inspected, uncommitted compiler fixes and their focused regressions.
The main checkout was left untouched; pre-existing Stage1-worktree edits were
preserved. The changes include reference-to-darray field lowering, fixed-array
spreads, UFCS fallback, local-container escape diagnostics and related tests.

Rebuilding the product/runtime pair from the dedicated Stage0 worktree was
attempted with the compiler's seed lock and RSS guard. Stage0 `-O3` exceeded a
3-GiB limit (observed peak 3,235,360 KiB); `-O1` exceeded 2.5 GiB (2,630,608
KiB); and `-O0` exceeded 2.5 GiB (2,679,008 KiB). Each run was stopped by the
guard, and the seed script cleaned its temporary outputs and locks; the old
product/runtime pair remains intact and was not overwritten. Consequently the
`generic_nonnull.c` native/generated parity result above used the previously
built isolated Stage1 product (SHA-256
`df31f9d00a8a3ffbb61302d02d05e00a7cc5eb23e7f03d36bb6fb0cedad4e369`) and its
matching runtime, not a binary built from the newly refreshed source. The
latest compiler source is now present in the worktree, but fresh Stage1 runtime
verification remains pending a build strategy/resource window below those
guarded peaks.

## Pointer-to-array element pointer layer — 2026-09-30

When decomposing a C++ pointer-to-array spelling, the terminal element type
was rendered through the generic type path rather than the array-element path.
For `objtype *(*rows)[4]`, that dropped the element pointer's writable and
nullable layer. Both contextual and fallback pointer-to-array renderers now
delegate the leaf to their ordinary array-element renderer. The fixture
asserts `take_rows(rows: mutable array[mutable Objstruct&?, 4]&?)`, preserving
the nullable pointer stored in each row as well as the outer row pointer.

The translator rebuilt with the isolated Stage1 compiler at
`98261837ddc8ba0596c3bf9b0c5906475bf289b7` (binary SHA-256
`df31f9d00a8a3ffbb61302d02d05e00a7cc5eb23e7f03d36bb6fb0cedad4e369`) and its
matching runtime (SHA-256
`741c2f6efd433ab6d92c7cadf275c8ceb92b3301eaf48a03a3f0cd89e0a1bd99`). The
guarded translator build peaked at 365,744 KiB RSS. The manifest passed 21/21;
the core fixture script stopped earlier at `generic_nonnull` because native
returned 0 while generated returned 1, before reaching the pointer-array
section. Running `pointer_array_decay.cpp` directly, then compiling/linking
its generated Elisa with the matching Stage1/runtime, produced native and
generated exit 0. The older local Stage0 could not rebuild this current source:
it rejected existing `can` syntax in `src/clang_ast_filter.elisa:191`; no
pointer-array test was run with that compiler. Other pointer-to-array
qualifier combinations remain open under F04.

## Projection schema boundary and C++ map-iterator regression — 2026-09-30

Clang projection's declaration-kind classification, declaration-location
retention rules and macro-origin detection now live in
`src/clang_ast_projection_schema.elisa`, included before the recursive
projector in `src/main.elisa`. This is a deliberately narrow, one-way frontend
boundary, not completion of the broader module-interface work. The projector
fell from 599 to 553 lines; the new schema module is 45 lines. The source-line
gate and `git diff --check` pass.

The first fixture run then caught a regression in the existing C++17
`unordered_map::find` adapter: generic template rejection ran on the inferred
`std::unordered_map<K,V>::iterator` local before the scanner recognized its
initializer. The scanner now resolves the initializer first and exempts only
the structurally verified `unordered_map::find` result; other unmodeled
template-valued locals still fail closed. The fixture emits the adapter
iterator type and expected `end`, `first`, `second` and `set_second` calls.
Native C++ and Stage1-generated Elisa both compiled and exited 0. The
translated fixture process peaked at 98,208 KiB RSS; its Stage1 compile/link
process peaked at 115,424 KiB RSS.

Verification used the isolated Stage1 compiler at commit
`98261837ddc8ba0596c3bf9b0c5906475bf289b7` (SHA-256
`1eb3c109d5a56669826ccfb77cd5c5df03ccec20bdb49aa17077c14dc5040fc6`) and its
matching runtime (SHA-256
`741c2f6efd433ab6d92c7cadf275c8ceb92b3301eaf48a03a3f0cd89e0a1bd99`). The
translator rebuilt from current source under a 1 GiB process-group RSS cap;
the build peaked at 414,400 KiB RSS / 391,681 KiB sampled physical footprint.
The fixture runner's support, frontend, AST-depth, metamorphic and declaration
closure checks passed, as did all 21 manifest cases and the compact projection
schema checks. A stale standalone typed-IR test initializer was updated for
the existing `specialized_types` field and passed on rerun. The full fixtures
suite is not yet claimed green: its long C++ adapter tail surfaced the
`unordered_map::find` regression, which was verified directly after the fix;
the suite has not yet been rerun end-to-end after that fix. The existing
Stage1 `__builtin_offsetof` backend capability skip remains distinct from a
translator mismatch.

## Region-bound Clang type view — 2026-09-30

Added `ClangTypeView` as a frontend type boundary with three independent,
region-bound facts: source `qualType`, Clang's optional `desugaredQualType`,
and `typeAliasDeclId`. `ast_qual_type` now reads the source spelling, C ABI
type selection reads the desugared form when available (preserving the
`va_list` special case), and typedef record-layout/dependency lookup reads the
alias declaration ID through the same view. This prevents consumers from
mistaking a source alias spelling, an ABI spelling and declaration identity
for one interchangeable string; it is not yet a recursive structural type
graph or a full target ABI model.

`testdata/clang_type_view_test.elisa` checks that all three Clang values remain
distinct and that absent optional fields are empty. It was compiled and run
with the isolated Stage1 compiler/runtime. `typedef_identity.cpp`,
`pointer_qualifier_layers.c` and `anonymous_typedef_include.c` were each
translated by the rebuilt translator, compiled natively and as Elisa with
Stage1, then both executables returned 0. The translator build used Stage1 at
`98261837ddc8ba0596c3bf9b0c5906475bf289b7` and peaked at 422,608 KiB RSS under
the 1 GiB process-group cap (object SHA-256
`c25e2baba8b2dc828c05727e6d4c3b805a16d2389cb6ed650ec45558aa41dabe`, executable
SHA-256 `65724e72e9dff0e5de4481f52cfabb1f9afe5e56607030fec91daedb68727dc0`).
The sensitive `cpp_unordered_map_find.cpp` output is byte-identical to the
pre-migration translation and its Stage1-generated executable also passes.
The focused type-view check passed; the full fixtures suite has not yet been
rerun after this frontend API migration.

## Versioned compact AST projection — 2026-09-29

The translator-owned compact AST root now carries
`elisaProjectionVersion: 2`. `translate_ast_mode_with_options` validates that
marker before declaration indexing or lowering and fails closed for a missing,
non-numeric, or unsupported version. Raw Clang JSON remains validated by the
separate pre-projection root contract; Clang is neither expected to emit nor
allowed to define the translator projection version. Version 2 describes the
current compact `TranslationUnitDecl` envelope and the dependency markers
added by projection. This is an internal schema boundary, not yet a complete
semantic fact model: canonical declaration/type identity, semantic facts not
available in JSON, and cross-version Clang schema compatibility remain open.

Fresh verification used the isolated Stage1 worktree at compiler commit
`98261837ddc8ba0596c3bf9b0c5906475bf289b7` (no Elisa source file newer than
its product), executable SHA-256
`1eb3c109d5a56669826ccfb77cd5c5df03ccec20bdb49aa17077c14dc5040fc6`, and
matching runtime SHA-256
`741c2f6efd433ab6d92c7cadf275c8ceb92b3301eaf48a03a3f0cd89e0a1bd99`.
Translator object/executable SHA-256 values are
`de3568f0a047cf97034e3c70c255d610a1bd765aec8203550dd52b821c82d8b3` /
`5e35f6db0dab6436bdbdfef082f149e7d35d3669daa171f4dcd47fb540622222`.

The translator was rebuilt from current source with that Stage1 executable
under the bounded runner (peak 293,904 KiB process-group RSS / 383,377 KiB
sampled physical footprint). A real-Clang `simple.c` translation produced
77,311 raw JSON bytes, 5,516 projected bytes, 40,208 parsed-arena bytes and
387 projected JSON values; generated Elisa compiled/linked against the matching
runtime and matched native C at exit 42. `scripts/test_clang_failure.sh`, the
transitive C declaration-closure fixture, and the unqualified C++ record-layout
fixture also passed; the latter two each compiled, linked and matched native
execution. `testdata/ast_projection_schema_test.elisa` compiles with Stage1,
links against its matching runtime and checks v1 acceptance plus rejection of a
missing marker, a string-valued marker, a fractional version, and unsupported
integer version 2. It also rejects duplicate projection-version keys rather
than allowing JSON member lookup order to decide which version wins.

## External inline definition dependency — 2026-09-29

Added `scripts/test_inline_dependency_closure.py` to cover an AST relationship
not exercised by the existing direct-reference test. Its real C fixture puts a
`static inline` prototype and body in separate headers outside the source
directory, redirects the source call's `DeclRefExpr.referencedDecl` to the
prototype ID, assigns both declarations synthetic external paths, and removes
their `isUsed` flags. This forces the projector to follow the symmetric
`previousDecl` canonical-redeclaration edge to the body-bearing definition;
the test asserts that definition and `main` are emitted, then compiles/links
generated Elisa and compares execution with native Clang (both exit 0).

The regression passes with the fresh translator and isolated Stage1 compiler at
`98261837ddc8ba0596c3bf9b0c5906475bf289b7`, linked against its matching
runtime. This closes only the observed external C inline redeclaration shape;
qualified record identity, C++ member/template definitions, template
specializations and other Clang schemas remain open.

## Project-table lifetime crash — 2026-09-29

The two-translation-unit cJSON project crash is fixed. The saved macOS report
for PID 91662 identifies the crashing frame as
`CTranslator.typed_project_function_has_arity`; symbolication against the
matching executable UUID and disassembly show the fault while loading a row
from `translator_project_state.functions`. The table header was global, but
its dynamically grown backing arrays were populated with ordinary `push`
inside `region source_translation`. Destroying the first unit's region freed
those buffers while the global table still retained their pointers.

All eight project-table insertion sites now use Elisa's `arena_da_append` with
one explicit `translator_project_arena`. The copied names/signatures already
use `string_view_copy`, which stores them in `perm_arena`; both the row arrays
and their string data therefore outlive each per-unit AST/lowering region. The
per-unit regions remain in place, so this fix does not keep complete ASTs alive
across a project. An initial attempt to reserve the global darrays in the
outer inferred region was rejected by the current Stage1 lifetime checker and
was discarded in favor of explicit arena ownership.

Validation with the freshly built translator and its matching Stage1 runtime:

- The three-input `module_a.c` / `module_b.c` / `other.module_a.c` project
  translates successfully. `module_b` calls `add_one` registered by the
  earlier unit; the generated project compiles and runs with exit 0, matching
  native C.
- The full two-source cJSON project now emits `cJSON.elisa` (1,661 lines),
  `cJSON_Utils.elisa` (1,074 lines), and `elisa_project.elisa`; the command
  completed under a 1.5-GiB process-group cap at 649,728 KiB peak RSS and
  804,962 KiB sampled physical footprint. One earlier run stopped cleanly at
  the 1-GiB cap's safety threshold (730,464 KiB RSS / 753,361 KiB footprint);
  the owned process group was terminated by the runner, not by a crash.
- The four-unit external-object project also translates in both compile-database
  orders. Its generated manifests are byte-identical; both generated projects
  compile against the same local Stage1 compiler/runtime and run with exit 0,
  matching native C. This exercises persistent function, global, extern and
  record-field lookup across multiple reclaimed translation-unit regions.
- `python3 -m unittest scripts.test_run_bounded_process` passed all six tests.
  During the first complete `--suite projects` attempt, the bounded-process
  RSS regression asserted specifically on the RSS diagnostic even though
  macOS correctly tripped the physical-footprint guard first; the assertion
  now accepts either configured safety guard. On the corrected rerun, the
  suite later stopped at Clang target-macro acquisition for
  `project_external_objects/main.c`; immediate standalone reruns of both
  compile-database orders succeeded, and both outputs compiled and ran as
  described above. Thus the focused lifetime evidence is green, while a clean
  full project-suite result is still pending.
- This closes the translator's project-mode SIGSEGV, not cJSON's backend gate.
  Compiling the large emitted cJSON Elisa with the exact local Stage1 product
  still fails at LLVM verification with `backend generated invalid LLVM IR`;
  full generated/native runtime parity remains open. The capped run left one
  unreferenced staged cJSON temp file in `build/cjson-project-lifetime-regression/`.

## Current cJSON provenance investigation — 2026-09-29

- The anonymous-typedef-through-included-implementation fixture now checks
  that complete record layouts (`parse_buffer` and `parse_error`) survive AST
  projection, while `scripts/test_transitive_decl_closure.py` guards against
  retaining unrelated external declarations. That closure test passed against
  the current working-tree translator binary.
- A fresh translation of the then-current
  `testdata/fixtures/anonymous_typedef_include.c`
  completed under a 256-MiB process-group cap and emitted both full anonymous
  typedef layouts. Frontend stats: raw AST 244,230 bytes, projected AST
  45,226 bytes, parsed arena 222,720 bytes, 2,245 projected JSON values. This
  generated output compiled with
  `../elisa-transpiler-worktrees/transpiler/bin/elisac-stage1 -emit obj -O0`,
  linked with that worktree's `elisacore_runtime.o`, and exited 0. Native C
  compiled with Clang and also exited 0. The source was manually translated,
  compiled and compared; the full fixture suite was not rerun.
- The fixture was extended with an unreachable included helper that calls
  `anonymous_unused_dependency`. The pre-fix translator emitted that unrelated
  function. A fresh rebuild with only the range-offset provenance guard still
  emitted it, exposing a second retention path: Clang's translation-unit-wide
  `isUsed` hint can be true because of a reference inside an otherwise
  unretained included body. The current working tree keeps offset-only nested
  nodes in included-file provenance and restricts the `isUsed` fallback to
  source-owned declarations. A fresh rebuild with both fixes translated the
  updated fixture, retained both complete anonymous typedef layouts, and
  omitted both `anonymous_unused_dependency` and `unused_include_helper`.
  Frontend stats were raw AST 259,142 bytes, projected AST 45,226 bytes,
  parsed arena 222,720 bytes, and 2,245 projected JSON values. Generated Elisa
  compiled with the isolated Stage1 compiler, linked with its matching
  runtime, and exited 0; native C also exited 0. This is focused fixture
  evidence, not a full-suite run.
- The cJSON smoke translation has not passed on the current working-tree
  revision. The high-memory probes below predate the latest included-source
  retention fixes and must be repeated against the rebuilt translator. A
  bounded standalone Clang JSON AST dump returned success, but its
  short runtime made the sampler's reported peak unreliable. In the actual
  translation command, the monitored process group (translator plus its Clang
  child) exceeded a 1.5-GiB aggregate RSS cap in approximately eight seconds
  and emitted no new translation. The existing
  `build/cjson.generated.elisa` is an older artifact and still contains opaque
  layouts; it is not valid evidence for this revision.
- A pre-fix diagnostic run used a 512-MiB cap and a 50-ms poll interval. It
  terminated in roughly four seconds after a sampled aggregate 563,488 KiB;
  the live process breakdown showed only `elisa-c-transpiler` (574,496 KiB)
  and no Clang child. The owned process group was reaped and no output was
  retained. This localizes the growth to translator-side projection/parsing/
  lowering, but does not distinguish those phases. The sample also showed the
  polling guard can overshoot its configured cap during rapid RSS growth.
- The runner now stops at `cap - min(cap / 8, 64 MiB)` to reserve reaction
  headroom between RSS polls; its four tests pass, including the threshold and
  per-process diagnostics. A second pre-fix probe used a 200,000-value JSON
  preflight limit, a 512-MiB configured cap and a 50-ms poll interval. It reached the
  458,752-KiB safety threshold at a 480,672-KiB group sample; the only live
  process was `elisa-c-transpiler` at 503,376 KiB. It did not reach the JSON
  value preflight or print frontend stats, consistent with the peak being in
  projection rather than DOM parsing/lowering. This is not a successful cJSON
  translation and does not measure the latest retention fixes.
- No broad suite is claimed for the current provenance changes. The translator
  has since been freshly rebuilt with the isolated latest Stage1 compiler and
  the focused positive/negative fixture passed, but full cJSON and broad-suite
  checks remain pending. It is not yet known whether Clang's AST
  generation, the translator's projection pass, or Elisa AST construction
  accounts for the peak. `scripts/run_bounded_process.py` now prints the live
  RSS of each owned process when the aggregate cap is reached. All four
  focused tests passed with assertions for member-level RSS, and a deliberately
  low-cap smoke confirmed the output and clean termination. The RSS test's
  committed allocation was reduced from 96 MiB to 24 MiB. The next cJSON run
  must be repeated against the rebuilt translator before phase-specific changes
  are made.
- A previous full-fixture pass recorded below predates these current cJSON
  provenance changes; do not interpret it as validation of this revision.

## Latest compiler and translator verification — 2026-09-29

- The isolated Stage0 compiler worktree is at
  `../elisa-transpiler-worktrees/stage0-latest/compiler`, revision
  `e42bbdfe8a1b8123c3c4bfd096d64eb4c97c8b11`. The isolated Stage1 compiler
  source worktree is at `../elisa-transpiler-worktrees/transpiler`, HEAD
  `98261837ddc8ba0596c3bf9b0c5906475bf289b7`. Its source includes the latest
  parser/semantic changes synced from the main compiler checkout, while
  preserving the worktree's local nullable-reference backend fix. The source
  files modified or added under `src/` and `elisacore_std/` in the main compiler
  checkout were byte-identical in this isolated worktree at this verification.
  The source
  worktree also contains an uncommitted generic export-alias correction: only
  annotation rows paired with an explicit `__export_global` marker can create
  LLVM aliases. This prevents LSP declaration-name metadata from colliding
  with symbols in programs linked against the runtime.
- Stage1 was freshly seeded from the isolated Stage0 compiler with
  `ELISA_STAGE1_SEED_MAX_RSS_KB=4194304`; the seed and matching runtime build
  completed successfully, and `scripts/assert_stage1_fresh.sh` passed.
  Stage1 executable SHA-256:
  `1eb3c109d5a56669826ccfb77cd5c5df03ccec20bdb49aa17077c14dc5040fc6`.
  Matching runtime object SHA-256:
  `741c2f6efd433ab6d92c7cadf275c8ceb92b3301eaf48a03a3f0cd89e0a1bd99`.
- The focused `test/parity/export_global_metadata_link_smoke.sh` compiled,
  linked, and ran a global-variable probe against that exact Stage1 runtime;
  it exited with the expected value and emitted no duplicate symbols. The same
  probe confirmed an explicit `export global ... as ...` alias is still present
  in the object file.
- `sh scripts/test.sh --suite fixtures --reuse-build` passed with both
  `ELISAC_BIN` and `ELISA_STAGE1_BIN` set to that local Stage1 executable and
  both runtime overrides set to its matching runtime object. The translator
  rebuilt because the compiler fingerprint changed. All 19 acceptance-manifest
  cases passed, followed by the core fixture checks, including unordered-map
  translation/runtime parity and cJSON quality checks. The harness reported
  one capability skip for executable parity of `compiler_builtins`, because
  this Stage1 backend declines an `offsetof` call expression; the suite itself
  exited successfully. System monitoring observed no memory-throttled pages
  during the compiler seed or fixture run.
- The tested translator executable at `build/elisa-c-transpiler` has SHA-256
  `7da83bf118cab241d49c4618b546b754defd064dff9e93869eb02f0977928d3f`.
- These compiler fixes remain uncommitted in the isolated Stage1 worktree;
  this record does not claim they have been merged into the compiler's main
  checkout. This entry supersedes earlier historical notes that the refreshed
  Stage1 product was stale or that the full fixtures run had not completed.

## Bounded translator checks — 2026-09-16

- The local stage0 compiler used for the current translator binary is the
  isolated `../elisa-transpiler-worktrees/stage0-latest` worktree at
  `3a5520d8fd56b86c430f39518a261e9030fa72ec`, executable SHA-256
  `975b1e8e1283abdf5068447d10fc1625d6e2eb59c8313af28e7b57866f39710f`.
- `build/elisa-c-transpiler` has SHA-256
  `4628fc2dbde2784e39eedd692775f994d5266a2c5eef429bc260ddf1157992ed`.
- The diagnostics JSON smoke passed: an unsupported conditional/comma
  fixture returned exit 1, emitted no stdout, and produced four valid JSON
  records on stderr with source/canonical identity and origin fields. A zero
  line/column is retained as the explicit unknown-coordinate sentinel for
  synthesized diagnostics.
- The deterministic metamorphic smoke passed: renaming source identifiers in
  a small equivalent C program produced byte-identical Elisa after reversing
  the known renames; a truncated C source failed with no partial output.
- The full fixtures suite was not used as evidence for this slice: one
  in-progress run was intentionally terminated after the bounded manifest
  checks when it reached the known CPU-heavy unordered-map negative corpus
  section. The direct diagnostics and metamorphic checks above completed
  independently.

## Environment snapshot — 2026-09-14

- Translator repository: current branch `work`; the checked-out implementation
  has substantial pre-existing unstaged and untracked work. Results
  below describe that working tree, not a clean checkout of `HEAD`.
- Local Elisa stage0 compiler: `../elisa-transpiler-worktrees/stage0`, revision
  `5284109c`; its worktree is clean at this verification.
- Local compiler executable SHA-256:
  `feaaface1f45bd817abf09a2e28e86e0c06da6f6fe322065152735de17f0dab5`.
- Latest focused translator build input fingerprint:
  `640850d53e6d2cd59f6d04a264c313b8fdb13db169976001cc836989a7b2a12b`;
  built translator SHA-256:
  `33bb90fd6b508db120dd2e696946627b7d003fdb63670398f052d9dd5dae7c5d`.
- Local Elisa stage1 compiler: `../elisa-transpiler-worktrees/transpiler`,
  revision `7fa91fef`; its worktree has uncommitted generic `Index` type-
  inference changes in `src/backend/codegen_expression_type*.elisa`, generic
  UFCS receiver validation and hidden store/arena ABI fixes in
  `src/backend/codegen_generic_call.elisa`, and focused compiler regressions.
  It was rebuilt from that source with the isolated stage0 compiler under the
  seed script's 4 GiB RSS guard. The generic-index and generic-dictionary-field
  smokes passed; fresh translator `projects` and `fixtures` suites also passed
  with this compiler.
  Executable SHA-256:
  `a9da2af1356ccc9154422dc528bef1ce2fc9231b235f8f6f013c6cee18457d9f`.
- Stage1 runtime object: `../elisa-transpiler-worktrees/transpiler/build/runtime/elisacore_runtime.o`.
  SHA-256: `4876d2943cc9b2999a812c9cabab34366cfee81866d125f3250651bd3739ea96`.
- Compiler build command: `elisac-local -emit obj -O0` over
  `src/main.elisa`; object linked with Clang and the stage0 worktree's
  `compiler/runtime/profile_hooks.c` fallback.
- Clang: Homebrew Clang 23.1.1, target `arm64-apple-darwin25.6.0`.
- Host: Darwin arm64.

## Compiler refresh audit — 2026-09-14

The preceding environment snapshot and test records describe the stage1 product
at `7fa91fef`; they are historical evidence, not evidence for the refreshed
stage1 source. The isolated compiler worktrees were checked again:

- Stage0 remains at `5284109ca5805560a488c3b0a5d8cd4a1a45e317`; its local
  executable hash remains the one recorded above.
- The isolated stage1 source worktree was fast-forwarded to
  `fd2cb3cff470319500db362e5fce2833cbe300de`, matching the fetched
  `Elisa-compiler` `origin/main`. This includes the recent scratch-capacity and
  allocation-routing changes, lexer token-buffer ownership/copy reduction,
  and related lifetime/performance work. The translator-local generic `Index`,
  dictionary-field and UFCS hidden-store fixes and their four repro/smoke files
  were preserved. One local `call_site_arena` call was adapted to the current
  four-argument API.
- The refreshed source compiled `src/driver/elisac.elisa` to
  `build/latest-compiler-refresh/elisac_stage1.o` using the main worktree's
  stage1 product (`Elisa-compiler/bin/elisac-stage1`, SHA-256
  `eebb4f562b8128ceedf4761225fd106335978c0a495c44754ec269da5fec1884`), with
  the 4 GiB process guard. The matching runtime object also built. The linked
  candidate (`build/latest-compiler-refresh/elisac-stage1`, SHA-256
  `8bea346daeebfc79cff4b06a26069456d5f5128ba7138e271781b94f53a420c4`) is not
  accepted as a product: macOS remained in dyld before application entry for
  both a compile smoke and `--version`. Only the owned smoke processes were
  stopped. The candidate was not published over the existing isolated binary.
- Consequently the isolated `bin/elisac-stage1` is still the old product
  (SHA-256 `a9da2af1356ccc9154422dc528bef1ce2fc9231b235f8f6f013c6cee18457d9f`)
  and is stale relative to the refreshed source. Its wrapper freshness guard
  must not be bypassed for translator acceptance tests. The earlier passing
  stage1 tests above do not establish compatibility with `fd2cb3cf`; a working
  local product and its project/corpus gates remain open under V06.

### Latest upstream product smoke — 2026-09-14

- A live `origin/main` query confirmed the upstream tip is still
  `fd2cb3cff470319500db362e5fce2833cbe300de`. Its recent optimization commits
  include scratch-buffer reuse/capacity work (`d1fce335`), allocation routing
  and parser-token scratch separation (`33503d21`), and returning completed
  lexer token buffers without copying (`c7c849c7`). The product used below is
  `../Elisa-compiler/bin/elisac-stage1` (SHA-256
  `eebb4f562b8128ceedf4761225fd106335978c0a495c44754ec269da5fec1884`) with
  its matching runtime (SHA-256
  `a58618f5358e30e8c19cf1344d47bddd3a7520ee61f83a471222bb0660e48a8f`).
  Since those translator checks, the compiler worktree has acquired
  uncommitted CoreIR/EDIR backend changes under `src/backend`, `src/ir`, and
  `src/driver/emit_edir.elisa`; those changes are not in the tested product.
  They were left untouched. A separate compiler build was active at roughly
  3.2 GiB RSS with significant swap activity, so no competing self-host build
  was started. The translator results in this ledger are specifically for the
  latest committed upstream product, not the uncommitted compiler experiment.
- The main checkout's product compiler (`../Elisa-compiler/bin/elisac-stage1`,
  SHA-256 `eebb4f562b8128ceedf4761225fd106335978c0a495c44754ec269da5fec1884`)
  passed its source-freshness check and compiled the existing small generated
  Elisa program `build/simple.old.elisa` to an object under a 1 GiB RSS limit.
  This confirms the current upstream product is runnable for basic compiler
  checks; it does not qualify the separately linked candidate built from the
  translator-local stage1 source.
- Follow-up verification now used that same current upstream product to compile
  the complete `src/main.elisa` translator to an object under a 1 GiB RSS cap
  with no diagnostics or backend declines. The main compiler checkout was at
  `fd2cb3cff470319500db362e5fce2833cbe300de`; it has since acquired the
  uncommitted backend changes noted above. The matching stage1 runtime object
  has SHA-256 `a58618f5358e30e8c19cf1344d47bddd3a7520ee61f83a471222bb0660e48a8f`.
  The translator object was linked with that runtime and the stage0 profile-hook
  fallback (object SHA-256
  `3dbc1a38d77f17035c62e041853ba47660c2276ea0cb788f996b608b8cb2b94e`,
  executable SHA-256
  `2338f5afa70769379680a00bf87506ba8e0cbd1af1a0cf3d888eefea73712787`).
  Its escaped-source-path end-to-end test translated a C file beneath a path
  containing a quote, backslash and UTF-8; the generated Elisa compiled with
  the same upstream product and matched native C's exit code 42. A first
  cold launch spent over 20 seconds in dyld; later absolute and relative
  launches both started normally, so this was not reproducible as a path bug.
- The upstream product declined
  `testdata/backend_index_overload_field.elisa`, which exercises translator-
  local generic `Index` fixes not present in upstream `main`. Those focused
  compiler-patch tests still require the patched local compiler; the complete
  translator itself builds and passes the bounded path-parity check with
  upstream main. Do not use the stale isolated stage1 binary for tests that
  specifically require the local generic compiler patches; the refreshed
  local candidate still needs its pre-main dyld startup failure resolved
  before it can validate them.
- A fresh manifest smoke used the same live-upstream product and matching
  runtime: `simple` translated, compiled, linked and matched native C with exit
  code 42. The exact compiler was
  `../Elisa-compiler/bin/elisac-stage1` at `fd2cb3cff470319500db362e5fce2833cbe300de`
  (SHA-256 `eebb4f562b8128ceedf4761225fd106335978c0a495c44754ec269da5fec1884`);
  the fixture artifacts are under `build/latest-compiler-smoke.eQRS6g/`.
- A follow-up source-provenance and declaration-closure build used the same
  upstream compiler/runtime pair under a 1 GiB stage1 RSS guard. The
  translator executable SHA-256 is
  `ea4df499bab63a57364a9d9d6e4618077afc1e543a0cdb4a984519a73e791067`.
  Source/external context now survives Clang's omitted `loc.file` values across
  top-level siblings and nested declaration/type children; `includedFrom` is
  considered alongside inherited provenance, and an explicit main-file path
  resets the context. A real-Clang fixture proves the old build emitted an
  unused header alias, record and inline helper, while the new build excludes
  them and still retains the hidden `LeafAlias -> HiddenAlias -> Hidden` chain
  through declaration IDs. Its generated `sizeof` check compiles, links and
  matches native C with the current upstream stage1 compiler. Direct and
  missing-dependency checks, the 256/257 AST-depth boundary, and bounded Clang
  failure/input checks all pass. Four native-vs-Elisa manifest cases pass:
  `simple`, `c_compatible_cpp`, `cpp_overloads`, and
  `c_record_pointer_call_arguments`. The 11 manifest-runner self-tests pass.
  `header_inline.cpp` retains both same-directory header definitions, compiles
  with upstream stage1, and its generated executable matches native C++ (exit
  0).
- Latest-compiler pin for the subsequent source-provenance change: live
  `origin/main` and the clean local stage1 source used for verification both
  resolved to `fd2cb3cff470319500db362e5fce2833cbe300de`. The fresh local product
  SHA-256 was
  `6cdcdf45fb396d319ce1d0d4e0c5d35e9b3161bd3e81f8d2e594ee60ac76c2a8`; its
  matching runtime SHA-256 was
  `a58618f5358e30e8c19cf1344d47bddd3a7520ee61f83a471222bb0660e48a8f`. The
  compiler wrapper accepted the product as source-fresh and compiled both the
  runtime support probe and this translator. This upstream revision contains
  the scratch reuse/capacity, allocation-routing and lexer-buffer ownership
  optimizations listed above. The separate main compiler checkout has newer
  uncommitted CoreIR/EDIR changes and its product became stale relative to those
  files during verification, so it was not used as the final toolchain pin.
- The translator rebuilt with that pinned product is
  `build/latest-compiler-provenance.zP0IUM/elisa-c-transpiler-upstream`
  (SHA-256
  `f83667760810140cd1519898584799a14665fd07c58a07c18a1d18b9f2a14884`). The
  new synthetic `includedFrom`-only provenance case passed alongside the real
  Clang hidden-typedef/header fixture; generated Elisa compiled, linked, and
  matched native C. The simple native-vs-Elisa manifest case also passed with
  exit 42. Direct-dependency, missing-dependency and depth-256/depth-257 tests
  passed, as did the source line-limit check, Python syntax check and
  `git diff --check`.
- The dedicated translator stage1 worktree has now been fast-forwarded from
  `fd2cb3c` to `c605b3f`, bringing in the two committed main-worktree changes
  `19f86a3` (shared typed scalar lowering for EDIR and LLVM) and `c605b3f`
  (removal of the duplicate EDIR local-lowering fallback). Its three modified
  compiler files and four untracked index-overload regressions were preserved.
  Stage0 remains at `5284109c`, which matches its live upstream `main`. The
  dedicated stage1 worktree product has not yet been rebuilt from `c605b3f`; a
  previous guarded seed attempt had failed cleanly on stage0 parsing newer
  stage1 constructs, leaving the old product untouched. The currently active
  compiler jobs are using other isolated worktrees, so a duplicate high-memory
  seed/rebuild is deferred until those jobs finish.
- The current full `testdata/upstream/cJSON/cJSON.c` translation has 23,623,912
  raw AST bytes, 3,929,646 projected bytes, 22,046,336 parsed arena bytes and
  222,543 projected JSON values. It emits 1,644 Elisa lines / 87,802 bytes with
  no `<invalid-ir>` or `<invalid-type>` markers; unused external SDK/header
  declarations previously admitted by offset-only source fallbacks are no
  longer projected. Source type names, enum references, direct IDs and
  declaration-graph edges are still collected together in one AST walk.
  `/usr/bin/time -l` reported 14.43 seconds wall time, 11.42 seconds user time,
  53,952,512 bytes maximum translator RSS and zero swaps. This is a single
  timing sample, not a stable latency comparison. The emitted cJSON file still
  fails current Elisa stage1 compilation on mutable optional-pointer assignment
  and value-`if` diagnostics, so cJSON compile/runtime parity remains open.

## Verified focused results

| Scenario | Result | Evidence / boundary |
| --- | --- | --- |
| Transitive declaration-ID retention through type aliases | Pass (bounded F02 slice) | A real-Clang fixture makes source code mention only `LeafAlias`, strips its desugared `Hidden` spelling, and gives `Hidden`, `HiddenAlias` and `LeafAlias` synthetic non-project provenance. The projector follows Clang ID edges across `LeafAlias -> HiddenAlias -> Hidden`, marks retained type declarations in its internal compact AST, and the typed collector emits all three. Generated `sizeof(LeafAlias)` is checked against `sizeof(int)`; latest upstream Elisa stage1 compiled and linked the translation, and native/generated execution matched. Direct-ID retention, missing-signature fail-closed behavior, AST-depth bounds and frontend failure checks also passed. Broader ID-less layout edges, canonical type identity, inline dependencies, templates/specializations and other Clang schemas remain open. |
| Target-aware C plain-`char` string-literal pointer boundaries | Pass (bounded S05/S06 slice) | String literals retain Elisa's `u8` storage but are cast to Clang's target-derived C `char*` representation at external calls and pointer-array initializers/assignments (`i8` on this signed-char Darwin arm64 target). Named C character arrays continue using their contextual ABI representation. `sh scripts/test.sh --suite upstream --reuse-build` passed after rebuilding translator fingerprint `640850d5…a12b` / SHA-256 `33bb90fd…e7c5`: inih translated, compiled, linked, and matched native output; Kilo compiled/linked and matched native no-argument behavior; cJSON structural smoke checks passed, with nullable-function executable parity capability-skipped. `sh scripts/test.sh --suite fixtures --reuse-build` also passed: manifest 12/12, core fixture checks passed, no failures or crashes. System memory stayed at 58–71% free during serial tests. Wide-string encodings and C literal mutability are not covered. |
| Fresh C/C++ fixture suite after unordered-map enum-key work | Pass (fixture suite; cJSON capability skip) | `sh scripts/test.sh --suite fixtures --reuse-build` completed on 2026-09-14. The stale build cache was rejected and the translator rebuilt with the isolated stage0 compiler; the fixture manifest passed 12/12, frontend checks passed, and the core suite completed, including unordered-map growth, enum-key hit/miss/count, iterator reads/writes, and explicit reference-escape diagnostics. Native and generated unordered-map fixtures agreed. cJSON nullable-function executable parity remains explicitly skipped because the selected Elisa compiler rejects nullable function fields. System-wide free memory remained 65–72% during the serial run; no crash or timeout occurred. |
| Effectful pointer-to-record call arguments | Pass (partial S03) | `lower_stmt.elisa` now treats a pointer to a record as a scalar pointer when deciding whether an effectful argument can be materialized; only by-value records remain in the unsupported aggregate path. `record_pointer_call_arguments.c` compiles and matches native C, checking that the record-pointer producer and a second scalar producer each run once before the call. The existing effectful by-value aggregate negative case remains fail-closed. After this correction, `scripts/quality_report.sh` translates the cJSON smoke unit (including `cJSON.c`) to 2,070 lines with zero invalid-IR markers; this is translation/quality evidence, not cJSON compile/runtime parity. |
| C `_Bool` representation and constant boolean folding | Pass (partial S02) | C `_Bool` is normalized to Elisa `bool`; boolean values no longer widen to integer storage when assigned to bool, and a folded comparison emits `false` for zero (rather than unconditionally `true`). The native-vs-Elisa fixture exercises `_Bool` assignment from `0`, postfix increment and prefix decrement; its generated module compiles, links, and exits 0. Broader proof-based bool inference and ABI/target coverage remain open. |
| Scalar pre/post increment/decrement value preservation | Pass (bounded S03 slice) | `increment_evaluation.c` compares native and generated Elisa behavior for prefix/postfix increment and decrement, assignment, nested arithmetic, call arguments, return expressions and conditions. It covers signed `int`, unsigned `char` wraparound, `float`, `_Bool`, and an indexed lvalue with a side-effecting index; helper emission is limited to used scalar type/mode pairs and uses deterministic source-derived names. All eight acceptance-manifest cases have passed across the canonical run and later selected runs; `sh scripts/test.sh --suite control-flow --reuse-build` and the source line-limit check also passed. C/C++ operand-order rules, volatile/atomic sequencing and broader C++ sequencing remain open. |
| Short-circuit assignment conditions and simple assignment-valued expressions | Pass (bounded S03 slice) | `sequencing_expressions.c` verifies that assignments on `&&`/`||` RHSs stay conditional, that `identity(cursor = 9)` both stores and yields its value, and that an indexed `unsigned char = int` assignment expression converts 300 to 44 while evaluating its index once. Native and Elisa executables match; the generic value helper is emitted only when an expression actually uses it. All eight acceptance-manifest cases have passed across the canonical run and later selected runs; `sh scripts/test.sh --suite control-flow --reuse-build` also passed. C/C++ unspecified argument ordering, volatile/atomic operations and general explicit sequencing temporaries remain open. |
| Scalar compound-assignment lvalue evaluation and value results | Pass (bounded S03 slice) | `compound_assignment_once.c` checks that `values[next_index()] += 1` in statement position calls the index function once and preserves unsigned-char wraparound. `sequencing_expressions.c` additionally uses `values[next_index()] += 1` as an initializer and checks the stored result, wraparound and one index call; it also uses `cursor += 3` in a condition. The translator emits concrete helpers specialized by operator and C target/RHS types, passing the lvalue address once. Native and generated Elisa executables match. `sh scripts/test.sh --suite control-flow --reuse-build`, `git diff --check` and the 600-line source gate passed. Other compound operators, pointer compounds and operands with volatile/atomic or more complex sequencing remain open. A wider fixtures run was previously stopped during the unrelated CPU-heavy `cpp_unordered_map_unsupported.cpp` translation; resident memory was stable and no crash occurred. |
| Conditional-comma effects in compound-assignment places and RHS | Pass (bounded S03 slice) | `compound_assignment_conditional_place.c` compares native and generated Elisa behavior for scalar integer `+=` in statement and initializer/value contexts. It checks a member lvalue selected through a comma-effectful conditional array index, a conditional-comma RHS, selected-branch behavior, stored/result values, and exactly-once independent place/RHS effects. Fresh `sh scripts/test.sh --suite control-flow` passed, including this compile/link/runtime differential and fail-closed unsupported-expression checks. This does not establish every compound operator/type or pointer, volatile/atomic, nested conditional-place, overloaded C++ subscript or broader C++ behavior. |
| Comma-effect and residual-side-effect ordering for plain function-pointer calls | Pass (bounded S03 slice) | `indirect_call_conditional_comma.c` exercises a local C function-pointer variable with branch-local effects in one argument and a residual call in another. The native and generated programs agree for both conditional arms and exact effect counts; generated-shape checks verify callee capture, complete residual-argument materialization, and invocation order. Effectful scalar argument values are evaluated as one unit in the translator's chosen argument order. Aggregate/reference arguments and calls through member/computed callees remain unsupported or unverified. |
| Complete effectful-argument groups for direct and indirect function-pointer calls | Pass (bounded S03 slice) | `call_argument_groups.cpp` is translated with its explicit `-std=c++17` compile-database entry and compiled natively with `-std=c++17`. It checks two call arguments that each append a two-event group, through both a named function and the `(*operation)(...)` function-pointer spelling; both programs accept either complete group order and reject interleaving. A volatile scalar read paired with a side-effecting setter checks the read is materialized before the next argument, and generated-shape assertions verify argument order plus callee capture. The focused control-flow suite and all eight selected acceptance-manifest cases passed against the current translator fingerprint. `conditional_comma_unsupported.c` confirms effectful record arguments fail closed with no generated stdout; aggregate/reference materialization and member or genuinely computed callees remain unsupported. |
| Const-qualified volatile comma operands fail closed | Pass (bounded S03 slice) | `const_volatile_comma.c` uses `const volatile int` as the discarded left operand of a comma expression. Qualifier detection now matches the complete `volatile` token rather than requiring it at the start of Clang's type spelling. Translation emits a volatile-sequencing diagnostic and no generated stdout. The focused control-flow suite passed after rebuilding; atomic operations and volatile loop-test lowering remain open. |
| Comma-effect preludes across expression contexts and loop tests; exact `continue` routing | Pass (bounded S03 slice) | `call_argument_conditional_comma.c` covers selected conditional arms in direct translated and external calls, scalar residual argument materialization, eager arithmetic operands, subscripts, member reads, scalar simple-assignment places/values, scalar short-circuit RHS effects in value/`if`/`while` contexts, and repeated `while` tests. `loop_condition_effects.c` compares native/generated behavior for per-test effects in `for` and `do-while`, skipped short-circuit RHSs, structured and goto-forced CFG `for` continue, and nested `do-while` continue. Statement preludes run at the correct loop-test point; native differential checks increments exactly once and effects on every required edge. `sh scripts/test.sh --suite control-flow --reuse-build` passed, including fail-closed unsupported-expression checks; the latest full fixture suite also passed after stage1 was refreshed. Remaining S03 boundaries include other compound-assignment operators/types, member/computed indirect callees, conditional glvalues, volatile/atomic sequencing, record-valued conditional materialization, overloaded C++ subscripting and broader C++ sequencing. |
| Translator build-cache stale-artifact guard | Pass | scripts/test_build_cache.sh validates a fresh matching fingerprint, rejects changed source fingerprints and modified executable bytes, accepts the newly hashed executable, and rejects a non-executable artifact. scripts/test.sh uses this same helper for reuse-build decisions and atomic fingerprint writes. |
| Canonical acceptance run before build-cache helper extraction | Pass | `sh scripts/test.sh --suite all --reuse-build` exited 0 after the actual-helper-emission change and before `scripts/build_cache.sh` was extracted. All fixture, project, control-flow, and upstream suites completed; cJSON compile/runtime parity was reported as a capability skip because this Elisa compiler rejects nullable function fields. |
| Post-extraction upstream smoke suite | Pass | `sh scripts/test.sh --suite upstream --reuse-build` exited 0 and reused the matching translator build. The upstream smoke programs passed, including Kilo compile/link and no-argument behavior parity; cJSON translation/structural checks passed while compile/runtime parity remained a compiler-capability skip. |
| Compilation database direct argv execution, normalization and response files | Pass (partial F01) | Fresh `sh scripts/test.sh --suite control-flow --reuse-build` and `sh scripts/test.sh --suite projects --reuse-build` runs passed; the frontend checks also passed standalone. Both `arguments` and restricted `command` entries use stable NUL-terminated argv and shared direct `execvp`; child cwd, independent stdout/stderr, exit status, output limits and process-group cleanup are uniform. Regressions cover quoted include paths, leading environment assignment, malformed argv/output flags, operator rejection, Clang failure, bounded output, stripping build/dependency artifacts without losing semantic flags, and `-x c++ -std=gnu++11 -D...` overriding a `.c` suffix; generated project executables match native Clang. A focused launcher regression proves assignment shorthand and explicit `env` argv normalize equivalently and collapse to one translation. The supported command decoder/process model is documented as POSIX-only (Darwin tested); Windows is explicitly unsupported. Response-file tests cover nested files, quoted include paths, output/dependency-flag normalization, missing and malformed files, byte and recursion bounds, and an absolute database `file` with a relative source operand for both database forms; missing, malformed, oversized and cyclic response files produce source-qualified diagnostics naming the offending file, and rejection emits no project output. Exact duplicates and canonical `..` aliases collapse to one module, conflicting settings through aliases are rejected, and equivalent cross-form entries collapse after normalized argv comparison. F01 remains incomplete: dependency-aware response-file invalidation (F07), broader driver-option coverage and the wider target/context matrix remain open. |
| Compilation-database effective source operand validation | Pass (partial F03) | Fresh `sh scripts/test.sh --suite projects` rebuilt the translator and passed the complete project suite. The frontend regression script verifies that both `command` and `arguments` forms are rejected before output when their direct source operand differs from the database `file`, and repeats that check when the mismatching source is supplied through a response file. |
| Escaped Clang JSON source paths | Pass (partial F02) | With the latest upstream stage1 product at `fd2cb3cff470319500db362e5fce2833cbe300de` (product SHA-256 `eebb4f562b8128ceedf4761225fd106335978c0a495c44754ec269da5fec1884`), the full translator compiled under a 1 GiB RSS cap. It translated `simple.c` beneath a path containing a literal quote, backslash and UTF-8, generated Elisa compiled with that same compiler, and native/generated executables both returned 42. This directly verifies decoding of Clang's JSON-escaped path before source-identity matching; inherited/omitted source locations remain open. |
| Raw AST JSON maximum nesting depth | Pass (partial F02) | `scripts/test_ast_depth.py` creates temporary fake-Clang JSON with the `TranslationUnitDecl` counted in the depth. The 256-level boundary is accepted; 257 levels are rejected in under the test deadline, emit no partial Elisa, and produce a source-qualified “invalid or over-depth AST JSON” diagnostic. The complete `scripts/test_clang_failure.sh` frontend regression passed against the latest-upstream-built translator. |
| Direct Clang declaration dependencies during projection | Pass (bounded F02 slice) | `scripts/test_decl_dependency_closure.py` starts from a real Clang AST, turns source-local `add` into an external prototype under synthetic non-project provenance, removes Clang's `isUsed` marker and deletes both call-site type summaries. Projection retains the declaration by referenced declaration ID; lowering recovers its full signature and emits `@link_name("add")`. The translator was rebuilt using upstream Elisa compiler `fd2cb3cff470319500db362e5fce2833cbe300de` (product SHA-256 `eebb4f562b8128ceedf4761225fd106335978c0a495c44754ec269da5fec1884`; runtime SHA-256 `a58618f5358e30e8c19cf1344d47bddd3a7520ee61f83a471222bb0660e48a8f`). Latest-compiler native-vs-Elisa fixtures `simple`, `c_compatible_cpp` and `cpp_overloads` all passed. |
| Missing function declaration dependency fails closed with direct caller path | Pass (bounded F02/F03 slice) | `scripts/test_missing_decl_dependency.py` removes `add` and its reference type from a real Clang AST. The translator rejects it without stdout or a guessed `int (...)` signature, and reports `missing-declaration-dependency:main -> add` against `testdata/fixtures/simple.c`. This build used source-fresh upstream Elisa stage1 `fd2cb3cff470319500db362e5fce2833cbe300de` (live `origin/main` matched; compiler SHA-256 `6cdcdf45fb396d319ce1d0d4e0c5d35e9b3161bd3e81f8d2e594ee60ac76c2a8`; runtime SHA-256 `a58618f5358e30e8c19cf1344d47bddd3a7520ee61f83a471222bb0660e48a8f`) to compile the translator (SHA-256 `2cec79ce5c9dc17e56247bfc466b1aa59545eb2573e146c23d3f8b57f9c2d3c4`). Multi-hop declaration dependency trails, template/layout closure and other Clang schemas remain open. |
| ID-less C by-value record-field layout dependency | Pass (bounded F02 slice) | `scripts/test_transitive_decl_closure.py` verifies Clang emits `LayoutOwner.payload` as `struct LayoutOnly` without a declaration ID. After moving both records to synthetic external provenance and removing the source-owned spelling, the projector reconstructs the edge only when the unqualified tag name is unique and emits the complete field layout. A second unrelated complete `LayoutOnly` declaration is injected; the translator succeeds but emits neither candidate layout, proving ambiguous names fail closed. The translator was compiled and linked with the source-fresh upstream compiler/runtime at `fd2cb3cff470319500db362e5fce2833cbe300de` (live `origin/main` returned the same commit; product SHA-256 `6cdcdf45fb396d319ce1d0d4e0c5d35e9b3161bd3e81f8d2e594ee60ac76c2a8`, runtime SHA-256 `a58618f5358e30e8c19cf1344d47bddd3a7520ee61f83a471222bb0660e48a8f`; translator SHA-256 `d9a1198a7e0c69c32f3a89d4876edc5e1f41d4e212bf76907890d6a901334104`). Generated Elisa compiled, linked and matched native C (both exit 0). Direct dependency, missing dependency, depth-256/depth-257, source-line, Python syntax and diff checks passed. With this translator, cJSON emits 1,644 lines / 87,802 bytes without invalid markers; one `/usr/bin/time -l` run took 11.09 seconds, reported 53,772,288 bytes maximum RSS and zero swaps. This is not canonical identity and does not cover namespace-qualified C++ tags, aliases, inline definitions or template/specialization closure. |
| ID-less unqualified C++ record layout and tag/alias ambiguity | Pass (bounded F02 slice) | `src/clang_ast_dependencies.elisa` now accepts a bare identifier (with cv/restrict qualifiers only) as a layout candidate only when the global name index resolves one explicit record/class declaration and no typedef/type-alias name shadows it. It ignores implicit C++ injected-class-name entries and leaves elaborated `struct`/`class` lookup unaffected by tag/alias collisions. `scripts/test_transitive_decl_closure.py` proves `typedef int Token` does not cause a same-named `struct Token` to be retained for an `AliasOwner` field; `scripts/test_unqualified_cpp_layout.py` uses real Clang C++ AST JSON for an external `Owner { Layout payload; }` with no declaration edge, checks implicit-name filtering, and injects another `Layout` to prove ambiguous lookup fails closed. Latest upstream `main` was verified live at `fd2cb3cff470319500db362e5fce2833cbe300de`; the clean local stage1 product used for verification has SHA-256 `6cdcdf45fb396d319ce1d0d4e0c5d35e9b3161bd3e81f8d2e594ee60ac76c2a8` and its matching runtime SHA-256 is `a58618f5358e30e8c19cf1344d47bddd3a7520ee61f83a471222bb0660e48a8f`. The final translator object/executable hashes are `cd6c272b77e5513c6b5b0a72f404457559772c4398f68326f900e0ed953dac1b` / `4b63f0cfc9d8fad1650068c33684745adff58d1566bba848f9ba6b14c967ca89` in `build/latest-upstream-f04/`. Both generated programs compiled with that stage1 product, linked with Clang, and matched native execution (exit 0). Declaration-closure, missing-dependency diagnostic and depth-256/depth-257 regressions also pass with this translator. Namespace-aware canonical resolution, aliases whose identity metadata is absent, templates/specializations, inline dependencies and other Clang schemas remain open. |
| Omitted Clang `loc.file` with `includedFrom` | Pass (one observed schema; partial F02) | Homebrew Clang 23.1.1 on Darwin arm64 omits `loc.file` for `add_one_value` in `header_inline.h` but includes `loc.includedFrom.file` for `header_inline.cpp`. The latest upstream translator retained both local header-inline definitions; generated Elisa compiled with the same upstream stage1 product, and native/generated executables both exited 0. This does not cover Clang versions with different inherited-location serialization or locations missing both fields. |
| Canonical AST main-source origin matching | Pass (partial F03) | The projector now resolves the main source's physical path once per AST projection and reuses it for path identity checks; it rewrites only exact physical matches to the source/database spelling, leaving same-directory sibling header origins intact. A symlink regression pairs the symlink in the database `file` with the physical target in the compiler operand, for both database forms; both generated modules contain `return 42`. Full canonical origin fields, inherited macro filenames and source maps remain open. |
| Macro spelling, expansion, physical-source and immediate includer diagnostics | Pass (partial F03) | The fresh stage0 translator build and direct control-flow suite passed. Diagnostics preserve requested/source spelling, macro spelling, macro expansion, line/column, canonical physical paths, and Clang's explicit immediate `includedFrom.file` for each macro origin; typed-IR v5 serializes these path fields hex-encoded. Regressions cover an in-translation-unit macro, a header macro expanded at two callsites, source/header resolution under a compilation-database working directory, a source symlink, and a macro defined in a nested header. The nested case proves `macro_origin.h` was immediately included by `macro_origin_include.h`; the full transitive chain is not inferred. Repeated file spellings reuse prior canonical identities. The user-facing diagnostic remains readable and keeps source spelling. Omitted macro `file` values still fall back to translation-unit spelling; reliable inherited-file reconstruction, transitive include ancestry, source hashes and full source maps remain open. |
| Translation-unit declaration ID/redeclaration index | Pass (partial F03) | Each parsed AST gets one bounded-load open-addressed index before type collection. Declaration lookup, record-definition selection, typedef-to-record/enum resolution, inline-header classification and external-call signature recovery use indexed IDs instead of recursively rescanning the AST; `previousDecl` edges and canonical IDs are retained in each slot. The direct control-flow suite passed, including `declaration_index.c` (36 globals force table growth; a prototype/definition pair remains callable) with native/generated runtime parity. Its typed-IR v5 dump reports `canonical=false has_previous=true` for the referenced definition without exposing Clang's unstable ID, directly exercising canonical resolution. The multi-file `forward_decl` project translated, matched expected extern/definition/export output, compiled with the local stage1 compiler and ran with exit 0. The typed-IR verifier unit was recompiled and exited 0. The latest fixtures run passed all eight manifest differentials, then stopped at the unrelated C++ reference-cursor case because stage0 rejects generated `ptr: mutable u8&? = bytes` (`bytes` is `array[u8, 4]`). Full C++ runtime parity remains open. |
| Scoped typedef identity and C++ `using` aliases | Pass (partial F04) | Fresh `sh scripts/test.sh --suite control-flow` rebuilt the translator and passed. The new `typedef_identity.cpp` fixture declares same-spelled aliases in separate namespaces using both C `typedef` and C++ `using`; the AST projection preserves `TypeAliasDecl`, alias recovery keys by qualified spelling plus Clang canonical declaration identity, and generated function signatures retain `u32` versus `u64`. Native and generated programs both exit 0. Structural canonical type nodes, qualifiers/layout and broader C++ scope forms remain open. |
| Qualifiers at nested pointer levels | Pass (focused partial F04) | `c_type_pointer_qualifiers_match` compares `const`, `volatile`, `restrict` and `_Atomic` at each printed pointer depth; multi-level cast/call compatibility no longer compares only the base qualifier. `c_type_pointer_can_write` emits an immutable chain for an all-readonly type such as `const int * const *`, while mixed chains retain Elisa's one global mutability capability if any pointee level is writable. `pointer_qualifier_layers.c` checks this readonly signature and retained casts for intermediate-const removal/base-volatile addition; native/generated executables both exit 0. `git diff --check` and the 600-line source gate pass. The local compiler rejects nested mutability syntax `(mutable i32&) &` (`expected IDENT, got mutable`), so mixed-layer permissions remain broader than C until both compiler stages support compositional ref qualifiers; retained casts are still warned as type-redundant. |
| Manifest-driven acceptance and runner failure classification | Pass | sh scripts/test.sh --suite fixtures passed all 11 runner self-tests and the simple, c_compatible_cpp, and readonly_nonnull_helper manifest cases. Tests verify nonzero expected exits, independent stdout/stderr capture, differential mismatches, signal crashes, timeout process-group cleanup, unsupported diagnostics, missing tools, optional skips, malformed manifests, and captured binary artifacts. |
| C enum storage and verifier metadata/reference distinction | Pass (partial S01/S02) | Fresh `sh scripts/test.sh --suite fixtures` rebuilt the current translator. Clang's explicit enum base/common `EnumConstantDecl` type is retained in typed IR; `WideMode` with `0xffffffffu` emits as `enum ... of u32`, mixed comparisons convert to `u32`, and the generated executable matches native Clang. The standalone verifier test roots an enum-name node whose `third` metadata is `4294967295`; it passes without treating that value as an expression-table index. Enum ABI cases where Clang JSON omits the selected representation (such as `-fshort-enums`), full target-dependent integer rules and scoped C++ enum conversions remain open. |
| C enum integer conversions at typed value boundaries | Pass (partial S02) | `enum_integer_semantics.c` verifies native/generated parity for integer-to-enum conversion at global/local initialization, assignment, call arguments, returns, record fields and scalar array elements; enum-to-integer conversion on returns and scalar call arguments; named and unnamed C enum values; and signed `i32` plus unsigned `u32` representations, including `|=`. The emitter preserves direct same-enum values and otherwise converts through Clang's selected scalar width/signedness before invoking the Elisa enum constructor. The acceptance-manifest case includes a generated-shape assertion for enum array constructors; all 11 manifest differentials and the complete fixtures suite passed with refreshed local stage1. Enum typedef/namespace aliases, `-fshort-enums`, all aggregate forms beyond tested record fields/scalar arrays, and scoped C++ enum rules remain open. |
| C/C++ array-to-pointer decay at typed value boundaries | Pass (partial S05) | `cpp_reference_cursor.cpp` previously emitted `ptr: mutable u8&? = bytes`, which stage0 rejected. `typed_emit_target_value` now routes array sources assigned to pointer targets through the generic pointer conversion used for call arguments, emitting `(&(bytes)[0]).cast[mutable u8&?]`; actual array targets remain on aggregate emission, including arrays whose elements are pointers. The core fixture asserts this spelling, compiles/links native and Elisa programs, and compares pointer stepping, one-past equality, and reference-to-pointer updates. The complete fixtures suite passed with this regression, plus `pointer_array_decay.cpp` row-pointer checks. Pointer subtraction/provenance, alias/lifetime modeling, dynamic arrays and complete pointer-ABI coverage remain open. |
| C-width-aware integer constant evaluation | Pass (partial S02/F04) | Fresh `sh scripts/test.sh --suite fixtures --reuse-build` passed. Native differential fixtures verify `u32` add/multiply wrap, unsigned bitwise-not, mixed `-1 < 1u` usual conversion, and unsigned shift wrap; condition folding emits the mixed comparison as `true` without a spurious truncating cast. `invalid_shift_count.c` confirms a `u32` count of 32 and signed-negative right shift remain as Elisa shift expressions rather than being folded. Target scalar widths and plain-char signedness now come from Clang; folding still conservatively declines host-overflow-risk signed and 64-bit arithmetic. Full-width `u64` constant evaluation and signed-overflow rules remain open. |
| Clang-derived scalar target ABI | Pass (partial F04) | Fresh `sh scripts/test.sh --suite fixtures --reuse-build` passed on the 64-bit host; after the pointer-width guard was added, `sh scripts/test.sh --suite control-flow --reuse-build` rebuilt the translator and passed. The cross-target `target_abi_compile_commands.json` test verifies LLP64 `long -> i32`, `unsigned long -> u32`, `size_t -> u64`, plain `char -> i8`, plus matching global and record-field types. The host `compiler_builtins.c` fixture compiled, linked and matched native behavior, including unknown `__builtin_object_size` results at 64-bit `SIZE_MAX`; a cast from `char *` to `unsigned char *` remains explicit when the target's plain char is signed. ABI parser unit checks verify LP64/LLP64, unsigned-char macro capture and rejection of a 32-bit pointer target against the local backend. The ABI query is bounded and uses the exact normalized compiler argv. Pointer width must match the Elisa backend; full record layout/alignment, bit-fields, calling conventions, `-fshort-enums`, and non-32-bit `int` targets are still unsupported; unavailable scalar ABI facts fail closed. |
| Short-circuit-aware constant conditions | Pass (partial S03) | `short_circuit_constant.c` puts side-effecting calls on the RHS of `0 && call()` and `1 || call()`. The constant evaluator returns before traversing either unreachable RHS; the lowered, unreferenced constant-left subgraph is removed too, so generated `main` reduces to `pass; return calls` with no runtime call or orphan IR. Its acceptance-manifest case checks output shape and native/Elisa exit parity (both return 0); the focused control-flow suite and selected manifest run passed. General sequencing, nonconstant short-circuit expressions and exact-once evaluation remain open. |
| Demand-driven generic non-null helpers | Pass | simple.c now emits no unused helper; readonly_nonnull.c emits only elisa_nonnull_readonly; existing mutable-pointer fixtures still emit and compile with elisa_nonnull. The complete focused fixture suite passed after this change. |
| Translator-owned C++ `unordered_map` recognition and boxed mapped values | Pass (partial L01/L02) | Verified scalar/enum keys and integer/floating/nullable object-pointer mapped values support `operator[]`, `clear`, `size`, `empty`, `contains`, `count`, key erase and scalar `find`/`end` iterator projections; `first`/`second` read by value and translated writes to `second` pass native/generated checks. A 64-key growth/readback test, enum-key queries, pointer default-null insertion, and C++17 iterator hit/miss checks passed with isolated Stage1 products. The adapter rejects unsupported key hashing, mapped-value initialization and extra template policy arguments. Reference binding/address-taking is rejected; full mapped-value construction/lifetimes, iterator/reference stability and insertion/emplacement APIs remain open. Recognition remains spelling-based rather than canonical-declaration-based. Evidence is distributed across the 2026-09-14 L02 plan record, 2026-09-29 pointer-value fix and 2026-09-30 iterator regression record below; do not treat those historical compiler runs as validation of the current dirty translator tree. |

| `__builtin_object_size` intrinsic lowering | Pass (supported provenance) | `testdata/fixtures/compiler_builtins.c` translated and its generated Elisa compiled, linked, and ran with the local compiler. Native/Elisa checks cover fixed-array sizes in modes 0–3, an array field in a named record (whole-record extent for modes 0/2 and field extent for modes 1/3), and unknown pointer results (`SIZE_MAX` for modes 0/1, zero for modes 2/3). Emission uses Elisa `size_of[...]` and `offset_of[...]`; no external `object_size` binding is generated. Complex/indirect provenance outside the recognized forms is diagnosed rather than guessed. |
| Direct C translation of `testdata/fixtures/simple.c` | Pass | Fresh local-stage0-built translator emitted Elisa; it compiled and linked with the same local stage0 compiler and exited with the expected status `42`. |
| C++-syntax subset translation of `testdata/fixtures/c_compatible.cpp` | Pass | Fresh translator selected Clang++ and emitted the expected `add` and `main` functions; the Elisa output compiled, linked, and exited with the expected status `42`. |
| Successful compilation-database translation of `forward_decl_main.c` and `forward_decl_impl.c` | Pass | Produced two Elisa units and `elisa_project.elisa` under an isolated temporary output directory. |
| Stable project output identity for filename/identifier collisions | Pass (bounded P01 slice) | A four-unit project contains two `part.c` files plus `symbol-unit.c` and `symbol_unit.c`, whose distinct module stems sanitize to the same Elisa initializer stem. Normal and reversed compilation-database orders produce identical canonical-source-derived module-name sets, byte-identical manifests and byte-identical generated modules. Each initializer definition is unique and resolves from its manifest call. Both generated projects compile with local stage1 and exit 0, matching native Clang. A direct-input alias regression confirms duplicate physical inputs are rejected before translation output; equal disambiguator hashes are rejected before writing. C static functions/data and C++ anonymous namespaces have separate bounded identity regressions. Broader declaration-registry integration, other C++ internal-linkage forms and initialization-order policy remain open. Fresh `sh scripts/test.sh --suite projects` passed. |
| Translation-unit-local C static function names | Pass (bounded P01 slice) | Two project units define different file-scope `static int helper(int)` functions; one unit also stores its helper in a function pointer. A shared header defines a `static inline` helper included by both units, verifying that it is emitted once per translation unit rather than project-wide deduplicated. The translator emits distinct, canonical-source-derived private Elisa identifiers for each definition and matching reference, but preserves source names for ordinary single-file output. Normal and reversed compile-database orders produce the same four-symbol private set. Both generated projects compile with local stage1 and match native Clang. Fresh `sh scripts/test.sh --suite projects`, `--suite fixtures`, and `--suite control-flow --reuse-build` passed after rebuilding the translator. cJSON compile/runtime parity remains the known nullable-function-field capability skip. Function/type collision-registry integration and additional C++ internal-linkage forms remain open. |
| Translation-unit-local C static data names | Pass (bounded P01 slice) | `TypedGlobal` retains its canonical declaration key, private-linkage flag and stable source-derived identity hash. Static file globals, block-scope static locals and a shared-header static object are resolved by declaration identity (so same-spelled declarations remain distinct) and emitted with translation-unit-private Elisa names in project mode; ordinary single-file output keeps source names. Direct translation in normal and reversed compile-database order emits the same six private global names. Both generated projects compiled with the local stage1 compiler under the configured 4-GB RSS cap and exited 0, matching the native fixture. The latest complete project suite passed. Collision-registry coverage for all declarations remains open. |
| C++ anonymous-namespace identities | Pass (bounded P01 slice) | Two C++ translation units each define an anonymous-namespace `helper(int)` and `project_anonymous_state`, plus a distinct externally linked wrapper; `main` verifies that the private state instances remain independent. Normal/reversed compile-database orders yield identical sets of two private function names and two private global names. Native C++ and both generated Elisa projects compile and exit 0 under the existing 4-GB RSS cap. Broader implicit-linkage cases, namespace-scope `const` objects, and exact overloaded-declaration identity remain open. |
| C++ namespace-scope const-object linkage | Pass (bounded P01 slice) | Project inputs derive their language mode from Clang's active `__cplusplus` predefined macro, not source suffix: a three-unit `.c` project compiled with `-x c++` contains same-named scalar namespace-scope `const` objects with different values. Those objects receive distinct translation-unit/declaration-derived Elisa identities, while a const global preceded by an explicit `extern` declaration remains shared across units. Normal and reversed compile-database orders compile/link with local stage1 and match native Clang C++ runtime behavior. Const-qualified function-pointer declarators and inline-variable ODR equivalence remain open. |
| Local C++ overload calls | Pass (bounded C01 slice) | Clang's selected declaration signature is retained for local direct overload calls. Numeric arguments are converted to the selected parameter type, and integer-valued `double`/`float` literals retain distinct types. The C++17 differential fixture covers `int`, `float`, `double`, and `long` overloads and `short`-to-`int` promotion. The generated Elisa program compiles, links, and matches native execution. External/project overloads are covered separately; namespace/member/template overloads remain open. |
| C++ overloads across project translation units | Pass (bounded C01 slice) | A two-unit C++17 project defines four same-name/same-arity overloads in one unit and calls the declaration-only overload set from another. Calls retain Clang's exact selected target through synthetic Elisa external aliases keyed by the mangled linker identity, avoiding collisions between `extern` declarations and the translated overload implementations. The emitter applies the selected argument conversion (`short` to `int`); both compile-database orders produce the same manifest, and both generated stage1 executables match native C++ behavior. The complete project and fixture suites passed after this change; the fixture suite reports only the existing skip for cJSON nullable-function-field parity, unsupported by the selected Elisa compiler. Namespace-qualified functions, member/library overload families, references and templates remain open. |
| External function declaration compatibility | Pass (bounded P01 slice) | Project-mode declarations are checked by Clang linker name and a normalized function signature before output publication. The check expands typedefs, ignores top-level cv/restrict qualifiers for simple scalar/pointer parameters, retains pointee constness, treats empty `()` and `(void)` parameter lists consistently, and reports table exhaustion rather than silently skipping checks. Normal/reversed four-unit projects cover compatible typedefs, qualified/unqualified parameters and empty-prototype/void declarations; both generated Elisa executables match native C. Normal/reversed conflict projects reject `int`/`long` declarations and `int *`/`const int *` declarations without writing a manifest. Fresh `sh scripts/test.sh --suite projects` and `sh scripts/test.sh --suite control-flow --reuse-build` passed; `sh scripts/test.sh --suite fixtures --reuse-build` passed with the known cJSON nullable-function-field capability skip. Nested callback/array declarators, full C default-promotion compatibility for non-prototype declarations, C++ ABI attributes, and one canonical emitted-declaration registry spanning functions, objects and exports remain open; object declarations have separate bounded checks. |
| External object declaration compatibility and initialized-extern definitions | Pass (bounded P01 slice) | Project AST collection checks user-owned explicit `extern` object declarations by linker name and desugared type, including declarations not referenced by emitted code. Incomplete and complete outer array bounds are compatible only when element types and remaining dimensions agree; different fixed bounds conflict. A file-scope `extern int value = 37` is retained as an initialized project global instead of being discarded as declaration-only; a two-unit native/generated runtime fixture checks direct and function-mediated reads and identical manifests under reversed compilation-database order. A separate C++ fixture diagnoses duplicate initialized `extern` definitions in normal and reversed database orders without publishing a manifest. Existing negative projects reject `int` versus `long` and `[3]` versus `[4]` declarations. Fresh `sh scripts/test.sh --suite projects` passed with the local stage1 compiler and runtime. Non-`extern` definitions, C tentative-definition coalescing, inline-variable ODR equivalence, canonical structural record identity, C++ namespace-scope linkage policy beyond the const-object slice, and unification of emitted declarations remain open. |
| Stable project unit ordering | Pass (bounded P01 slice) | Project sources are sorted by canonical physical source identity, then directory/path spelling as a stable fallback, before translation, manifest include generation and initializer emission. The multi-file collision fixture compares the complete manifest and each generated module byte-for-byte across reversed database order; the external-declaration fixture does the same. Fresh `sh scripts/test.sh --suite projects` passed, including stage1 native-parity execution in both orders. Explicit constructor-priority and other source-order-sensitive initialization policies remain unaudited. |
| Direct C input rejected by Clang | Pass | `scripts/test_clang_failure.sh` observed nonzero status, no generated stdout, and a source-qualified translator diagnostic. |
| Direct C++-subset input rejected by Clang++ | Pass | Nonzero status, no generated stdout, and a source-qualified translator diagnostic. |
| C and C++ compilation-database inputs rejected by their Clang drivers | Pass | Both returned nonzero, emitted no translator stdout, and left no generated project files. |
| Partial-AST regression precondition | Pass | The fixture makes Clang exit 1 after writing 54,638 bytes of parseable `TranslationUnitDecl` JSON; the test script checks for this behavior before testing the translator. |
| Configurable frontend-output limit | Pass | `--max-frontend-output-bytes 64` rejected a larger Clang AST and compilation database without output/artifacts; zero was rejected before launching Clang. |
| Opt-in frontend metrics | Pass | `--frontend-stats` reports raw/projected JSON bytes, preflight value count, and parsed arena bytes; a regression confirms its Elisa output is byte-identical to ordinary single-file output. |
| Pre-DOM AST value limit | Pass | A low `--max-frontend-json-values` limit rejected a fixture with no JSON-arena allocation and a source-qualified diagnostic; zero is rejected during option parsing. |
| Raw Clang JSON validation before projection | Pass | A fake successful Clang driver supplied a truncated `inner` array and an invalid string escape inside a field the projector drops; both produced `invalid-json` diagnostics and no Elisa output. The pre-change translator accepted both and emitted 40-byte Elisa stubs. The complete cJSON AST still passes and generates byte-identical output. |
| Compilation command quoting | Pass | `command` and `arguments` database forms both resolved a header through an include path containing spaces and emitted the expected `return 42`. |
| Shell control syntax in a command string | Pass | `&&` was rejected before process launch, with no stdout or generated project files. |
| Full translator regression suite | Pass | `sh scripts/test.sh` exited 0 using local stage0 and refreshed local stage1. C/C++ fixture and project-generation checks passed; inih output matched native; cJSON translation/structure checks passed; Kilo compiled and its no-argument behavior matched native. |
| Source-size gate and modularized test harness | Pass | `scripts/check_source_line_limits.sh` enforces the 600-line limit for maintained Elisa files in `src/` and `cpp_lib/`, excluding generated `build/` outputs. `scripts/test.sh` sources focused fixture, project-generation, control-flow, and upstream suites. |
| Focused suite selection and content-based build reuse | Pass | `--help` documented four focused suites; an invalid suite was rejected with status 2. Full suite passed. `--reuse-build --suite control-flow` and `--reuse-build --suite upstream` both reused the matching translator binary and passed; reuse hashes implementation/stdlib inputs, local compiler, Clang, flags/platform and the output executable. |
| Explicit local compiler path validation | Pass | Test invocations with invalid `ELISAC_BIN` and invalid stage1 worktree paths fail early with status 2 and actionable local-worktree errors; no installed compiler fallback is attempted. |
| Bounded Elisa source modules | Pass | All maintained production `.elisa` files are at most 600 lines. AST capture/access/projection and the oversized type, expression, CFG, statement and control-lowering modules were split at declaration boundaries. |
| Output preservation after emitter extraction | Pass | A fresh `--frontend-stats` translation of `testdata/upstream/cJSON/cJSON.c` compared byte-for-byte with the pre-extraction spooled output; frontend metrics stayed at 22,765,720 raw bytes, 2,099,598 projected bytes, 12,013,216 arena bytes and 117,062 projected values. |
| Invalid-Goto fixture reaches translator diagnostics | Pass | Replaced an undeclared-label program (which Clang correctly rejected first) with a valid GNU C indirect-goto case; the test now verifies the translator’s unsupported `AddrLabelExpr` diagnostic. |
| Broad generated-program compile/link/runtime parity | Partial | The full fixture suite ran successfully, including numerous native-vs-generated checks. cJSON compile/runtime parity was explicitly skipped because this stage0 does not support the nullable-function-field probe; Wolf remains unverified. |
| Typed IR verifier reference/range and ownership slice | Pass (bounded S01 slice) | `testdata/typed_ir_verifier_test.elisa` compiles and runs: empty/one-function valid IR is accepted; malformed binary operands, an invalid `ArrayIndex.value` side-effect edge, an out-of-range function-local label ID, overlapping function/external parameter and record-field ranges, overlapping expression-argument/block-child/switch-case slices, cross-function statement sharing, and orphan statements/expressions/child-table entries are rejected. Reachability follows expression operands, argument slices, global initializers, switch values and the non-obvious array-index side-effect edge. Compile-time object-size modes no longer allocate runtime IR; a folded conditional drops its temporary test and lowers only the chosen arm. Fresh `sh scripts/test.sh --suite fixtures` rebuilt the translator and passed, including cJSON smoke translation; `--suite control-flow --reuse-build`, `--suite projects --reuse-build`, and `--suite upstream --reuse-build` passed against that build. Declaration/type identity, full CFG-edge semantics, value-category, scope/lifetime checks and pass-selection controls remain open. |
| Typed switch case/default edge invariants | Pass (bounded S01 slice) | The verifier requires no more than one default per switch, requires default edges to use the `value = -1`/nonconstant representation, and requires each non-default case edge to reference an expression. Focused valid and malformed-IR regressions are in `testdata/typed_ir_verifier_test.elisa`. The standalone harness was freshly compiled and run with local Stage1 `elisac-stage1-callbackfix-final-v3-o1` and matching `elisacore_runtime.callbackfix-final-v3-o1.o`; exit status 0. This is structural switch validation only, not complete CFG-edge, duplicate-constant-case, value-category, or scope/lifetime verification. |
| Typed control-transfer lexical-scope invariants | Pass (bounded S01 slice) | The verifier tracks loop depth, nearest breakable construct, and the active `for` increment through blocks, branches, loops, labels, and switch cases; incompatible cross-scope statement sharing is rejected. Focused cases accept `continue` in a `for`, through a nested switch, and in a nested `while` that correctly resets the active increment; they reject out-of-scope/misclassified break forms, a mismatched continue increment, and a non-expression `for` increment. The standalone verifier harness compiled and ran with local Stage1 `elisac-stage1-callbackfix-final-v3-o1` plus its matching `elisacore_runtime.callbackfix-final-v3-o1.o`; exit status 0. The lowering preserves a `goto` leaving a loop from inside a nested switch instead of collapsing it to a switch-local `break`. `goto_out_of_loop_from_switch.c` passed native/generated runtime parity, and `sh scripts/test.sh --suite control-flow --reuse-build` passed with that freshly rebuilt translator, the pinned local Stage1 compiler and matching runtime. The translator build stayed within the explicit 1 GiB RSS cap (peak 430144 KiB RSS; 424498 KiB physical footprint). This remains one bounded control-flow slice, not complete CFG-edge or general scope/lifetime verification. |
| Private-global declaration identity invariant | Pass (bounded S01 slice) | A private-global `Name` reference must point to an in-range private `TypedGlobal`, match its target spelling, and carry that target's canonical declaration ID. The verifier harness accepts a valid reference and rejects mismatched names and missing identity. A fresh translator rebuild under the 1 GiB RSS cap (peak observed physical footprint 423010 KiB) and the complete `sh scripts/test.sh --suite fixtures --reuse-build` suite passed, exercising this harness alongside generated/native parity checks. This does not yet attach canonical IDs to local variables, parameters or function references, nor prove every source `DeclRefExpr` reaches the right canonical binding. |
| Typed call-mode and signature-index invariants | Pass (bounded S01 slice) | The verifier checks that direct calls have no expression callee, indirect calls have one, only known mode tags are used, encoded user/external signature tags have valid alignment, and each index is in its respective table. The harness accepts direct, indirect, user-signature and external-signature calls, and rejects callee-mode mismatches, unknown/misaligned tags and out-of-range indices. The fresh bounded translator rebuild (peak 451056 KiB process-group RSS / 423010 KiB physical footprint) and all four focused suites (`fixtures`, `control-flow`, `projects`, `upstream`) passed with local Stage1 and its matching runtime. The shared Clang-failure preflight intermittently omitted Clang++ stderr during two suite invocations; isolated reruns passed, and subsequent project/upstream suite reruns passed. No translator change was made for that transient; reproducibility under concurrent host load remains unproven. Canonical declaration matching for encoded signatures and call argument/return type verification remain open. |
| Deterministic typed-IR dump | Pass (diagnostic facility) | `--dump-typed-ir` emits `typed-ir-v7`, adding private-global linkage and source-derived identity fields while continuing to hex-encode source text and diagnostic origins, preserve stable table order and exclude raw Clang declaration IDs. Version 7 retains function internal-linkage identity and the explicit `do-while` condition-prelude / `continue` increment references in existing statement slots. Declaration-info records expose stable canonical/previous-declaration booleans only. Diagnostic records include requested/canonical paths, macro spelling and expansion paths, immediate includer paths and coordinates. `sh scripts/test.sh --suite control-flow --reuse-build` passed v7 CLI checks, while `--suite fixtures --reuse-build` compiled/ran the typed-IR verifier and repeated-dump determinism checks. Pass-selection controls remain open. |

## C++ unordered_map policy-fixture expansion — 2026-10-02

The unsupported-policy fixture now includes custom hasher and equality types,
plus an explicit nested `std::allocator<std::pair<const int, int>>` argument.
The shell regression requires at least three generic policy diagnostics and
empty translated output. A bounded Clang C++11 syntax check passed with the
process-group guard (`66,624 KiB` peak RSS); this verifies fixture syntax only.
Static shell/source-limit/diff checks also pass.

The translator-level regression has not been run: many current Elisa source
inputs are newer than `build/elisa-c-transpiler`, so that binary is stale and
must not be used as evidence. Before the syntax check, no Elisa compiler process
was visible and `24,537 / 1,572,864` VM pages were free. A later static-check
snapshot showed `33,611` free pages (about 2.1%), still below a prudent build
window; no translator or Stage1 build was started. The expanded policy
diagnostic assertion remains pending a fresh translator build in a safe window.

## Latest isolated Stage0 refresh and translator compile probe — 2026-10-02

The isolated Stage0 worktree was fast-forwarded from `e42bbdfe` to the clean
Stage0 main commit `a98ef922`; its one existing tracked parser fix and three
untracked local files were preserved, and the main checkout was untouched. A
separate compiler binary was built from that updated source:
`stage0-latest/compiler/bin/elisac-local-mainrefresh-2026-10-02`, SHA-256
`aa1c56d72a3b8c7243596ae6cf1f15bf8a4f59eff8f7e7d6b099e40067505c42`.
The bounded Go build peaked at 584,288 KiB RSS and 346,195 KiB physical
footprint.

Using this compiler exposed nine ambiguous postfix-return/effect-clause forms
in the translator. Parenthesizing the effectful call disambiguates the parse;
the next bounded build passed parsing but failed during the compiler's
local-borrow/region analysis, reporting borrowed AST views or local values
being stored into longer-lived darrays. No translator object was produced, so
this is not a successful translator build. Peak process-group RSS was about
350 MiB / physical footprint about 315 MiB; memory was not the failure cause.

The isolated Stage1 worktree is still at `e8f7469e` while Stage1 main is at
`bb5a13cf`; six main commits are not yet merged, and the Stage1 main product
fails its freshness check against current sources. A read-only merge preview
shows one conflict in `src/semantic/check_local_view_return_escape.elisa`.
The shared seed lock is absent and system memory pressure was 56% free at the
last check, but Stage1 synchronization and a source-fresh seed are still
required before validating the current translator with Stage1.

## Findings

- Clang and Clang++ can emit partial JSON before returning failure. The driver
  must treat the child exit status as authoritative and must not translate or
  publish that partial AST. Direct and compilation-database regressions now
  cover both drivers.
- Projection is lossy by design, so validating only its result can hide damage
  in fields that are discarded or synthesize a closed empty declaration list
  from truncated input. A strict allocation-free raw JSON scan now runs before
  projection; on failure, the unprojected bytes reach the ordinary parser for
  its established diagnostic. The separate projected-value cap still runs
  before DOM allocation.
- Returning a record that contains a `darray[u8]` together with a status flag
  corrupted the AST bytes in this compiler configuration. Replacing that
  shape with caller-owned output buffers and a mutable status out-parameter
  restored successful C, C++-subset, and compilation-database translation.
- `arguments` compilation-database entries now use direct `execvp`, stable
  NUL-terminated copies of JSON strings, child-side working-directory changes,
  independent stderr capture, child-status checks and process-group cleanup.
  The 32-bit POSIX `pipe` descriptor array is explicitly represented as
  `i32[2]`; passing an Elisa `int[2]` had packed the descriptors incorrectly
  and caused the parent to retain the pipe writer indefinitely.
- Compile-command strings are tokenized using a restricted POSIX-like word
  grammar and passed directly to `execvp`; leading `NAME=value` words use the
  `env` utility. No shell is started. Expansion, substitution, redirection,
  globbing, and control operators fail closed. This deliberately is not a
  complete shell or cross-platform command-line parser. Explicit `@file`
  arguments in both database forms are expanded before normalization; nested
  relative paths use the entry cwd, empty files are accepted, cumulative bytes
  share the configured frontend-output budget, and nesting/argv counts are
  bounded. The response parser reuses the restricted POSIX-like token grammar,
  not every platform-specific Clang/clang-cl dialect. Missing, unreadable,
  malformed, cyclic/deep and over-budget files now report their offending path
  and source during preflight. Response files are not yet part of
  dependency-aware cache invalidation (F07). The launcher policy is direct
  argv execution with explicit wrappers preserved, and the tested command
  grammar is POSIX-only; broader driver-option coverage and more diagnostic
  precision remain open under F01/B02.
- Compilation database normalization currently strips known action/output and
  dependency-generation options before adding AST-dump flags. `-Xclang`,
  `-Xlinker`, and `-Xpreprocessor` operand pairs are preserved to avoid
  reinterpreting forwarded options. Regression coverage exercises `-c`, `-o`,
  `-MD`, `-MF`, `-MT`, `-MQ`, `-MJ`, serialized diagnostics, `-save-temps`, and
  `-ftime-trace`; uncommon driver-specific output options may still need adding.
- Duplicate compile-database detection stores a canonical filesystem identity
  for existing sources and uses it to collapse path aliases; unresolved paths
  fall back to lexical spelling plus cwd. Entries still need identical cwd and
  compiler settings to collapse, and conflicts are rejected before output.
  Regressions exercise a `..` alias both with identical argv and conflicting
  defines. `command` and `arguments` entries now compare by an unambiguous
  length-prefixed signature of normalized argv after response expansion;
  working directory remains part of identity. Sharing canonical source
  identity with source-qualified diagnostics remains open.
- A manual response-file probe exposed a source-location identity gap: Clang
  accepts an absolute compilation-database `file` paired with a relative source
  operand from an `@file`, but a lexical-only ownership check left an empty
  Elisa stub (`raw_json_bytes=55355`, `projected_json_bytes=41`, three JSON
  values). The projector resolves the main source's physical path once against
  the compilation entry's working directory, reuses that identity for AST
  location checks, and normalizes only exact main-file `file` origins to the
  database source spelling. Same-directory sibling headers retain their own
  file origins. Both
  `command` and `arguments` response-file forms have regressions for this
  absolute/relative mismatch. Canonical source identities are also stored on
  compile-database entries to collapse aliases and reject conflicting settings.
  The effective source operand is now checked after response expansion and
  option normalization against the database `file`; the scanner skips known
  separate-argument options so their values cannot be misidentified as source
  operands. Mismatches fail before module output, with regressions for direct
  and response-file operands in both database forms. A symlink regression
  verifies canonical main-source matching when the database names the symlink
  and the compiler operand names its physical target, for both database forms.
  Unsupported-feature diagnostics retain distinct macro spelling and expansion
  paths plus line/column coordinates. Their canonical physical paths are
  resolved against the translation unit's Clang working directory, while the
  original spellings remain available for display. The projector keeps macro
  location trees only when macro-origin metadata is present. Clang's explicit
  immediate `includedFrom.file` is retained as a separate origin edge, but it
  is not a complete transitive include chain. Inherited-file reconstruction,
  full include ancestry and complete source-map records remain open F03 work.
- Direct single-file mode uses C11 / GNU C++11 defaults chosen by source suffix,
  but no longer overrides `_DEFAULT_SOURCE` or forces `_FORTIFY_SOURCE=0`.
  Compilation-database `-x` and standard flags are preserved; an end-to-end
  `.c`-suffix fixture verified a C++11 mode override and define. Explicit `-x`
  and standard-selection flags are still unavailable for direct-file CLI input.
- Compiler builtins are dispatched as intrinsics, not ordinary external calls.
  `__builtin_object_size` now models all four mode results for fixed arrays,
  recognized named-record array fields, and direct unknown pointers; its
  unknown-pointer sentinel follows the result width. Other builtin families
  remain individually unsupported until their semantics and native differential
  tests are implemented. Pointer arithmetic or member access whose provenance
  cannot be proven by the current narrow resolver fails with a diagnostic.
- The default frontend stdout cap is 134,217,728 bytes (128 MiB), configurable
  with `--max-frontend-output-bytes N`. This bounds retained subprocess output,
  not total RSS: Clang itself, the compacted AST, and parsed JSON can multiply
  memory use. A linear preflight scan counts projected JSON values and enforces
  the default 1,000,000-value cap before DOM allocation; configure it with
  `--max-frontend-json-values N`. `--frontend-stats` reports the preflight
  count, compacted AST bytes, and parsed JSON arena payload bytes.

## Latest compiler nullable-function-field gate — 2026-09-15

The translator check used the latest committed Elisa compiler source, not the
installed compiler or the stale isolated stage1 product. A live query confirmed
upstream `main` at `fd2cb3cff470319500db362e5fce2833cbe300de`; a fresh local
stage1 build from that revision has SHA-256
`6cdcdf45fb396d319ce1d0d4e0c5d35e9b3161bd3e81f8d2e594ee60ac76c2a8`, paired
with runtime object SHA-256
`a58618f5358e30e8c19cf1344d47bddd3a7520ee61f83a471222bb0660e48a8f`. The
translator executable used was `build/latest-upstream-f04/elisa-c-transpiler`
(SHA-256 `4b63f0cfc9d8fad1650068c33684745adff58d1566bba848f9ba6b14c967ca89`).

That compiler accepted the translated nullable function-pointer-field fixture,
which the older canonical compiler path had capability-skipped. The generated
Elisa object linked against the matching stage1 runtime; native C and generated
executables both exited 0. The generated source and object hashes are
`d2c7d31ee36ab5ef159afa71300b821a647ecffd27fa3d9b61523f9e60d582a3` and
`36f056e96b846fc7dd7778fb99c16a2f61014a966a2e5ae8f5116a7c5196b171`, in
`/tmp/elisa-latest-compiler-probe.kEbB7z/`. This is a focused capability gate,
not a claim that the full cJSON or upstream corpus suite has passed with this
compiler. A separate stage1 build remained active during this check, so the
nullable-field probe was run first. With system memory still above 50% available,
a single cJSON compile probe was then attempted; it stopped at frontend/type
diagnostics before object generation.

That initial cJSON compile attempt preceded the conditional-expression fix
below. The latest source-fresh stage1 compiler at
`fd2cb3cff470319500db362e5fce2833cbe300de` was then used to rebuild the
translator from the current working tree. The compiler product and matching
runtime hashes remained `6cdcdf45fb396d319ce1d0d4e0c5d35e9b3161bd3e81f8d2e594ee60ac76c2a8`
and `a58618f5358e30e8c19cf1344d47bddd3a7520ee61f83a471222bb0660e48a8f`;
the rebuilt translator is SHA-256
`b9e3d0a18e2cad030e70df822dc9ecb475a65cbce13f0be710bfbafca67b5389`.

The new `nested_conditional_operator.c` regression passes through translation,
compilation, linking and native/generated execution (`exit=0` on both sides).
It verifies nested true/false arms remain explicitly parenthesized and that
known target-aware scalar `sizeof` conditions fold to the selected branch. The
acceptance-manifest run used the exact `fd2cb3…` stage1 product and passed all
four generated artifacts for this case.

With the same rebuilt translator, full cJSON now emits 1,636 lines / 87,294
bytes (SHA-256
`072b9b97fbcbe069896b2febd66f8cebf8fb0cc294d1457f2581ee3bb242eddf`). The
nested-conditional/missing-`else` diagnostics are gone and the float-size
conditional is folded. The latest compiler reports only three remaining
assignments from `u8&?` into `mutable u8&?` at emitted lines 443, 709 and 740:
all are mutable local pointer bindings whose C pointee is `const`. Full cJSON
compilation/linking/runtime parity therefore remains open pending a general
Elisa/compiler distinction between local pointer rebinding and pointee write
capability. No casts that discard `const` were introduced. The focused nested
fixture and cJSON outputs/logs are under
`build/latest-upstream-nested-conditional/`.

Compiler provenance was refreshed once more after that run: the isolated
translator stage1 source is now at `c605b3faa516de7b2f4945a9ac4ccb21d78ae2e0`
while public upstream `main` remains at `fd2cb3cff470319500db362e5fce2833cbe300de`.
An already-built, clean isolated compiler at descendant commit
`ce9e0292f40a6618b7803a4b9b07961d08033a5e` includes both `c605b3f` lowering
optimizations; its stage1 binary SHA-256 is
`9c8e31c9902ba6d0106c9e2eb2cbcdb68992efd3faa264ed8c220e2ab5387682` and its
runtime hash is unchanged at
`a58618f5358e30e8c19cf1344d47bddd3a7520ee61f83a471222bb0660e48a8f`. That
newer product was used to rebuild the translator object (SHA-256
`b935e394d9a2575d5bd4995be248766201556d1912efa717ae43bee4639c5ba9`) and
executable (SHA-256
`b9e3d0a18e2cad030e70df822dc9ecb475a65cbce13f0be710bfbafca67b5389`) in
`build/latest-compiler-ce9e/`. The nested-conditional acceptance case passed
with four artifacts. cJSON was then translated and compiled with the same
`ce9e029` product: its generated Elisa remained byte-identical to the prior
translation (1,636 lines / 87,294 bytes; SHA-256
`072b9b97fbcbe069896b2febd66f8cebf8fb0cc294d1457f2581ee3bb242eddf`) and the
compiler reported the same three readonly-pointee/rebind diagnostics. Thus the
new compiler changes and optimizations are confirmed in the test toolchain,
but do not resolve that language-model gap; full cJSON compilation and runtime
parity remain open. The dedicated translator compiler worktree's own stage1
product is still stale and must be rebuilt before it becomes the default local
test compiler.

## cJSON frontend resource baseline and spool comparison — 2026-09-12

Measured on `testdata/upstream/cJSON/cJSON.c` in the current working tree with
the local stage0-built translator and Homebrew Clang 23.1.1:

| Measurement | Result | Method / interpretation |
| --- | ---: | --- |
| Raw Clang JSON | 22,765,720 bytes | Counted while streaming a fresh successful Clang AST dump into the temporary spool. |
| Capture strategy | Pass | Clang stdout is copied in 8 KiB chunks to `tmpfile()` with the configured byte cap enforced before writes; after successful exit and flush, the file is mapped read-only for raw validation and projection, then unmapped and closed (auto-deleted). |
| Projected AST JSON | 2,099,598 bytes | `--frontend-stats`; projection is about 10.8x smaller than Clang's raw JSON. |
| Parsed JSON arena payload | 12,013,216 bytes | `Arena.used_bytes` after parsing; about 5.7x the projected JSON size, excluding arena block metadata and unused capacity. |
| Projected JSON values | 117,062 | Preflight count before DOM parsing; object keys are excluded. |
| Generated Elisa output | 85,966 bytes | 1,647 emitted lines; identical with and without `--frontend-stats`. |
| Translator maximum RSS, in-memory capture | 70,303,744 bytes | `/usr/bin/time -l`; four cJSON runs of the strict-validation build before spooling. |
| Translator maximum RSS, spooled capture | 53,805,056–53,985,280 bytes | `/usr/bin/time -l`; five cJSON runs with identical output and frontend stats. About 23% lower than the in-memory capture result. |
| Clang max RSS | 53,772,288 bytes | `/usr/bin/time -l` around the equivalent Clang invocation, measured separately. |
| Sampled process-tree RSS, in-memory capture | 83,440–83,600 KiB | Two `ps` samples every 20 ms, summing translator and descendants during cJSON translation. |
| Sampled process-tree RSS, spooled capture | 52,016–52,160 KiB | Three `ps` samples every 20 ms, summing translator and descendants; about 38% lower than the in-memory capture samples. |
| Paired wall time | 4.48 vs. 4.45 s; 4.76 vs. 4.66 s (spooled vs. in-memory) | Two `/usr/bin/time -l` pairs; observed spool overhead ranged from 0.03–0.10 s (about 0.7–2.1%). More corpus measurements are needed. |

The translator and Clang `time -l` measurements are per-process. The process-
tree samples give a simultaneous estimate, but their 20 ms interval can miss
short peaks and does not establish an OS-recorded high-water mark. Spooling
removes the raw AST's large growable heap buffer; the complete file is still
mapped during projection, so OS page residency can vary. The 12 MB parsed-arena
payload remains a concrete amplification point, and the value limit does not
establish a total memory bound. Wider corpus measurements and a streaming
semantic projection remain open F02 work.

## Next verification gates

1. Extend S01 beyond reference/range validation: check declaration/type identity,
   CFG edges, value categories and scope/lifetime ownership, then add deterministic
   IR dumps/pass selection and targeted negative tests for each invariant family.
2. Translate and attempt to compile the Wolf4SDL corpus with the refreshed local
   compiler worktrees; distinguish missing Elisa/backend features from translator
   frontend/lowering failures and keep heavy jobs serial.
3. Extend Clang driver-option coverage and add differential command-context
   checks, while keeping unsupported host command syntaxes explicit.
4. Extend F03's coordinate-only macro origins to canonical physical filenames,
   inherited-file tracking and source-qualified diagnostic/source-map records;
   include response files in future dependency invalidation.
5. Refresh this evidence from a clean, reproducible checkout before treating
   B01 or F01 as complete.

On 2026-09-13, `sh scripts/test.sh --suite all --reuse-build` passed against
fingerprint `138836793721e43dccc950faea3409a8bd905349d1101b17784fd7cd8705a661`
and translator SHA-256
`5b984c6e3657111ddd512e386166420f2c3e2f15fa36a27197b3e1d387f79d2c` after the
enum-storage, integer constant-evaluation and short-circuit-folding changes.
This includes fixture, control-flow, project and upstream suites, unsigned-
enum and arithmetic/shift native differentials, short-circuit side-effect
parity, condition-folding output checks, and the verifier metadata regression.
Invalid-count and signed-negative-right-shift expressions remain unfurled.
cJSON smoke translation and Kilo checks pass; cJSON executable parity remains
capability-skipped because the selected Elisa compiler does not support
nullable function fields. Tests were run serially; sampled memory stayed
between 76% and 82% free with zero throttled pages during the longest C++ map
fixture. A transient 40%-free reading during the final small linker step also
showed zero throttled pages, and the full run completed successfully.

## C `const` emission and fortified object-size parity — 2026-09-15

The current isolated stage1 worktree is pinned at `c605b3faa516de7b2f4945a9ac4ccb21d78ae2e0`, including the shared typed-scalar lowering and duplicate-EDIR-fallback optimizations. The local stage1 product used for this check is
`/private/tmp/elisac-transpiler-rebuild.P475UO/elisac-stage1-binding` (SHA-256
`f43d50bc002c09447572fc83572cc8883d4197f746e30d2e72bd020d824d4a96`) with
the matching isolated runtime object (SHA-256
`4876d2943cc9b2999a812c9cabab34366cfee81866d125f3250651bd3739ea96`). No
installed Elisa compiler was used.

The translator rebuilt with that compiler is
`/private/tmp/elisa-transpiler-stage1-rebuild.cxS8Jy/elisa-c-transpiler`
(SHA-256 `35635e53923e4e106c63ce4fd2104233ef87d65bab2a4897dacadb8722decff1`).
Its generic AST compile-time integer evaluator correctly evaluates Clang's
fortified-header object-size mode expression `2 > 1 ? 1 : 0`; the former
first-literal walk incorrectly selected `2` and emitted a zero bound. Unknown
maximum object sizes now emit the target-width `SIZE_MAX`, while minimum-mode
queries still emit zero. The evaluator is generic and is not keyed to cJSON or
any particular library.

Fresh cJSON translation produced 2,840 lines / 150,194 bytes (SHA-256
`1cfcf0b606695073883c6f0d19f7e63524f04dca540a25e7b328eb1d191ffeb2`). It
contains real fields for `C_error`, `Parse_buffer` and `Printbuffer`; all
fortified `__builtin___strcpy_chk` calls use the correct unknown-size sentinel
`18446744073709551615`; source C `const` is not emitted as an Elisa
qualifier (the generated `json` and `readonly` bindings use ordinary Elisa
immutability). The generated program compiled with zero diagnostics using the
same isolated stage1 compiler, linked against its matching runtime, and printed
`{"name":"elisa","items":[1,true,null]}` with exit 0, matching the native
cJSON smoke executable. This closes the previously observed Darwin
`__chk_fail_overflow` runtime trap for the supported object-size provenance.

## C `const` binding and direct static-global initialization — 2026-09-15

The C-`const` rule is now explicit and generic: Elisa bindings are immutable by
default, so an object-level C qualifier is omitted from the emitted spelling.
`const int x` becomes `x: i32`; it does not become an Elisa `const` keyword or a
mutable zeroed binding. Pointer binding mutability and pointee write capability
remain separate: a rebindable `const T *p` can receive `mutable p:` only when
the lowered C body actually reassigns the pointer slot, while `T * const p`
keeps the ordinary binding spelling and retains a writable reference capability.

The isolated optimized stage1 compiler used for this check is the local
`codex/transpiler-local-stage1` worktree at `c605b3faa516de7b2f4945a9ac4ccb21d78ae2e0`.
The rebuilt translator is
`/private/tmp/elisa-transpiler-stage1-rebuild.const.Nwp1dj/elisa-c-transpiler`
(SHA-256 `ced87407dcd8c4b6f43cc52fdf054f94e16c8caa57a41d47e823e0c955da2ca0`).
Its matching local stage1 runtime was used for every generated compile/link
check; the installed compiler was not consulted.

The focused source fixture `testdata/fixtures/const_bindings.c` translates with
no diagnostics and emits these generic forms:

```elisa
scalar: i32 = 3
fixed: mutable i32&? = &value
readonly: i32&? = &scalar
```

No generated declaration contains a C `const` qualifier. The native and
generated executables both pass. The project fixture
`testdata/fixtures/project_cpp_internal_const_compile_commands.json` likewise
emits immutable constant globals with direct initializers (`= 17` and `= 29`)
and no runtime assignment; both normal and generated projects compile, link and
return the native result. This proves the direct path for static scalar globals
and the ordinary-binding policy, while pointer/address static initializers and
full per-reference-layer capability remain separate open work.

## C `const` pointer-parameter capability correction — 2026-09-15

The first direct-global implementation exposed one generic boundary error in a
full cJSON compile: a C parameter written `T * const p` was treated as entirely
readonly because the parameter binding qualifier and pointee capability were
collapsed into one predicate. The emitter now treats them independently. The
binding remains ordinary Elisa immutability, while the parameter type carries a
writable reference when the C pointee is writable. The focused assertion now
requires `fixed: mutable i32&?` for the `int * const fixed` parameter in
`testdata/fixtures/const_bindings.c`.

With the isolated optimized stage1 compiler
`f43d50bc002c09447572fc83572cc8883d4197f746e30d2e72bd020d824d4a96`, matching
runtime `4876d2943cc9b2999a812c9cabab34366cfee81866d125f3250651bd3739ea96`,
and rebuilt translator
`aebef0580f7dd0b1517be858a3b24ecffce54800a843cf032cafa1a98b70e22a`, full
`cjson_smoke.c` translates to 2,836 lines / 149,947 bytes. It contains no
emitted C `const` declaration/type qualifier, compiles and links with zero
diagnostics, and its output matches native execution:
`{"name":"elisa","items":[1,true,null]}`.

The storage-duration regression `testdata/fixtures/static_local.c` also passes
with the same translator/compiler/runtime pair. The emitted module has one
`global mutable value: i32 = 4`, no residual `static` syntax, and three calls
observe the persistent sequence 7, 10, 13 exactly as native C does. This proves
the current C static-local promotion for constant initialization; cross-unit
identity collisions and C++ dynamically initialized local statics remain open.

## Native Elisa slice endpoint probe — 2026-09-15

The translator must not replace `sview("text", 0, -1)` with Elisa slice
syntax until the selected compiler gives the slice operator the same `-1`
endpoint meaning. The isolated stage1 compiler accepts `"arg8"[0:4]` and the
probe returns length `4`, but it also accepts `"arg8"[0:-1]` and the resulting
view reports length `-1`; it does not apply the runtime `sview` sentinel rule.
The probe therefore fails its semantic check even though parsing succeeds.
No translator output was changed. This is a compiler/runtime contract gap, not
a reason to emit shorter but incorrect Elisa; the slice-recovery item remains
open until the compiler establishes clamped/sentinel endpoint semantics and a
positive empty/non-ASCII/lifetime regression passes.

## C `const` aggregate lowering — 2026-09-15

The generic aggregate fixture `testdata/fixtures/const_aggregates.c` now
passes translation, isolated stage1 compilation, native/generated linking and
execution. Its `static const int[3]` becomes the ordinary immutable Elisa
global `const_numbers: array[i32, 3]`, and its `static const struct` becomes an
ordinary immutable `Const_configuration` global with a direct aggregate
initializer. Neither emitted declaration contains a C `const` qualifier.

The fixture also covers the important boundary case `static const char
*const_names[2]`: because Elisa's startup path must populate the pointer table,
that storage is emitted as `global mutable const_names ... = zeroed` and filled
once by the generic generated initializer. The mutability is therefore an
implementation requirement for the aggregate storage, not a reintroduction of
C `const` syntax. Native and generated programs both exit 0. This closes the
direct scalar/array/record aggregate case while dynamic address initializers,
cross-unit static identity and per-reference-layer capability remain open.

## Isolated stage1 binding-contract rebuild — 2026-09-15

The local stage1 source received the generic readonly-reference correction in
`src/semantic/check_readonly_ref.elisa`: a parameter written `mutable p: T&`
is excluded from the write-through-readonly set, so its binding slot may be
reassigned while the referenced `T` remains read-only. This is the Elisa
contract required by C `const T *p`; it does not add a C-style `const` keyword.

The two older stage0 products in the stage0 worktree could not seed the current
optimized stage1 source, so the product was rebuilt through the existing
optimized stage1 compiler and linked with the isolated matching runtime. The
resulting stage1 compiler is
`/private/tmp/elisac-stage1-selfhost-const.6fbtda/elisac-stage1` (SHA-256
`e80e33b2fe1a1f17930396a965a863cbf01de6ba0a1fc9303962e473863944db`), with
runtime SHA-256
`4876d2943cc9b2999a812c9cabab34366cfee81866d125f3250651bd3739ea96`.
`test/repro/parameter_binding_qualifier.elisa` compiles, links and returns 0,
proving the binding/pointee distinction. The translator rebuilt from this
product is
`/private/tmp/elisa-transpiler-stage1-const-contract.4d8WTo/elisa-c-transpiler`
(SHA-256 `aebef0580f7dd0b1517be858a3b24ecffce54800a843cf032cafa1a98b70e22a`).

With that pair, cJSON still emits 2,836 lines / 149,947 bytes (SHA-256
`5c5438d785364f4be223f64610c8f3cb471ba85fa37277479bc3771d2ed234d3`),
compiles with zero diagnostics, and produces the same
`{"name":"elisa","items":[1,true,null]}` output as native C. The
stage0 seed mismatch remains an isolated compiler-bootstrap maintenance item;
the translator verification itself uses the fresh self-hosted stage1 product
and its matching runtime, never an installed compiler.

## Generic JSON traversal de-duplication — 2026-09-15

The dependency type-index walker and the source/dependency-fact walker now
return the end cursor of the subtree they have already traversed. Their parent
array/object loops reuse that cursor instead of calling the generic JSON
skipper over the same child a second time. The projection pass also retains
the first pass's top-level source-state facts, so it does not rescan every
translation-unit child merely to rediscover its source location and inherited
provenance. Non-object values still use the generic skipper as a safe advancing
fallback, so arrays containing primitive JSON values cannot stall the walkers.

This is generic frontend work; it contains no cJSON- or Wolf-specific branch.
The isolated self-hosted stage1 compiler used here is
`/private/tmp/elisac-stage1-selfhost-const.6fbtda/elisac-stage1` (SHA-256
`e80e33b2fe1a1f17930396a965a863cbf01de6ba0a1fc9303962e473863944db`) with
matching runtime SHA-256
`4876d2943cc9b2999a812c9cabab34366cfee81866d125f3250651bd3739ea96`.

The resulting translator is
`/private/tmp/elisa-transpiler-topindex.BbldAR/elisa-c-transpiler` (SHA-256
`71aed76a38dc7cdecf4321e87f98fb9881de864b3ca0a080cd9fc660309a3fea`). A
fresh cJSON smoke translation reports:

```text
raw_json_bytes=28834124
projected_json_bytes=5278616
parsed_arena_bytes=29347480
projected_json_values=278954
generated_lines=2836
generated_bytes=149947
```

The generated cJSON executable compiles, links and prints the same
`{"name":"elisa","items":[1,true,null]}` output as native C. The generic
`const_aggregates.c` regression also compiles, links and exits 0 with the
ordinary immutable Elisa binding policy.

For Wolf4SDL, a bounded project-mode probe of the vendored
`testdata/upstream/wolf4sdl/wl_menu.cpp` reaches the configured frontend guard
after about 141.5 seconds and roughly 332 MiB resident memory, reporting:

```text
projected AST exceeded --max-frontend-json-values 1000000
```

It produced no partial Elisa module and no crash. This is useful progress in
diagnostic safety, but it is not a Wolf translation success: the next Wolf
work is to inventory why this unit retains more than the current value budget
and either reduce the generic projection or raise the budget only after a
calibrated memory/latency policy.

## Wolf projection and mixed-width compound-assignment fix — 2026-09-15

The large-unit projection was improved generically by treating `LinkageSpecDecl`
as a wrapper rather than retaining every wrapper in a C++ translation unit.
Source-location and declaration-dependency evidence still retains a wrapper
when it owns a needed declaration or referenced child. Wolf4SDL's bounded
`wl_menu.cpp` AST contains 1,048 such unused top-level wrappers; dropping them
removed the earlier one-million projected-value rejection without increasing
the configured guard or adding a Wolf-specific name rule.

The emitter also now applies C's compound-assignment conversion at the
destination ABI boundary. Direct statements and value-preserving generated
helpers convert the RHS to the destination scalar width and signedness before
emitting Elisa `op=`. This is required because C promotes operands while Elisa
requires the backend overflow intrinsic operands to have one concrete type.
The regression `testdata/fixtures/compound_widths.c` covers `i32 += i16`,
`i32 += u8`, `u8 += i32`, record fields and unsigned wraparound; isolated stage1
translation, compilation, linking and native/generated execution agree. The
existing sequencing and conditional-place fixtures continue to pass.

Using isolated stage1
`/private/tmp/elisac-stage1-selfhost-const.6fbtda/elisac-stage1` (SHA-256
`e80e33b2fe1a1f17930396a965a863cbf01de6ba0a1fc9303962e473863944db`) and its
matching runtime (SHA-256
`4876d2943cc9b2999a812c9cabab34366cfee81866d125f3250651bd3739ea96`), the
fresh translator
`/private/tmp/elisa-transpiler-compound-fix.QZQozv/elisa-c-transpiler` (SHA-256
`96ca5089d61a391f1f799154a1816b93d1ada8172e425ba86cd7c398c1b05232`) emits:

```text
elapsed=185.23s
peak_translator_rss≈335 MiB
wl_menu.elisa=6447 lines / 305346 bytes
externs=140
functions=113
records=44
globals=40
```

The generated object compiles successfully with stage1 at both `-O0` and
`-O2`. The `-O0` object is 329 KB (SHA-256
`b642739a204d4d5e498a5d7be11b5127ca425c192d98e6baa358c0c6c6d26656`) and the
`-O2` object is 154 KB (SHA-256
`f16b1b2369bfca1b34c5480912b32813de617b8e91d401968915ab03274b1dd2`). The
compiler reports only these remaining capability warnings:

```text
VL_LatchToScreenScaledCoord__inline_3@10793 (field expression)
VL_LatchToScreen__inline_3@10800 (field expression)
IN_GetScanName@14216 (index expression)
```

These are explicit backend body declines, not a translator crash or invalid
LLVM IR. Full Wolf linking, startup and runtime gameplay remain open until the
three bodies and their external SDL/game dependencies are supported or
deliberately isolated behind a verified compatibility boundary.

## External provenance closure regression — 2026-09-15

The transitive-declaration regression exposed a generic provenance edge in the
projection filter. Clang may put `includedFrom: <main-file>` on a nested node
inside an external header declaration, and it may omit `loc.file` on later
header siblings. The previous classifier allowed that nested marker to
promote the node to source ownership, which could collect an unused header
type name or retain an unrelated external record. The classifier now keeps an
explicit external ancestor authoritative, treats included-from-only locations
as external, and lets a direct file match re-establish source ownership for a
later top-level source sibling. The same rule is applied to the final
retention predicate, so location evidence cannot bypass the provenance state.

The focused checks pass with the isolated stage1 compiler and matching runtime:

```text
transitive declaration closure check OK (hidden typedef chain, C tag collision; compile/runtime parity)
declaration dependency closure check OK (id-based; not location/isUsed dependent)
unqualified C++ record-layout check OK (implicit-name filtering, ambiguity rejection, compile/runtime parity)
```

This remains generic Clang-schema handling; no cJSON, Wolf, header name or
external-library special case was added. Additional Clang versions and
provenance serializations remain open under F02.

## Latest stage1 ABI-boundary verification — 2026-09-15

The translator was rebuilt from the current Elisa compiler worktree using the
explicit local stage1 product, never the installed compiler:

- stage1 product: `../Elisa-compiler/bin/elisac-stage1`, compiler commit
  `565ccb2fd585d03f94457185376f526e1930b1cb`, SHA-256
  `2324bf11c796433ac2868b4dc5d4c8ab26f4e471e30dfafb3d3067a1f159dd17`;
- matching runtime: `../Elisa-compiler/build/runtime/elisacore_runtime.o`,
  SHA-256 `85f1107eef00a7dd903e511df366b8b6cade4d8573cf0478f1de91604ea5beb9`;
- generated translator: `build/elisa-c-transpiler`, SHA-256
  `dfcc1a781767c83a7efef436d16190c53b970b5294350383e1dbab6ca9318546`.

The C++ `unordered_map` adapter regression exposed a generic mixed-width
comparison boundary: a C++ method result was emitted as `i32` while a raw
Elisa integer literal reached LLVM as `i64`. The emitter now materializes an
integer/character literal at the selected ABI width only when it is the
literal side of a comparison with a call result. Ordinary variable-based
expressions remain clean (`value != 7`), so the fix does not spread casts
through idiomatic output. `cpp_unordered_map_find.cpp` now compiles, links and
exits 0 with native and generated programs; its emitted checks use
`(7).i32()`/`(42).i32()` only at the method-result boundary.

C object-level `const` follows Elisa's default immutability model: `const T`
emits an ordinary immutable Elisa binding without a generated `const` keyword.
Pointer-slot rebinding and pointee write capability remain independently
represented by Elisa's existing `mutable` positions. The const binding,
aggregate and const-cast fixture checks use indentation-tolerant shape
assertions so they test semantics rather than a backend's effect-block
formatting. The CFG/goto hoisting path now applies the same boundary: top-level
`const` remains ordinary immutable after hoisting, while non-const hoisted
locals retain the writable representation required by later-block assignments.
The fresh-stage1 `control-flow` suite and focused const fixtures pass native /
generated parity, and none of those outputs contain a C `const` binding
qualifier.

The bounded semantic acceptance manifest completed with 13/13 cases passing
under this stage1/runtime pair, and the transitive declaration, unqualified
layout, missing-dependency and Clang-failure checks passed. The extended
header-heavy fixture tail was not used as a completion claim: the host sent
SIGTERM after several minutes while repeated C++ negative cases were still
running. No translator or compiler crash, invalid LLVM result, or unbounded
RSS event was observed in this run. The known stage1 capability skip for the
`offset-of` compiler-builtin executable probe remains explicit.

The generic non-null helper was then hardened without adding a C/C++-specific
special case. Its null branch now calls `panic(...)` directly; returning
`zeroed` from a `T&` helper could fabricate a valid-looking reference. The
isolated stage1 backend accepts this direct generic conditional panic but
declines the nested `trusted:` block form, so the emitter uses the simpler form
while preserving the same generic helper names and signatures. A bounded
manifest rerun with the main stage1 product and matching runtime passed
`simple`, `readonly_nonnull_helper`, `c_array_to_pointer_decay`, and
`c_record_pointer_call_arguments` (4/4, native/generated parity). The complete
13-case bounded manifest was then rerun with the same exact configuration and
passed 13/13, including the new direct-panic shape assertion. The test harness
also now derives its explicit stage1 runtime link input from `ELISAC_RUNTIME`
when supplied, preventing a second stale-worktree runtime from being appended
by legacy direct-link checks.

## Latest lexical-name recovery verification — 2026-09-15

Nested C shadowing exposed a generic emission bug: the previous declaration
stack could mistake an inner `int value` for a replay of the outer binding and
emit `value <- ...`. The emitter now tracks lexical declaration-scope starts,
creates a deterministic source-name alias only for a nested collision, resolves
the newest alias first in expressions, and restores both aliases and bindings
at scope exit. `keyword_identifiers.c` verifies the shared keyword boundary
(`match`/`module` become `c_match`/`c_module`), while `nested_shadowing.c`
verifies the output spelling and native/generated execution parity with the
isolated stage1 compiler and its matching runtime.

The follow-up `for_scope_shadowing.c` regression found that the first lexical
fix was incomplete: mutability inference still scanned assignments by source
spelling and counted the loop's shadowed `index += 1` as an outer write. The
shared analysis now carries the target declaration index and scope-local
binding state through blocks, `for` scopes, branches, loops and switches. The
generated output keeps the outer `index` immutable and emits only the loop
binding as mutable; native and generated programs both exit 0.

## Refreshed local bootstrap pair — 2026-09-15

The default translator test path now selects the newest isolated compiler pair:

- stage0 worktree: `../elisa-transpiler-worktrees/stage0-latest`, commit
  `3a5520d8fd56b86c430f39518a261e9030fa72ec`, local product SHA-256
  `975b1e8e1283abdf5068447d10fc1625d6e2eb59c8313af28e7b57866f39710f`;
- stage1 worktree: `../elisa-transpiler-worktrees/transpiler`, commit
  `d6a693c0f724c05f7b71418658dd8bda95ba73b3`, local product SHA-256
  `f781d4a92bc0749393eeed29373d5855ff59c56e23824cdf1c2dd536e0f68886`;
- matching stage1 runtime SHA-256:
  `85f1107eef00a7dd903e511df366b8b6cade4d8573cf0478f1de91604ea5beb9`.

The former `stage0` worktree is retained as a legacy checkout, but it cannot
seed this stage1 revision because it predates the current parser syntax. The
new `stage0-latest` worktree was created from the refreshed `structpy-tree`
checkout, and successfully seeded the local stage1 product and matching
runtime. With that pair, `sh scripts/test.sh --suite control-flow
--reuse-build` rebuilt `build/elisa-c-transpiler` (SHA-256
`1b9285516b9ac92c1e39514754810c2c79a8364ee79c85daaea9324be6330548`) and
passed the frontend, depth, declaration-closure, missing-dependency,
unqualified-layout and control-flow checks. The build still emits a large
set of non-fatal missing-effect-grant warnings in existing translator helpers;
warning cleanup is a separate plan item and is not treated as a test failure.

## Rewrite accounting verification — 2026-09-15

The idiomatic emitter now records applied typed-IR readability rewrites in a
small per-translation diagnostic counter: redundant casts, identity binary
operations and safe integer constant folds. `--explain-rewrites` writes one
machine-readable summary to stderr and leaves generated Elisa stdout untouched.
For `testdata/fixtures/integer_constant_semantics.c`, the normal and explained
outputs compare byte-for-byte and the report is:

```text
rewrite-stats source=testdata/fixtures/integer_constant_semantics.c redundant_casts=0 identity_binaries=0 integer_folds=3 constant_conditions=1 boolean_predicates=0 conditional_prunes=0
```

The focused control-flow suite passes with the refreshed isolated compiler
pair. This is applied-rule accounting, not yet a complete proof/decline
explanation report; unsafe algebraic rewrites and unsupported proof reasons
remain open under I06/P06.

## Raw Clang AST schema guard — 2026-09-15

The frontend now validates the raw JSON envelope before projection. The
supported root contract is a JSON object whose first `kind` value is the
string `TranslationUnitDecl` and whose first `inner` value is an array. This
check is deliberately limited to the envelope that projection unconditionally
consumes; nested declaration fields remain optional and version-tolerant.

Five syntax-valid fake-frontend roots were rejected with no generated stdout:
non-object root, missing `kind`, wrong `kind`, missing `inner`, and non-array
`inner`. Each diagnostic names the violated field and source, for example:

```text
elisa-c-transpiler: Clang AST schema violation: missing-required-field:root.kind while processing testdata/fixtures/simple.c
```

The bounded control-flow suite passed with the isolated latest compiler pair;
the existing malformed-JSON, depth, failure-status and projection tests also
remain green.

## Mode-gated readability rewrites and writable address exposure — 2026-09-15

Optional readability rewrites now have an explicit pass-selection gate. The
default `--idiomatic` mode may apply verified redundant-cast removal, identity
operations, safe integer folds, constant-condition simplification,
boolean-predicate cleanup and constant conditional-arm pruning. `--fidelity`
keeps the shared semantic lowering and verifier, but retains source-level
expression structure for those optional rewrites. The constant-fold fixture
compiled and ran successfully in both modes: idiomatic output emits
`return 20`, while fidelity output retains `return ((2 + 3) * 4)`.

Mutability inference also treats a writable address escaping from a local as a
binding-capability fact. This fixes the generic C case where an otherwise
directly-unmodified object is later modified through `&object`; read-only
`const` pointees do not gain that capability. The pointer-qualifier fixture
compiled and ran with matching native/generated exit status using the isolated
stage0 compiler.

The local compiler pair was recreated from the current main repositories after
the previous worktree directory was found empty:

- stage0 source commit `3a5520d8fd56b86c430f39518a261e9030fa72ec`, product SHA-256
  `975b1e8e1283abdf5068447d10fc1625d6e2eb59c8313af28e7b57866f39710f`;
- stage1 source commit `d6a693c0f724c05f7b71418658dd8bda95ba73b3`, product SHA-256
  `f781d4a92bc0749393eeed29373d5855ff59c56e23824cdf1c2dd536e0f68886`;
- matching stage1 runtime SHA-256
  `85f1107eef00a7dd903e511df366b8b6cade4d8573cf0478f1de91604ea5beb9`.

The focused control-flow suite passed with the rebuilt translator (SHA-256
`1b9285516b9ac92c1e39514754810c2c79a8364ee79c85daaea9324be6330548`). The
manifest fixtures also passed, including enum integer semantics after enum
conversion boundaries were made nominally typed for the latest compiler.

## Header-heavy AST projection scan — 2026-09-15

The projection filter now treats enum retention as a declaration-containment
query. It checks a node's direct `kind`/reference fields and follows only
Clang's `inner` arrays, instead of recursively searching location and type
metadata. The query is also disabled when the source walk found no enum
evidence; declaration-ID dependency closure remains the retention mechanism
for referenced external declarations.

On the real-Clang `cpp_unordered_map_unsupported.cpp` regression, which emits a
roughly 113 MiB AST because of `<unordered_map>`, translation now reaches the
three generic unsupported-policy diagnostics in about 13 seconds on the local
arm64 host. Generated stdout remains empty. The test remains intentionally
library-policy based only for the translator-owned C++ adapter and does not
introduce a source-program-name or cJSON-specific rule.

## Transactional project output and C++ overload export adapters — 2026-09-16

Project-mode module and manifest output is now written to transaction-specific
temporary names. A completed translation publishes each module and publishes
the manifest last; existing outputs are moved to exact per-transaction backup
names and restored if publication fails. A bounded regression uses a successful
first unit followed by a Clang failure and verifies that the previous module and
manifest remain byte-for-byte unchanged, stdout stays empty, and no temporary
or backup files remain.

The regression also caught and fixed a NUL-termination error in module backup
paths: appending `.backup` after the path's terminator caused the old module to
overwrite the new staged module on reruns. A direct rerun probe now replaces an
existing generated module correctly.

The project C++ overload fixture exposed a second generic boundary issue. Elisa
export aliases resolve a target by source spelling and arity, which is ambiguous
for same-arity C++ overloads. The translator now emits a private typed adapter
for only those ambiguous wrapper targets; the adapter calls the overloaded source
name with the exact typed parameters, while the native ABI wrapper targets the
unique adapter. The project C++ overload output compiles, links, and returns the
same result as the native program under the isolated local stage1 compiler.

## Explicit support roots and demand-driven project helpers — 2026-09-16

The translator now accepts `--cpp-lib-dir DIR --elisa-std-dir DIR` as a paired
explicit configuration. In that mode, generated projects include the selected
runtime and collections files plus the include-free
`cpp_lib/unordered_map_core.elisa`; the old repository-local wrapper remains
available for local development. A regression copies the generated C++ project
to a separate output directory and compiles/runs it with the isolated stage1
compiler, proving that the generated project no longer follows the translator's
build-relative compatibility wrapper.

Project manifests also aggregate runtime helper requirements from each translated
unit. `elisa_nonnull`, readonly-nonnull and variadic runtime declarations are
emitted once and only when required; the C++ map fixture needs none of these
translator helpers, while the external-pointer project fixture verifies that a
needed nonnull helper is retained without emitting the other families.

Project publication now snapshots the prior manifest before replacing it. After
the new manifest is safely published, cleanup accepts only the translator's
exact generator marker and safe single-component `.elisa` module includes from
that prior manifest. It removes stale generated modules that are absent from
the new source set, while leaving user-owned files and malformed/non-generated
manifests untouched. A direct two-generation probe and the project suite cover
this ownership boundary. The focused control-flow and project suites passed
after these changes. The selected support roots are still external dependencies;
fully vendored release assets remain an open roadmap item.

## CFG empty-edge threading — 2026-09-16

Residual CFG emission now threads through unlabeled empty jump-only blocks at
the transfer edge. The walk is bounded and stops at labels, non-empty blocks,
invalid targets or cycles, so source-visible jump entries and malformed graphs
remain fail-closed. Existing goto/switch fixtures were rebuilt and passed
native/generated control-flow parity with the isolated compiler pair.

## Effectful switch selectors — 2026-09-16

The generic switch lowering now detects calls, assignments, increment/decrement
sequences, side-effecting indexed accesses and other non-pure selector nodes.
Those selectors are evaluated into a deterministic collision-checked temporary
before `match`; pure selectors retain the direct `match expression` form. The
same rule is applied inside localized CFG switch regions. This is a translator
compatibility guard for the current Elisa backend, whose inline match lowering
can otherwise evaluate a selector once per arm. `switch_selector_once.c` now
checks the generated temporary shape and passes native/generated parity, while
the control-flow and fixture suites remain green.

## Source-linked rewrite explanations — 2026-10-03

`--explain-rewrites` now emits opt-in, machine-readable applied/declined events
to stderr with half-open source byte ranges. Applied events identify the proof
category; declined events state why a candidate rewrite was not safe. Events
are recorded both when constant conditionals are pruned during typed lowering
and when rewrites are selected at emission, including source-node origins for
the early-lowered case. The new generic C fixture covers pure identity/folding,
effectful and volatile declines, constant-arm pruning through both paths, and
conditional side effects. It confirms explanation mode leaves generated Elisa
stdout byte-identical.

Validation passed with an isolated Stage1 product rebuilt after the shared seed
lock cleared. Compiler source HEAD was `9486c95679e635e4d77c8a406b35bbcdf622a5e6`;
the compiler worktree also contained uncommitted updates in
`src/semantic/check_region_storage_stability.elisa`,
`src/semantic/check_type_path_separator.elisa`, and
`test/parity/diagnostics_smoke.sh`, so the product is identified by artifact
hash as well as commit. Stage1 binary SHA-256:
`850abebe3365da674109a5499b17e57f136d118cdee7796e96dda2bc2eef651b`;
matching runtime SHA-256:
`424aaf9f49da71988809232ce658234ce97acf470ff02ab663e92f6fa09b1442`;
translator executable SHA-256:
`81ded2058c2fd821236c156bea02648b21bf7c3abff39fc37bd37f47cb75b801`.
The translator object build peaked at 322864 KiB process-group RSS under a
1048576-KiB cap. `scripts/test_rewrite_explanations.py`,
`scripts/test_diagnostics_json.py`, `scripts/test_source_map.py`, and
`scripts/test_clang_failure.sh` passed;
`run_fixture_manifest.py --case rewrite_explanations` passed native/generated
compile, link, and runtime parity (four artifacts). Static line-limit, diff,
shell-syntax, manifest-JSON, and fixture-runner unit checks also passed.

This closes the source-map origin/emission-span and rewrite-explanation items
in P06. The broader unsupported-construct report requirements remain open; no
full translator or upstream acceptance suite was run for this slice.

## Current isolated compiler reconciliation and guarded Stage1 seed — 2026-10-02

The isolated Stage0 worktree is fast-forwarded to its current local `main`
revision `a98ef922`. Its separately built Stage0 executable is
`../elisa-transpiler-worktrees/stage0-latest/compiler/bin/elisac-local-mainrefresh-2026-10-02`
(SHA-256 `aa1c56d72a3b8c7243596ae6cf1f15bf8a4f59eff8f7e7d6b099e40067505c42`).
The isolated Stage1 worktree now merges latest committed compiler main
`bb5a13cf` at `9e1ddcbc`. One overlap in
`src/semantic/check_local_view_return_escape.elisa` was manually reconciled to
keep main's expanded view-origin summaries and enum/lambda cases while retaining
the isolated move-of-local and container-root escape safeguards. The main
compiler checkout remains untouched.

All 36 tracked working-tree changes and 11 untracked test/fixture files from
the main compiler checkout were imported into the isolated Stage1 worktree.
Shared untracked files compare byte-for-byte; the one remaining source-file
difference in `src/backend/codegen_export_aliases.elisa` is the isolated
marker-pair guard, which is intentionally retained. Two Git stashes remain as
recovery snapshots of the isolated Stage1 edits before synchronization; neither
was dropped.

A source-fresh Stage1 seed was attempted only after confirming the host-wide and
worktree-local seed locks were free, using the refreshed Stage0 executable,
`-O3`, the seed script's existing 4-GiB child RSS limit, the existing 6-GiB
process-group RSS cap, and a 900-second deadline. The bounded runner stopped
the owned process group at a 4,669,440-KiB physical-footprint safety threshold;
the observed peak was 4,672,374 KiB physical footprint and 3,051,056 KiB RSS.
The Stage0 compiler itself was at 1,992,064 KiB RSS when the runner reported
termination. System memory headroom had declined to 44% and recovered to 47%
after cleanup; no memory-throttled pages were reported. Both seed locks and
PID-specific temporary outputs were removed. The old Stage1 product remains
SHA-256 `df31f9d00a8a3ffbb61302d02d05e00a7cc5eb23e7f03d36bb6fb0cedad4e369`,
and its runtime remains SHA-256
`6a8d933dc5d9e77d491de34225ca21b7a37c117182e1e0e14d3a3e20ff6afc5e`; therefore
there is still no source-fresh Stage1/runtime pair. No translator build or
compiler-dependent fixture result is claimed from this attempt. Keep the
existing ceiling; the next meaningful route is lowering bootstrap memory or
waiting for a window with more sustained system headroom.

## P06 project source-map hardening — 2026-10-02

Each unit's source table deduplicates physical aliases and streams file contents
in fixed-size chunks; project mode accumulates the byte budget across units.
The canonical translation unit is included and hashed even when the AST emits
no source-origin spans (for example, a macro-only file).
Per-unit JSON is copied to permanent storage before the short-lived translation
region ends, then the bounded aggregate is assembled after all unit regions have
closed. The project output-size check reserves its closing JSON bytes before
accepting each unit. Project publication rejects a source-map destination that
resolves through a symlink to an input source, and map-generation failures now
remove modules staged by earlier units. The end-to-end harness covers two-unit
aggregation, shared macro-header origins, symlink and generated-output
collision refusal, and leftover staging cleanup after a failed generation.

Static checks pass: `git diff --check`, the 600-line source gate, shell syntax,
and Python syntax. Elisa compilation and executable fixture runs are deferred
until the shared Stage1 seed/build lock is available and host memory recovers;
the last read showed less than 1% free pages and active unrelated workloads.
The main compiler checkout remains at `bb5a13cf` with 47 dirty paths and the
isolated translator compiler at `e8f7469e` with 30 dirty paths, so those changes
must still be reconciled without discarding either worktree before claiming a
latest-compiler validation.

## Structured unsupported-diagnostic context — 2026-10-02 (in progress)

Typed diagnostics now carry the rejected Clang node's qualified type and a
separate required-capability field. Unsupported constructs derive their semantic
category from the Clang AST kind (expression, statement, declaration, or
frontend), while the specific sequencing/layout/ABI blocker is kept in
`required_capability`. Generic unsupported reports leave that field empty
rather than claiming a specific missing feature. The machine-readable schema is
version 3; human-readable and typed-IR-dump diagnostics include capability
context when known. Diagnostics also carry half-open Clang source byte ranges,
using macro expansion offsets for the primary span when present. Fixtures assert
the semantic category, capability, relevant type, and exact source slice for
the effectful conditional-record case. A focused Elisa
unit harness now covers expression, statement, declaration, C++ initializer/base
specifier, and unknown-kind classification; another directly probes normal,
macro-expansion, fallback-token-length and missing source-range offsets.
Typed IR now has optional expression/statement origin side tables, and lowering
populates them only when capture is enabled so normal translations do not pay
the per-node memory cost. Raw nested statement spans now carry copied source
and macro-origin metadata plus synthesized-node reasons in `TypedTranslation`.
An opt-in formatting path remaps their positions through final whitespace and
line wrapping, but it is not compiler-verified or enabled by the CLI.
Source-content hashes and end-to-end generated/source maps remain open.
Source line limits, fixture shell
syntax, stale-expectation search, and `git diff --check` pass. Elisa compilation
and fixture execution remain pending: current host memory pressure is severe
and another task has a compiler process active, so the shared Stage1 seed is
being left untouched until a safe window. This is an incremental P06
implementation, not source-map coverage or completion of actionable reports.

## Full-width unsigned integer constant folding — 2026-10-01 (in progress)

The typed constant evaluator now parses integer magnitudes across the complete
`uint64` range and stores upper-half values as their original `i64` bit pattern.
It evaluates unsigned arithmetic, division/remainder, shifts, and comparisons
using `u64` operations, then normalizes narrower unsigned results at their C
source width. Signed 64-bit add/subtract/multiply folds now guard host overflow;
division and remainder retain `MIN / -1` rather than evaluating undefined
behavior. The emitter restores unsigned Elisa typing when a folded `uint64`
result's bit pattern is negative. Out-of-range unsigned-to-signed casts remain
unfolded so the selected Clang target defines their implementation-specific
result, including casts from upper-half `uint64` values to narrower signed
types. Regressions now cover `(int)UINT64_MAX`, `(int)0x80000000ULL`,
`(short)UINT64_MAX`, and the representable `(int)0x7fffffffULL` boundary.
Native Clang execution passes with `-Wall -Wextra -Werror` and under UBSan,
and the source/shell checks pass. Generated Elisa compilation, shape
assertions and runtime parity remain pending a fresh Stage1/compiler-runtime
pair. Exported but uncalled probes also retain `i64` max-add, min-subtract,
max-multiply, `MIN / -1` and `MIN % -1` in the AST; since those executions are
undefined in C, structural output assertions—not runtime calls—must prove they
remain unfurled. The fixture now has uncalled 32-bit and 64-bit probes for both
division and remainder. Clang's intentional-overflow diagnostic is disabled
only for this fixture.

A follow-up width audit found that the evaluator retained `MIN % -1` only at
the host `i64` width, although C makes the remainder undefined whenever the
corresponding quotient is unrepresentable at any signed width. The evaluator
now checks the expression type's signed minimum for both `/` and `%`; uncalled
32-bit probes and emitted-shape assertions cover both operations. Elisa
translation/compilation of those probes remains pending the safe Stage1 refresh.

`integer_constant_semantics.c` now exercises full-width wrap, shifts,
division, mixed signed/unsigned ordering, and negative-to-unsigned conversion.
Its native Clang build/run passes with `-Wall -Wextra -Werror`, and source line
limit plus whitespace checks pass. Generated Elisa compilation and runtime
parity are still unverified: the local Stage1 product predates the latest
compiler source, while available system memory was below the previously
established safe threshold for refreshing that shared seed. The new
`u64`-specific assertions in `core_fixtures.sh` are ready for that validation,
including checks that out-of-range `uint64`-to-signed conversions retain an
explicit Elisa cast rather than being folded to a host-specific signed value.

## Guarded Stage1 refresh deferral — 2026-10-01

The isolated Stage1 worktree is at `e8f7469e` plus its existing in-progress
main-worktree changes; it is newer than the verified Stage1 product. The
source-fresh local Stage0 product used for refresh is
`stage0-latest/compiler/bin/elisac-local-rebuild` (SHA-256
`24d761b47f987db09c0b76abc32492fc515ecc667b8ff07c7b381c1521a63002`). Two
refresh attempts were launched only in windows with the host-wide seed lock
clear, under `scripts/run_bounded_process.py` (6 GiB aggregate RSS ceiling,
900-second timeout) and the seed script's 4 GiB child RSS ceiling. Both were
stopped by this task's host-memory safety floor at 41% free. Competing compiler
processes appeared during the first attempt; the second reached the floor with
the seed as the only observed compiler process. Neither was an Elisa compiler
failure or a runner limit breach. Their peak process-group measurements were
1,394,720 KiB RSS / 1,507,987 KiB physical footprint and 2,180,000 KiB RSS /
2,185,204 KiB physical footprint. PID-specific temporary outputs were cleaned;
the old Stage1 product/runtime were unchanged (binary SHA-256
`df31f9d00a8a3ffbb61302d02d05e00a7cc5eb23e7f03d36bb6fb0cedad4e369`, runtime
SHA-256 `6a8d933dc5d9e77d491de34225ca21b7a37c117182e1e0e14d3a3e20ff6afc5e`),
and the seed lock was released before another task acquired it. Do not treat
the new product as built: retry after an idle, high-headroom window; the
runtime arithmetic acceptance regression added in this turn also remains
unrun until that refreshed compiler/runtime pair is available.

## C++ scoped-enum identity through namespaces and aliases — 2026-10-01

`typed_c_type` now follows Clang's `typeAliasDeclId` chain to the selected
`EnumDecl`, preserves the qualified scoped-enum spelling, and keeps aliases to
that declaration canonical during type expansion. Enum collection uses the
qualified type reported by Clang's enumerator declarations, so nested aliases
do not create duplicate enum definitions. Rendering and conversion analysis
resolve aliases back to that one enum; pointer/reference-shaped enum uses stay
pointer/reference types instead of being mistaken for enum scalar values.

`testdata/fixtures/cpp_enum_namespace_alias.cpp` covers
`renderer::PixelMode -> renderer::PixelModeAlias -> PublicPixelMode`, explicit
`unsigned int` storage, two high-bit values (`0x80000005` and `0xffffffff`),
function returns/parameters, and a pointer parameter. It emits one
`Renderer__PixelMode of u32` definition, compiles and links, and matches native
C++ execution with exit 0. The negative fixture
`cpp_scoped_enum_implicit_conversion_unsupported.cpp` checks both forbidden
directions; Clang and the translator both reject it with source diagnostics
and no generated stdout. The existing C enum integer, C typedef-alias, and
bool-backed C++ enum manifest cases pass as regressions.

Verification used a fresh translator build with the previously verified local
Stage1 product `elisac-stage1-callbackfix-final-v3-o1` (SHA-256
`4f6457d89d13185e6839c3baf8a04e93b83573d5c47c69220905dff4a31698f3`) and its
matching runtime (SHA-256
`6a8d933dc5d9e77d491de34225ca21b7a37c117182e1e0e14d3a3e20ff6afc5e`). The
translator SHA-256 is
`641d7bf8fea37afd6bdc5d5bf592ee5c1dc3ea0c6000eadb9007c9f184dace4e`; its
bounded source build peaked at 483 MiB RSS. The generated/native manifest case
and three enum regression cases passed, and the source line-limit and diff
whitespace gates passed. This is not a fresh build against the imported latest
Stage1 main-worktree source: that source refresh remains pending under V06 and
the shared seed-lock/memory guard policy. The later conversion work below was
rebuilt and verified with the latest local Stage1 compiler/runtime product.

## C integer conversion preservation with latest local Stage1 — 2026-10-01

Expression lowering now retains Clang's implicit arithmetic cast targets when
their scalar ABI type changes, including integer promotions, and retains
explicit numeric C/C++ casts. The emitter routes these nodes through the
shared scalar-conversion helper, including boolean destinations. This keeps
the compiler-selected width and signedness visible through narrowing and
subsequent promotions instead of reconstructing them from the original
operands. The boundary regression extends the two-level typedef-alias enum
fixture with `0xffffffffu` conversions to signed and unsigned char, short,
int, long, and long long, then compares each result against native C.

The latest compiler rejected the existing growing `darray[sview]` queue in
`ast_dependency_graph_close` because a value appended inside the loop could be
read on a later iteration. The closure queue now stores stable graph-node
indices in `darray[i64]`; the graph is immutable during closure, so this avoids
borrowed-view widening without copying identifiers or changing dependency
identity.

The direct declaration-ID closure, transitive layout/alias closure, and
external inline-redeclaration closure regressions all pass with the freshly
built translator and latest Stage1 compiler/runtime; each test was bounded to
1 GiB aggregate RSS (observed peaks below 80 MiB).

Verification used the latest isolated local Stage1 product at compiler source
revision `e2871b2`, binary SHA-256
`c6d28027b7ad6012bf711144912c2f5cf05ae857e302cde8a05cc99ca687cf50`, and its
matching runtime SHA-256
`424aaf9f49da71988809232ce658234ce97acf470ff02ab663e92f6fa09b1442`. The
translator was freshly built with `-O0` under a 1 GiB process-group RSS limit;
peak RSS was 454,944 KiB (peak physical footprint 458,914 KiB). Its SHA-256 is
`8f10ca8cb62d7f506136b072104f5127261248372bb11840cd7cb7d12a37e782`. The
four enum manifest regressions passed; `enum_typedef_aliases.c` also compiles,
links and returns 0 in `--fidelity`. The scoped-enum negative fixture still
fails translation with two diagnostics and no generated stdout. The complete
29-case acceptance manifest passed 28 cases. `c_void_pointer_boundaries`
remains a backend decline (`main@43`, binary expression); translation with
the pre-change translator produced byte-identical Elisa, so this is not
introduced by scalar cast preservation. No manifest process crashed, timed
out, or hit its resource cap. Source line-limit and `git diff --check` gates
passed.

## C pointer subtraction element scaling — 2026-10-01

C pointer subtraction now converts the target-width byte-address difference
to an element count using Clang's selected element size. This covers known
scalar, enum, pointer, and GNU `void *` pointees; it preserves signed negative
differences and omits an unnecessary division for one-byte elements. When a
record/array pointee size is unavailable, lowering emits a source-qualified
unsupported diagnostic and no Elisa program instead of returning a byte
count as though it were an element count.

`pointer_difference.c` checks positive and negative `int *` differences,
`unsigned char *`, `double *`, enum pointers, and `int **` (including the
pointer-sized inner element). It compiles and matches native C using the
pinned local Stage1 compiler/runtime. `pointer_difference_unknown_layout.c`
checks the record-layout refusal and empty stdout. The new acceptance-manifest
case is wired into `scripts/test.sh`; both focused checks pass. The full
fixtures suite also passed on this tree before the final pointer-to-pointer
size correction, with 21 pre-existing selected manifest cases; it did not
include the newly added case because that suite invocation had already read
its explicit case list. The current translator was then rebuilt with the
pinned compiler/runtime and the new acceptance case passed individually.
Record layout acquisition, pointer provenance/alias lifetime, and complete
pointer-bearing aggregate/ABI boundaries remain open.

## C object-pointer and `void *` boundaries — 2026-10-01

`void_pointer_boundaries.c` exercises ordinary C object-pointer conversion to
and from `void *` at local initialization, a function return, a call argument,
a record field, and an array element; it also checks null round-trips and a
`void **` slot/return path. Generated-shape assertions verify that `void **`
keeps two separately nullable Elisa reference layers. Native Clang and the
generated Elisa executable both return 0 with the pinned local Stage1
compiler/runtime. The focused manifest case passes and is wired into the
selected fixture suite. This is evidence for these C boundaries only; callback
signatures, project/external ABI paths, volatile-qualified pointees, and deeper
pointer chains still need independent coverage.

## Direct external C++ class-template layouts — 2026-09-29

Direct source uses of external class templates with explicit type arguments
now lower to concrete Elisa records both at global scope and through named
namespace scopes. The compact AST projection walks namespace declarations,
reconstructs each specialization spelling from its qualified namespace path
and Clang `TemplateArgument` nodes, then promotes only source-used
specializations, including verified omitted-default aliases. Typed collection
associates the canonical fully specified spelling with the specialization's
Clang declaration ID and gives each layout a deterministic `ElisaTemplate_…`
name. Omitted source spellings map to that same emitted type. It rejects ambiguous
declaration identities and emitted-name collisions. Clang also nests implicit
injected `CXXRecordDecl`s with the primary template's ordinary source name
beneath specializations; those placeholders and the primary template pattern
are now excluded, leaving only concrete layouts.

The `cpp_template_direct.cpp` regression instantiates `ExternalCell<int>` and
`ExternalCell<double>`, plus `Alpha::Cell<int>` and `Beta::Cell<int>` from the
same header. The latter two intentionally have the same short template name
and argument but must produce different Elisa types. The fixture writes and
reads all four fields, asserts four distinct generated records and no stray
primary/injected records, and compiles/links/runs generated Elisa against the
matching Stage1 runtime at both `-O0` and `-O2`. Native C++ and generated Elisa
both exit 0; two fresh translations are byte-identical. Scalar non-type values
and the bounded default-argument subset are detailed below. The existing
alias-backed regression in
`scripts/test_template_specialization_closure.py` also
passes against this rebuilt translator, so the direct-use path did not replace
or regress the existing declaration-ID path.

The translator source was rebuilt with isolated Stage1 commit
`98261837ddc8ba0596c3bf9b0c5906475bf289b7` and its matching runtime. Compiler
and runtime SHA-256 values are
`1eb3c109d5a56669826ccfb77cd5c5df03ccec20bdb49aa17077c14dc5040fc6` and
`741c2f6efd433ab6d92c7cadf275c8ceb92b3301eaf48a03a3f0cd89e0a1bd99`.
No Stage1 source file is newer than the compiler product. The current
translator object/executable SHA-256 values are
`b412e2be721e7165e8f8ce454adc9d358abaa470176d6e1f67e1c22230b1b7f4` /
`203e01895ba5c95fe118aaaffabec4de41945c270d459d716dd2ed99ee19402d`.
The bounded translator rebuild peaked at 272,480 KiB process-group RSS / 390,097
KiB sampled physical footprint. The updated unordered-map fixture translated
within its 1 GiB cap at 130,448 KiB peak RSS; generated and native programs
both returned 45 after compiling/linking with that same Stage1 pair. Alias-
specialization, declaration-closure, transitive-layout and unqualified-C++-
layout tests also pass against this rebuild.

This support remains deliberately narrow: exact source spelling is not
canonical C++ type identity. Anonymous/inline namespace elision, defaults
outside the bounded subset below, non-type arguments other than the scalar
cases documented below, partial
specializations, function templates, member-template definitions, dependent
nested layouts and cross-version Clang schema behavior remain open. These
focused fixtures were validated individually; the full fixture suite was not
rerun in this turn.

## Direct C++ scalar non-type template arguments — 2026-09-29

Direct external class-template specialization projection now handles validated
decimal integer values and boolean values. Clang JSON may omit a `type` object
from a `TemplateArgument` that carries only `value`; the projector therefore
collects the primary `ClassTemplateDecl`'s immediate ordered parameter
declarations. Integer spellings are accepted only when the scalar is a
decimal digit sequence with an optional leading minus. Boolean arguments are
normalized from Clang's integral `0/1` representation to source-level
`false/true` only when the corresponding `NonTypeTemplateParmDecl` says the
parameter type is `bool`. Unknown scalar encodings stay fail-closed.
Specialization selection still requires the reconstructed spelling to match a
source type exactly; concrete layout still comes from Clang's specialization AST.

The generic `cpp_template_direct` fixture covers integer template arguments
`FixedBuffer<2>` and `<3>`, confirming separate generated Elisa record names
and `array[i32, 2]` / `array[i32, 3]` field layouts; `FeatureFlag<true>` and
`<false>`, confirming bool-parameter-aware normalization and distinct types;
and `IntegralTag<-2>`, covering negative signed decimal values. The fixture
also verifies `DefaultBuffer<>` and explicit `<4>` share one Elisa type while
`<5>` remains distinct, plus `DefaultType<>` and explicit `<int>` sharing one
type while `<double>` remains distinct. Omitted suffixes match only when
Clang's parameter AST supplies a supported concrete type default or direct
integer-literal default equal to the specialization argument. A separate
real-Clang regression proves `N = 2 + 2` fails closed because the compact AST
does not expose a scalar value on that default expression. The canonical
full-argument spelling remains the emitted identity; abbreviated source
spellings are registered as aliases. Unsupported/dependent default expressions
do not authorize an alias. Alongside the explicit type-argument and namespace-
collision cases, all thirteen specializations compile with the isolated
Stage1 compiler at `-O0` and `-O2`. Generated and native C++ executables all
return 0.

The rebuild used the source-fresh isolated Stage1 compiler at commit
`98261837ddc8ba0596c3bf9b0c5906475bf289b7`, with compiler/runtime SHA-256
`1eb3c109d5a56669826ccfb77cd5c5df03ccec20bdb49aa17077c14dc5040fc6` /
`741c2f6efd433ab6d92c7cadf275c8ceb92b3301eaf48a03a3f0cd89e0a1bd99`.
The translator build peaked at 272,480 KiB process-group RSS and 390,097 KiB
sampled physical footprint. Its current object/executable hashes are
`b412e2be721e7165e8f8ce454adc9d358abaa470176d6e1f67e1c22230b1b7f4` /
`203e01895ba5c95fe118aaaffabec4de41945c270d459d716dd2ed99ee19402d`.
Alias-specialization, direct-declaration closure, transitive declaration
closure, and unqualified C++ layout regressions also passed. The larger
unordered-map AST translated under the 1 GiB cap at 130,448 KiB process-group
RSS; its Stage1-generated executable and native executable both returned 45.
The full fixture suite was not rerun. This does not yet implement enum,
pointer, floating, structural, packed or dependent non-type arguments,
general default-expression evaluation, partial specialization or generic-
template recovery.

## External C++ class-template specialization closure — 2026-09-29

Clang places class-template specializations inside `ClassTemplateDecl.inner`
arrays. The compact projector now follows source-referenced `typeAliasDeclId`
edges to the alias's `RecordType.decl`, then promotes only matching
specialization nodes into the translation-unit projection. It does not retain
the entire primary-template subtree or unrelated sibling specializations.
Typed collection resolves the complete record by declaration ID, and record-
valued aliases keep their Elisa record spelling rather than expanding
`IntegerCell` into the unsupported `ExternalCell<int>` scalar fallback.

`scripts/test_template_specialization_closure.py` uses real Clang JSON for an
external `ExternalCell<int>` specialization, externalizes both template and
alias provenance, removes coarse use flags, and strips desugared source type
spellings. It verifies the concrete `IntegerCell` layout and emitted local
type, then compiles, links, and compares execution to native C++ with the
isolated Stage1 compiler and its matching runtime. The test is part of
`scripts/test.sh`. This establishes one alias-reached class-template layout
shape only; direct template-valued declarations, namespace-qualified records,
function-template bodies, member templates, other Clang schemas, and full
canonical structural type identity remain open.

A separate native-valid direct-use probe (`ExternalCell<int> cell`) exposed an
unsafe fallback: without a retained specialization identity, the local object
was lowered as `i32` even though member accesses remained. The translator now
rejects this unsupported direct class-template value with empty stdout and a
source diagnostic. The fixture is part of the core suite and is compiled/run
with native Clang first. This prevents incorrect output but does not implement
direct template specialization naming or lowering.

The same C++ standard-library-heavy input was used to check the projection
boundary: `cpp_unordered_map.cpp` now translates to a 68-line Elisa file,
compiles with the isolated Stage1 compiler, and matches native execution
(both return 45). The bounded translator process peaked at about 130 MiB RSS.
The unordered-map policy validator is now limited to source-owned declarations,
so implementation-only libc++ template parameters are not misreported as
unsupported user policies. This is one focused map regression, not a full
fixture-suite pass.

## Test-suite failure attribution — 2026-09-29

The recent fixtures command exposed that a `set -e` exit from a sourced suite
could terminate `scripts/test.sh` without naming the failing command or source
line. Added a Bash `ERR` handler inherited by sourced suites; it reports the
command, source file and line only while `errexit` is enabled. Non-Bash POSIX
shells skip this optional detail. `scripts/test_test_support.sh` verifies a
deliberate error is attributed to `/dev/stdin:10`, while both `! false` and a
`set +e`/status-check sequence remain silent. The self-test passes, and both
`/bin/sh -n` and Bash syntax checks pass. The fixture suite itself is still not
claimed green; rerunning it will now identify the exact unexpected shell
failure if one recurs.

## Source-path identity and cJSON callback verification — 2026-09-29

The escaped-path fixture had regressed despite the JSON decoder being present.
Clang's raw AST contained all four functions, but an older predicate used to
distinguish a relative project include from the main source compared the raw
JSON string contents against the source spelling. A quote in a directory name
is serialized as `\"`, so the real main file was misclassified as an included
project file and sparse-location siblings were discarded. The predicate now
delegates to the same JSON-decoding, canonical-path matcher used elsewhere; no
path-specific or corpus-specific name case was added.

The original path containing quotes, a backslash and UTF-8 now projects all
four functions, including `main` (5,525 projected bytes / 386 JSON values),
compiles with the isolated Stage1 compiler and matching runtime, and exits 42
like native C. The source-level escaped-path case in
`scripts/test_suites/core_fixtures.sh` was passed by the rebuilt suite before
it advanced to later fixtures.

The const-qualified indirect callback fix is also verified through the new
`function_pointer_const_field_call` manifest case, which passes translation,
native compile, Stage1 compile/link and native/generated execution. The
refreshed single-TU cJSON smoke emits 1,573 lines / 37 functions, contains no
invalid-IR markers, compiles and links with the matching Stage1 runtime, and
matches native output exactly. The generic parser now recognizes standard
pointer qualifiers between `*` and `)` in Clang's function-pointer spelling,
so a `const` record view no longer causes the allocator's `size_t` argument
to be inferred as the callback's pointer return type.

Fixture-suite status for this turn is intentionally not called green: all 21
manifest cases passed. One trace-only retry failed early because a concurrent
Clang target-macro query produced no macro output; immediately running
`scripts/test_clang_failure.sh` alone passed. A subsequent cached run passed
the frontend preflights and manifest and progressed through the core C++,
cJSON-quality, and final switch-selector artifacts, but `scripts/test.sh
--suite fixtures --reuse-build` still exited 1 without printing the failing
assertion. The final switch-selector native and generated executables and the
pointer-valued-map native/generated executables all return the expected status
when checked directly. A traced, lower-contention rerun is still needed to
pinpoint that suite-level exit. The earlier invocation using a relative
Stage1 path failed for a separate harness reason; later runs used absolute
compiler/runtime paths. Translator RSS stayed below about 130 MiB during the
large C++ AST walks; the translator build itself was bounded at 1.5 GiB.

## Nullable pointer indexing and fresh cJSON attempt — 2026-09-29

The idiomatic expression emitter now preserves an explicit generic checked
conversion when a nullable pointer is used inside a generated
`trusted Unsafe.StaleRef` statement. The ordinary flow fact still elides the
conversion outside that boundary; within it, Elisa does not retain the
branch-local null proof from the separately emitted guard. This rule is
source-agnostic and does not inspect cJSON names or declarations.

Added `testdata/fixtures/nullable_index_after_guard.c`, which passes a
`const int *`, returns early on null, then indexes the value. The emitted
`elisa_nonnull_readonly(value)[0]` compiles, links and returns the same result
as native C with the local Stage1 compiler/runtime. Five bounded cases passed:
`readonly_nonnull_helper`, `nullable_index_after_guard`,
`c_array_to_pointer_decay`, `c_record_pointer_call_arguments`, and
`sequencing_expressions`. The six bounded-runner unit tests, source line cap,
manifest JSON validation and `git diff --check` also passed.

Fresh cJSON single-file stdout translation used:

```text
python3 scripts/run_bounded_process.py --max-rss-kb 1048576 --timeout-seconds 900 -- \
  zsh -c 'exec build/elisa-c-transpiler --idiomatic testdata/upstream/cJSON/cJSON.c > build/cjson.nullguard-20260929.elisa'
```

It exited successfully at 204,064 KiB peak process-group RSS and 221,745 KiB
sampled physical footprint, producing 89,294 bytes / 1,637 lines. The prior
`indexing requires proven non-null reference` frontend diagnostics are gone.
This output has not passed the whole-program compiler gate: the exact local
Stage1 compiler exits at its LLVM verifier with
`backend generated invalid LLVM IR; refusing to optimize or emit`, before link
or runtime comparison. The verifier exposed no underlying IR message. An
LLDB attempt to capture the module stopped its own compiler child and reached
the 120-second cap without an IR dump; no compiler source or binary was
modified by the attempt.

Separately, translating the two-unit project `cJSON.c` + `cJSON_Utils.c` with
`--output-dir build/cjson.nullguard-20260929` exited by SIGSEGV at 222,752 KiB
process-group RSS (147,201 KiB sampled physical footprint). This is a
project-mode crash, not the earlier multi-gigabyte RSS event. Single-file
stdout mode remains successful. Neither cJSON compile/runtime parity nor the
two-unit project path is accepted yet.

Toolchain provenance for these checks: translator worktree `HEAD
588e6880034f4b0c95513a6619c107a8407acbe1` with a dirty working tree;
translator binary SHA-256
`fc3a7bee8488a7703eaa51b57c8f43deea17214d277a069299ab9afde8e03757`;
Stage1 compiler worktree `HEAD
98261837ddc8ba0596c3bf9b0c5906475bf289b7`, product SHA-256
`1eb3c109d5a56669826ccfb77cd5c5df03ccec20bdb49aa17077c14dc5040fc6`, matching
runtime SHA-256
`741c2f6efd433ab6d92c7cadf275c8ceb92b3301eaf48a03a3f0cd89e0a1bd99`, and
Homebrew Clang 23.1.1 on Darwin arm64. No compiler-worktree edits were made.

## C++ `unordered_map` nullable mapped-value initialization — 2026-09-29

The complete fixture suite exposed a semantic bug in
`cpp_lib/unordered_map_core.elisa`: `arena_box_zeroed[V](&perm_arena)` returns a
heap reference to a zeroed `V` slot, but the adapter had stored that address as
the mapped `V`. With `V = u8&?`, the address is non-null, so `names[8] != nullptr`
incorrectly took the present branch. The emitted LLVM confirmed the mistake:
the `arena_box_zeroed` pointer was stored directly into the nullable pointer
field. An Elisa `zeroed` literal cannot be used for this generic `V`, because
the generic declaration itself does not prove non-null-reference fields safe
to zero. The adapter now reads element `[0]` from the zeroed box, obtaining the
value rather than its storage address, then copies that value into the map entry.

The focused translated C++ fixture and native program both exit 0. A fresh
`bash scripts/test.sh --suite fixtures --reuse-build` also passed using the
isolated stage1 compiler and its matching runtime; all 18 acceptance-manifest
cases and the broader core fixture checks passed. The translator object build
peaked at about 351 MiB RSS under a 1 GiB cap. No compiler sources were changed
for this fix. This verifies the current scalar/nullable object-pointer subset
only—class construction, custom policies, function-pointer values, pointer keys
and full iterator/reference stability remain open under L02.

## C enum typedef chains and stage1 manifest linking — 2026-09-29

Added `testdata/fixtures/enum_typedef_aliases.c` for a two-level C typedef chain
around an unsigned-backed enum. It exercises global initialization, a typed
function argument/return and explicit cast, bitwise compound assignment, plus
conversion to every standard signed and unsigned integer rank from char to long
long. Native and generated Elisa executables both exit 0. The case is now part
of the selected acceptance manifest; all 19 selected cases pass with the
isolated stage1 product and matching runtime object.

That stage1 run also exposed a test-driver integration omission: the fixture
runner already accepted `--elisa-runtime`, but `scripts/test.sh` was not
forwarding its selected runtime, so two runtime-using manifest fixtures failed
at link with `_arena_free` unresolved when stage1 was selected. The test entry
now passes the selected runtime; a runner unit test confirms it is appended to
Elisa links only, never native builds. All 12 runner self-tests pass. The
broader core fixture suite passed in the preceding run after the map fix; it
was not rerun after adding this manifest case. C++ namespace-qualified enum
aliases, scoped-enum conversion restrictions, and emitting readable Elisa type
aliases rather than duplicate enum declarations remain open.

## Worktree provenance snapshot — 2026-09-29

`docs/worktree_inventory.md` records the preservation snapshot for B01:
the translator checkout is at `9709e31f`, with 30 modified tracked entries,
228 untracked status entries and none staged. The isolated stage0 checkout is
clean at `e42bbdfe`; isolated stage1 and compiler `main` share base
`98261837`. All 14 common compiler-file diffs compare byte-for-byte equal;
stage1 also has two isolated backend/test edits. The main compiler checkout's
untracked nested worktree and all existing translator/build probes were left
untouched. Since the translator sources changed after the cached
`build/elisa-c-transpiler` was produced, its recorded hash is historical, not a
fresh-build claim. A compiler build was already active elsewhere, so no new
heavy build or upstream corpus run was started. B01's clean-source attribution
and fresh-build/corpus acceptance therefore remain open.

## Configurable compiler standard-library path — 2026-09-29

`src/main.elisa` and the C++ unordered-map adapter no longer embed the default
`elisa-transpiler-worktrees/transpiler` path. Setup/test select the standard
library through `ELISA_STAGE1_STDLIB` (default: the selected stage1 worktree),
and `scripts/ensure_local_stdlib_link.sh` creates an ignored
`src/.compiler_std` symlink. The helper is idempotent and refuses to replace a
different link or any existing non-symlink path. Build fingerprints now hash
all `.elisa` files under the selected stdlib so library changes invalidate
reuse. The helper validates the required runtime, JSON and collections modules.
Its isolated shell regression (including spaced paths, idempotence, collisions
and incomplete selections), build-cache self-test, script syntax checks,
source-size gate and `git diff --check` pass. The helper has not been exercised through Elisa's
actual include expander and no translator rebuild was started while another
compiler job was active; compiler-level relocation validation remains open.

## Short-enum ABI and current local compiler refresh — 2026-09-28

The compile-command parser preserves `-fshort-enums` (with the final
`-fno-short-enums`/`-fshort-enums` occurrence taking precedence), and C enum
emission chooses a storage integer wide and signed enough for the declared
enumerator range. `scripts/test_short_enum_abi.sh` passed against native Clang,
the refreshed local stage0 compiler, and stage1. Its fixture checks unsigned
and signed 8-bit enums, an unsigned 16-bit enum, casts/function boundaries,
`sizeof`, and a record containing all three enums.

Toolchain identities for that run:

- stage0 worktree: `e42bbdfe8a1b8123c3c4bfd096d64eb4c97c8b11`, executable
  SHA-256 `915d12bba8a4c2a89eb826d61d741f952ec3be718cf023b84f51f71ffaf28ba1`;
- stage1 source: `98261837ddc8ba0596c3bf9b0c5906475bf289b7`, executable SHA-256
  `bcb0dab36d1944ca8d8dfcfae2c8aed276e6745d97591cfd7495b9ecb0bcf8a2`;
- matching stage1 runtime SHA-256
  `741c2f6efd433ab6d92c7cadf275c8ceb92b3301eaf48a03a3f0cd89e0a1bd99`.

This run used the existing translator executable (SHA-256
`57dfcdcf5024bee996e5ab630cbe55ded8fb93a7c062e4f2e9fc9cd1ba948026`), not a
fresh build from current sources. A fresh compile attempt with the refreshed
compiler pair exposed a compatibility break: the translator directly names
the stdlib JSON module's now-private `JsonValue`, `JsonMember`, and raw child
copy helpers, while the current public API is region-indexed
`JsonValueHandle[r]`. The handle migration is tracked under V06; it must retain
the parse arena's lifetime and avoid a second full DOM copy. The generated
program's successful dual-stage compile/run therefore verifies the enum ABI
behavior but is not evidence that the current translator source builds with
the refreshed compiler pair.

## Latest isolated compiler refresh and enum-size regression — 2026-09-16

The isolated stage1 compiler worktree was fast-forwarded from `d6a693c0` to
the current main-worktree tip `5329edfd` (`fix match target machine
optimization level`), bringing in the four latest committed compiler changes
while preserving the translator-local variadic/intrinsic and unordered-NaN
backend fixes. Stage1 was then rebuilt from the isolated stage0 product under
the 4 GiB RSS guard, together with its matching runtime object.

The refreshed products are:

- stage0 revision `3a5520d8fd56b86c430f39518a261e9030fa72ec`, executable
  SHA-256 `207e5a3d997f921f161d242e92860a6c99db0f5c917d9f676c3498d3ab312670`;
- stage1 revision `5329edfdbefa27b5c1c51253da0073256ed51058`, executable
  SHA-256 `9c3302bfb0b830cda5310e10c11740bfcfe7634d12671c5c5c57fc254c01b3e3`;
- matching stage1 runtime SHA-256
  `85f1107eef00a7dd903e511df366b8b6cade4d8573cf0478f1de91604ea5beb9`;
- translator executable SHA-256
  `15a4d1ccce0becbab44c08657cd94bf7c01e98d49df8b25865c016884b6d67e8`.

The first refreshed 19-case manifest run exposed two generic issues: stage1's
constant folder did not recognize enum conversion calls in global
initializers, and the translator rendered `sizeof(Truth)` as `size_of[i32]`
instead of the Clang-selected `u8` backing size. The isolated stage1 folder now
preserves enum-cast constants, and the translator's `sizeof` emitter resolves
plain enum names through the collected backing type. The full 19-case manifest
then passed serially: 19 passed, 0 failed, 0 timed out, 0 crashed. This is
evidence for the bounded fixture corpus only; upstream header-heavy corpus
coverage and the remaining ABI/layout work stay open.

## Structured quality metrics — 2026-09-16

`scripts/quality_report.sh` now performs one translation with the typed-IR dump
and rewrite explanation enabled, then reports structural expression, statement,
switch-case, function, global and residual goto/label counts alongside the
existing rendered-output pressure metrics. It also exposes every applied
readability-rule counter. This keeps the new structural measurements independent
of source names, comments and string contents; the cJSON quality regression
checks that the IR metrics are populated and that rewrite counters are numeric.

## Generic `va_arg` lowering — 2026-09-16

Clang models `va_arg(ap, T)` as a dedicated `VAArgExpr`, not as an ordinary
callable builtin. The translator now preserves that result type and lowers the
operand to the generic Elisa spelling `va_arg[T](...)`. The emitted prelude
contains one generic declaration:

```elisa
extern va_arg[T](storage: mutable void&) -> T
```

The isolated stage1 compiler was refreshed from the local compiler worktree,
and its backend now recognizes the generic primitive through the shared
generic-extern mechanism and calls LLVM's `LLVMBuildVAArg`. A direct stage1
probe emitted a real `va_arg ptr %ap, i32` instruction with no unresolved
`@va_arg` declaration. The generic
`testdata/fixtures/variadic_va_arg.c` fixture translated to
`va_arg[i32]((&ap).cast[mutable void&])`, compiled and linked with isolated
stage0, and ran with exit code 0. This slice is intentionally narrower than
complete variadic support: aggregate extraction and
target-specific lifetime/ABI diagnostics remain open under S08.

The same generic boundary now lowers C's `__builtin_va_copy` to
`llvm_va_copy(destination, source)`. The compiler resolves the overloaded
`llvm.va_copy` intrinsic from the destination pointer type and emits
`llvm.va_copy.p0` in LLVM; it does not create a target-library `va_copy` symbol.
The translated `variadic_va_copy` fixture reaches native and generated build
artifacts successfully. Its final runtime comparison is currently blocked by
the host's intermittent macOS dyld stall before `main` (the native child was
sampled in `_dyld_start`), so the source-level and LLVM checks are accepted but
the end-to-end runtime gate remains open until the launcher is healthy.

The variadic call emitter also applies C's default argument promotions at the
ellipsis boundary. The target ABI supplies the integer width used to decide
which values promote to `int`; `_Bool` and enumerations promote to `i32`, and
`float` promotes to `f64`. The `variadic_promotions` fixture demonstrates
`unsigned char` → `i32`, `float` → `f64`, and `_Bool` → `i32`. Its generated
Elisa compiles, links, and returns the expected result with both the isolated
stage0 compiler and the refreshed isolated stage1 compiler. Aggregate
extraction and complete target-specific `va_list` lifetime/cleanup diagnostics
remain intentionally open under S08.

## Owned compiler-build limits — 2026-09-29

`scripts/test.sh` now builds and links the translator through
`scripts/run_bounded_process.py`. Each command is launched in its own POSIX
session; the runner samples summed RSS for that process group, applies a wall
deadline, and terminates/reaps only that owned group on a limit breach. The
defaults are 2 GiB and 600 seconds, configurable with
`ELISA_TRANSLATOR_BUILD_MAX_RSS_KB` and
`ELISA_TRANSLATOR_BUILD_TIMEOUT_SECONDS`. The test driver also runs four
bounded-process regressions for returned exit status/output, timeout cleanup
of a child process, aggregate-RSS termination and invalid-limit rejection; all
four passed on 2026-09-29.

This records the guard implementation and unit evidence only. No translator
rebuild was started for this entry: concurrent compiler builds were active and
system free-memory readings fluctuated from 33% to 43%. Therefore it does not
yet establish a fresh translator build, calibrated end-to-end peak, or a
whole-suite system-memory bound.

## JSON handle migration source audit — 2026-09-29

Correction to the older 2026-09-28 note under “Short-enum ABI and current
local compiler refresh”: the translator source has since been migrated to the
public region-indexed JSON API. A repository-wide word-boundary search found
no `JsonValue` or `JsonMember` references in translator `src/`, and no raw
child-copy helpers. `emit_program` parses into `ast_arena`, obtains the root
with `json_handle_from_result(parsed)`, then carries that handle in the
translation context; traversal accessors preserve the handle's region, and
text accessors return region-bound views. The stdlib's private `JsonValue`
variants contain scalar data or pointers/counts into the parse arena, while
the public accessors wrap those existing nodes. This verifies the source-level
ownership/no-second-DOM contract, not compilation of the current translator
sources; V06's fresh build and large-input regression remain open.

## Designated and sparse initializers — 2026-09-16

Clang's initializer-child ordering is now used to lower C designated
initializers generically. Record designators become named Elisa fields,
array designators become their target positions, and omitted members retain
their C zero-initialized values. `testdata/fixtures/designated_init.c`
emits `Pair{first: 3, second: 7, third: zeroed}` and
`[zeroed, zeroed, 7, zeroed, 9]`; the fixture passes native/generated
compilation, linking, and stage0 runtime comparison. The generated source also
compiles and links with the refreshed isolated stage1 compiler. A later
multi-case stage1 runtime run was stopped because the host's native child
entered the known macOS dyld stall before `main`; this does not affect the
completed stage0 runtime result. Nested designator chains, unions, flexible
arrays, and initializer evaluation-order cases remain separate S06 work.

## Generic C floating builtins and NaN semantics — 2026-09-16

Clang expands standard `NAN`/`INFINITY` macros into builtin identities such as
`__builtin_nanf` and `__builtin_huge_valf`. The translator now classifies the
whole builtin family by identity, rejects wrong argument shapes, and emits
typed compiler-owned IEEE expressions rather than declarations for guessed
platform symbols. Both the `f32` and `f64` paths are covered by
`testdata/fixtures/floating_edge_values.c`; its generated source contains
`(0.0 / 0.0)` and `(1.0 / 0.0)` for the double values, and the corresponding
typed forms for the macro-expanded float values.

While validating that fixture, the isolated latest compiler pair exposed and
fixed a backend bug: LLVM predicate value 9 is unordered-equal, while
unordered-not-equal is value 14. Stage0 and stage1 now emit `fcmp une` for
floating `!=`, and float-to-bool conversion uses the same unordered predicate.
The compiler-owned regression `llvm_float_compare_test.go`, direct LLVM probes,
and native/generated runtime checks all pass with the refreshed isolated stage1
compiler and matching runtime. Exact long-double/extended-format handling,
fast-math policy, signaling-NaN payloads, and broader literal-rounding coverage
remain open under S04.

## Effectful switch selectors — 2026-09-16

The generic switch lowering now detects calls, assignments, increment/decrement
sequences, side-effecting indexed accesses and other non-pure selector nodes.
Those selectors are evaluated into a deterministic collision-checked temporary
before `match`; pure selectors retain the direct `match expression` form. The
same rule is applied inside localized CFG switch regions. This is a translator
compatibility guard for the current Elisa backend, whose inline match lowering
can otherwise evaluate a selector once per arm. `switch_selector_once.c` now
checks the generated temporary shape and passes native/generated parity, while
the control-flow and fixture suites remain green.
