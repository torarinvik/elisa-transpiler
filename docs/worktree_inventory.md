# Worktree inventory

Snapshot taken 2026-09-29 for roadmap item B01. This is a preservation
inventory, not a clean baseline: the translator checkout had accumulated
uncommitted work before this snapshot. No pre-existing files were reset or
removed. After capturing the snapshot, only this new inventory document was
staged and committed; all other dirty paths remained untouched.

## Re-audit — 2026-10-05

Read-only compiler-source and process-safety re-audit; no compiler build,
worktree creation, checkout or source refresh was started.

- Translator: branch `main`, HEAD
  `2b098cde3bcae7b01938f5d739d944ed3e2ce96d`. At audit time the only tracked
  modifications were the bounded-process host-memory gate, its setup
  integration and regression tests, plus the Stage1 freshness-guard test
  adaptation. Ignored `build/`, upstream fixtures and `src/.compiler_std`
  remain preserved; the standard-library link still targets the intended
  translator-local Stage1 worktree path.
- Stage0 source checkout: `../Go projects/Elisa-core`, clean `main` at
  `6a0628cc48a7e019ed023c835b379fb55522ff1e`.
- Stage1 source checkout: `../Elisa-compiler`, clean `main` at
  `8e08cd3397b1680c61bfb76b70e1a76541522e3d`. Its source-fresh Stage1
  executable SHA-256 is
  `f7d4dc3c2a2a126da19723abdcd806bf99f08a71cc8bf15a35c2f508e2e19b9d`,
  matching runtime SHA-256 is
  `b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`, and
  provenance sidecar SHA-256 is
  `d69a501ba4dfdae54c5ea9975a9faf477641789e171aee8d0980c02b06adc375`.
  The Stage1 source-freshness guard reported this product current for the
  source checkout. These main-checkout artifacts have not yet been copied
  into the translator's private compiler worktree.
- The translator-local Stage0 and Stage1 worktree directories are absent;
  their configured branches are not yet checked out. A separate Stage1 seed
  was active under `/private/tmp/luna-g75-return-repro-20261005` and held
  `${TMPDIR}/elisac-stage1-global-seed.lock`. The host sampler reported 37%
  free memory during the harmless runner smoke test. The new setup guard's
  default 41% floor therefore correctly makes this an unsafe compiler-build
  window. Wait for the lock and recheck host headroom before creating/building
  the translator-local compiler pair.

## Re-audit — 2026-10-03

This read-only re-audit supersedes the compiler revisions and artifact-freshness
claims below; the September 29 translator preservation snapshot remains useful
for its historical ownership caveats. No build, checkout, merge, or lock
operation was started by this audit.

- Translator: branch `work`, HEAD `588e6880034f4b0c95513a6619c107a8407acbe1`;
  31 modified tracked paths, 341 untracked non-ignored paths, and zero staged
  paths. Existing changes remain unattributed and must not be blanket-staged.
  `build/elisa-c-transpiler` is an October 1 artifact (SHA-256
  `39e15bb1b09e0e9f107b23433753d036b1017146dfe310eeac4504aa780e22f7`), so it
  is not evidence for the current translator sources.
- Selected isolated Stage0: `../elisa-transpiler-worktrees/stage0-latest`,
  branch `codex/transpiler-local-stage0-latest`, HEAD
  `a98ef9228144619570f0aa47c5a92c4050f7d4ae`; its on-disk binary SHA-256 is
  `915d12bba8a4c2a89eb826d61d741f952ec3be718cf023b84f51f71ffaf28ba1`.
- Selected isolated Stage1: `../elisa-transpiler-worktrees/transpiler`,
  branch `codex/transpiler-local-stage1`, HEAD
  `9e1ddcbc8ccc5646d5f668bee2fbaaa56bf3a978`, with 31 dirty status entries.
  Against the local compiler `main` checkout at
  `9486c95679e635e4d77c8a406b35bbcdf622a5e6`, the selected Stage1 branch has
  five commits not in `main`, while `main` has 23 commits not in the Stage1
  branch (merge base `bb5a13cfd1ed90ccb6257a8d2cfbd3925c5b5270`). The `main`
  checkout itself has 47 dirty status entries. Neither checkout was modified.
  The selected Stage1 executable (SHA-256
  `df31f9d00a8a3ffbb61302d02d05e00a7cc5eb23e7f03d36bb6fb0cedad4e369`) and
  runtime object (SHA-256
  `6a8d933dc5d9e77d491de34225ca21b7a37c117182e1e0e14d3a3e20ff6afc5e`) are
  dated September 30 and are not source-fresh for either dirty checkout.
- During the audit a separate Stage1 seed process was active in another
  scratchpad worktree and the shared seed lock existed; system-wide memory
  reported 53% free. No compiler build was started. Wait for the shared lock to
  be released and re-check active compiler work and memory before refreshing
  the local Stage1 product from the newer local `main` source.

