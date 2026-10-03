#!/usr/bin/env python3
"""Check proof/decline rewrite events are source-linked and diagnostic-only."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path


EVENT = re.compile(
    r"^rewrite-event source=(?P<source>.+) "
    r"range-start=(?P<start>-?\d+) range-end=(?P<end>-?\d+) "
    r"expression=(?P<expression>-?\d+) rule=(?P<rule>[a-z-]+) "
    r"decision=(?P<decision>applied|declined) "
    r"(?P<detail_name>proof|reason)=(?P<detail>[a-z-]+)$"
)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    translator = Path(
        os.environ.get("ELISA_TRANSLATOR_BIN", root / "build" / "elisa-c-transpiler")
    ).resolve()
    if not translator.is_file():
        raise SystemExit(f"translator executable not found: {translator}")

    source_path = (root / "testdata" / "fixtures" / "rewrite_explanation.c").resolve()
    source = source_path.read_bytes()
    normal = subprocess.run(
        [str(translator), str(source_path)], cwd=root, capture_output=True, check=False
    )
    explained = subprocess.run(
        [str(translator), "--explain-rewrites", str(source_path)],
        cwd=root,
        capture_output=True,
        check=False,
    )
    assert normal.returncode == explained.returncode == 0
    assert normal.stdout == explained.stdout, "explanation mode changed generated Elisa"

    events = []
    for line in explained.stderr.decode().splitlines():
        match = EVENT.match(line)
        if match:
            event = match.groupdict()
            event["start"] = int(event["start"])
            event["end"] = int(event["end"])
            event["expression"] = int(event["expression"])
            events.append(event)

    def require(rule: str, decision: str, detail_name: str, detail: str, snippet: bytes) -> None:
        for event in events:
            if (
                event["rule"] == rule
                and event["decision"] == decision
                and event["detail_name"] == detail_name
                and event["detail"] == detail
                and event["source"] == str(source_path)
                and 0 <= event["start"] < event["end"] <= len(source)
                and source[event["start"] : event["end"]] == snippet
            ):
                return
        raise AssertionError(
            f"missing source-linked {decision} event for {rule}/{detail}: {snippet!r}\n"
            + explained.stderr.decode(errors="replace")
        )

    require(
        "identity-binary",
        "applied",
        "proof",
        "integer-identity-with-pure-operands",
        b"value + 0",
    )
    require(
        "integer-fold",
        "applied",
        "proof",
        "target-abi-safe-integer-constant",
        b"3 + 4",
    )
    require(
        "identity-binary",
        "declined",
        "reason",
        "operand-has-side-effects",
        b"next_value() * 1",
    )
    require(
        "identity-binary",
        "declined",
        "reason",
        "operand-has-side-effects",
        b"volatile_value + 0",
    )
    require(
        "conditional-arm-pruning",
        "applied",
        "proof",
        "target-abi-integer-constant-condition",
        b"1 ? 9 : next_value()",
    )
    require(
        "conditional-arm-pruning",
        "applied",
        "proof",
        "target-abi-integer-constant-condition",
        b"1 ? 2 : next_value()",
    )
    require(
        "conditional-arm-pruning",
        "declined",
        "reason",
        "condition-has-side-effects",
        b"next_value() ? value : 0",
    )
    require(
        "boolean-zero-predicate",
        "declined",
        "reason",
        "operand-not-boolean",
        b"not_bool == 0",
    )
    assert b"rewrite-stats source=" in explained.stderr
    print("rewrite explanation checks passed")


if __name__ == "__main__":
    main()
