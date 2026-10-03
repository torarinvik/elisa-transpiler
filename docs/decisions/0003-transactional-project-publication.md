# ADR 0003: Publish project output as a recoverable generation

## Status

Accepted

## Context

A multi-file translation can fail after some units have succeeded. Writing
modules directly to their final paths can leave a mixed generation that looks
usable but combines old and new source. A manifest must also never advertise a
module that was not fully translated.

## Decision

Project modules and the manifest are first written beside their final paths
with a process-and-index transaction suffix. After all units have passed
frontend, projection, lowering, diagnostics, and write checks, existing final
files are moved to exact transaction-specific backup paths. Staged modules are
renamed into place, and the manifest is renamed last. Any failed rename restores
the backups and removes staged files. Failed translation before publication
leaves previous outputs untouched.

All suffix construction removes the existing C-string terminator before adding
another suffix. Paths are exact validated paths; no broad directory deletion is
used.

## Consequences

- A consumer sees either the previous complete generation or the new complete
  generation, subject to the underlying filesystem's rename guarantees.
- Publication is recoverable if an individual rename fails.
- Obsolete generated files still require validated prior-manifest ownership
  before they may be removed.
- Full target-language compile validation before publication remains a separate
  workflow policy; the translator's default transaction validates its own
  frontend and typed-lowering stages.

## Evidence

`src/cli_project_transaction.elisa` implements staging, backup, publication,
rollback, and cleanup. `scripts/test_clang_failure.sh` proves that a successful
unit followed by a Clang failure preserves prior modules and the prior
manifest, emits no partial stdout, and leaves no transaction files. Project
generation tests also verify that a rerun replaces existing modules.