Consequently the translator currently has no verified build against the
latest local compiler `main` source. Historical test results below remain
historical until rerun against a source-fresh Stage1 binary and its matching
runtime.

## Translator checkout

- Repository: `elisa-transpiler`
- Branch and base commit: `work` at `9709e31fac630bed219955056552a2afc54cc67e`
- Git status: 30 modified tracked entries, 228 untracked porcelain entries,
  zero staged entries. Git collapses some untracked directories, so these are
  status-entry counts, not necessarily leaf-file counts.
- Status groups: root 3 tracked / 2 untracked; `scripts/` 19 entries;
  `src/` 58; `testdata/fixtures/` 162; other `testdata/` 12; `docs/` 1;
  `cpp_lib/` 1. The path-group totals include both modified tracked paths and
  untracked paths, except the root split shown explicitly.
- Tracked root edits are `.gitignore`, `IMPLEMENTATION_PLAN.md`, and
  `README.md`. The two root-level untracked artifacts are `stage1_out.bc` and
  `stage1_out.o`. The tracked translator edits otherwise lie in `scripts/`,
  `src/`, and two existing fixtures (`enum_flags.c` and `unsupported_for.c`).
- Untracked source/modules, fixture additions, runner tests, C++ adapter files,
  and execution notes map to roadmap areas, but their authorship cannot be
  established from the Git state alone. They are preserved as existing work.
- Diagnostic-only/unclassified material includes backend probes and repros in
  `testdata/`, fake tools, generated stage1 bitcode/object files, and the large
  ignored `build/` tree. These remain untouched and are not presumed to be
  deliverable source.

No single clean translator baseline exists from which to attribute every
working-tree hunk. For that reason this snapshot does not authorize a blanket
commit. Later commits must stage only a reviewed, self-contained slice with
known ownership; otherwise keep the accumulated changes intact and ask before
reorganizing them.

## Elisa compiler worktrees

| Worktree | Branch / revision | State and product identity |
| --- | --- | --- |
| Stage0 main checkout `Go projects/Elisa-core` | `main`, `e42bbdfe8a1b8123c3c4bfd096d64eb4c97c8b11` | Clean and exactly aligned with the isolated stage0 worktree; no newer stage0 changes need pulling. |
| `elisa-transpiler-worktrees/stage0-latest` | `codex/transpiler-local-stage0-latest`, `e42bbdfe8a1b8123c3c4bfd096d64eb4c97c8b11` | Clean; `compiler/bin/elisac-local` SHA-256 `915d12bba8a4c2a89eb826d61d741f952ec3be718cf023b84f51f71ffaf28ba1`. |
| `elisa-transpiler-worktrees/transpiler` | `codex/transpiler-local-stage1`, `98261837ddc8ba0596c3bf9b0c5906475bf289b7` | 16 modified tracked paths: 14 compiler edits shared with main plus local backend fix and regression. Existing `bin/elisac-stage1` SHA-256 `2a3dee07958e1cfe73eb385dad7a258ff2c7ab1ffd9e0e801e9ed0bf7608ab8c`; matching runtime object SHA-256 `741c2f6efd433ab6d92c7cadf275c8ceb92b3301eaf48a03a3f0cd89e0a1bd99`. These product hashes identify the files on disk; they do not prove that the binaries contain the current dirty source edits. |
| Main compiler checkout `Elisa-compiler` | `main`, `98261837ddc8ba0596c3bf9b0c5906475bf289b7` | Has the same 14 shared compiler-file edits, plus an unrelated untracked nested worktree directory. The 14 shared `git diff --binary` outputs compare byte-for-byte equal to the isolated stage1 worktree. Main checkout left untouched. |

The 14 shared files are `src/driver/elisac_pymodule_type_names.elisa`,
`src/parser/{ast_side_tables,parser_decl_contracts,parser_func_params,parser_machine_laws,parser_protocol_parameters,parser_stmt_for,parser_stmt_pattern}.elisa`,
and `src/semantic/{check_call_argument_exclusivity,resolve,resolve_expr_walk,resolve_flow,resolve_scope,semantic_types}.elisa`.
The isolated stage1-only edits are
`src/backend/codegen_expr_direct_call.elisa` and
`test/parity/backend_smoke_behavior.sh`.

## Current translator artifact and build safety

The canonical-looking `build/elisa-c-transpiler` exists and has SHA-256
`f022d863a824e43c46600788004172cf750c6f692820a4f25521143b4c6343e6`; its
mtime is 2026-09-28 23:28 CEST. Because translator sources are dirty and no build
was run for this snapshot, treat it as a cached historical artifact, not proof
of the current source. The selected Clang reports Homebrew Clang 23.1.1 for
`arm64-apple-darwin27.0.0`.

At inventory time compiler work was active in other worktrees. Accordingly no
translator rebuild or upstream corpus run was started. The new bounded runner
has unit-test evidence recorded in `execution_status.md`; its process limits
have not yet been exercised on a translator build. B01 remains open until a
fresh bounded build and serial test/corpus results are recorded.
