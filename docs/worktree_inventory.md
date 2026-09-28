# Worktree inventory

Snapshot taken 2026-09-29 for roadmap item B01. This is a preservation
inventory, not a clean baseline: the translator checkout had accumulated
uncommitted work before this snapshot. No files were reset, removed, staged or
committed as part of the inventory.

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
