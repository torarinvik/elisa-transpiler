#!/usr/bin/env python3
"""Deterministically minimize JSON ASTs while preserving a caller predicate."""

from __future__ import annotations

import json
from typing import Any, Callable, Iterator


def _compact_size(value: Any) -> int:
    encoded = json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        separators=(",", ":"),
    )
    return len(encoded)


def _reduced_values(value: Any, *, root: bool = False) -> Iterator[Any]:
    """Yield smaller JSON-compatible values in a stable, structural order."""
    if isinstance(value, dict):
        for key in value:
            if root and key in ("kind", "inner"):
                continue
            candidate = dict(value)
            del candidate[key]
            yield candidate

        for key, child in value.items():
            if root and key == "kind":
                continue
            for reduced_child in _reduced_values(child):
                candidate = dict(value)
                candidate[key] = reduced_child
                yield candidate
        return

    if isinstance(value, list):
        length = len(value)
        chunk_size = length
        while chunk_size:
            for start in range(0, length, chunk_size):
                candidate = value[:start] + value[start + chunk_size :]
                if len(candidate) < length:
                    yield candidate
            chunk_size //= 2

        for index, child in enumerate(value):
            for reduced_child in _reduced_values(child):
                candidate = list(value)
                candidate[index] = reduced_child
                yield candidate
        return

    if isinstance(value, str):
        length = len(value)
        seen = {value}
        candidate = ""
        if candidate not in seen:
            seen.add(candidate)
            yield candidate
        chunk_size = length
        while chunk_size:
            for start in range(0, length, chunk_size):
                candidate = value[:start] + value[start + chunk_size :]
                if candidate not in seen and len(candidate) < length:
                    seen.add(candidate)
                    yield candidate
            chunk_size //= 2
        return

    if isinstance(value, bool) or value is None:
        if value is True:
            yield False
        return

    if isinstance(value, int):
        candidates = (0, 1, -1, value // 2)
        seen: set[int] = set()
        for candidate in candidates:
            if candidate != value and candidate not in seen:
                seen.add(candidate)
                yield candidate
        return

    if isinstance(value, float):
        if value != 0.0:
            yield 0.0


def minimize_ast_json(
    value: Any,
    preserves_mismatch: Callable[[Any], bool],
    *,
    max_probes: int = 32,
    max_candidates: int = 256,
) -> tuple[Any, int]:
    """Shrink a JSON value, bounding both oracle probes and candidate work.

    If the root is an object, its ``kind`` and ``inner`` fields are never
    removed. The caller's predicate remains authoritative for AST validity and
    whether the observed mismatch is preserved. Returns the minimized value
    and the number of predicate (typically translator-process) probes used.
    """
    if max_probes < 1 or max_candidates < 1:
        raise ValueError("minimizer budgets must be positive")

    current = value
    if not preserves_mismatch(current):
        return current, 1

    probes = 1
    candidates_seen = 0
    while probes < max_probes and candidates_seen < max_candidates:
        current_size = _compact_size(current)
        accepted = False
        for candidate in _reduced_values(current, root=isinstance(current, dict)):
            if candidates_seen >= max_candidates or probes >= max_probes:
                break
            candidates_seen += 1
            try:
                if _compact_size(candidate) >= current_size:
                    continue
            except (TypeError, ValueError):
                continue

            probes += 1
            if preserves_mismatch(candidate):
                current = candidate
                accepted = True
                break

        if not accepted:
            break

    return current, probes
