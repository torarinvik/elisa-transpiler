#!/usr/bin/env python3
"""Render acceptance-run outcome counts beside translation quality metrics."""

import json
import re
import sys
from pathlib import Path


OUTCOMES = (
    "passed",
    "failed",
    "timed_out",
    "crashed",
    "resource_limited",
    "monitor_error",
    "unsupported",
    "skipped",
    "missing_tool",
)


def summarize(path, manifest_path=None):
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("acceptance summary must be a JSON object")
    selected = document.get("selected_cases")
    counts = document.get("counts")
    if not isinstance(selected, list) or not isinstance(counts, dict):
        raise ValueError("acceptance summary requires selected_cases and counts")
    if any(not isinstance(name, str) for name in selected) or len(set(selected)) != len(selected):
        raise ValueError("selected_cases must contain unique case names")
    normalized = {}
    for outcome in OUTCOMES:
        value = counts.get(outcome, 0)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("counts.%s must be a non-negative integer" % outcome)
        normalized[outcome] = value
    unrecognized = set(counts) - set(OUTCOMES)
    if unrecognized:
        raise ValueError("unrecognized outcome counts: %s" % ", ".join(sorted(unrecognized)))
    selected_count = len(selected)
    recorded_count = sum(normalized.values())
    pass_fraction = (
        "%.4f" % (normalized["passed"] / selected_count)
        if selected_count
        else "n/a"
    )
    rows = [
        ("acceptance_selected_cases", selected_count),
        ("acceptance_results_recorded", recorded_count),
        ("acceptance_results_complete", str(recorded_count == selected_count).lower()),
        ("acceptance_pass_fraction", pass_fraction),
    ]
    rows.extend(("acceptance_%s" % outcome, normalized[outcome]) for outcome in OUTCOMES)
    results = document.get("results")
    if results is not None:
        if not isinstance(results, list) or len(results) != selected_count:
            raise ValueError("results must contain one result for every selected case")
        result_names = [result.get("name") if isinstance(result, dict) else None for result in results]
        if any(not isinstance(name, str) for name in result_names):
            raise ValueError("each result requires a string case name")
        if set(result_names) != set(selected) or len(set(result_names)) != len(result_names):
            raise ValueError("results names must match selected_cases exactly")
        observed_counts = {outcome: 0 for outcome in OUTCOMES}
        for result in results:
            if not isinstance(result, dict) or result.get("status") not in OUTCOMES:
                raise ValueError("each result requires a recognized status")
            observed_counts[result["status"]] += 1
        if observed_counts != normalized:
            raise ValueError("summary outcome counts do not match per-case results")

        manifest_families = None
        if manifest_path is not None:
            manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
            manifest_families = manifest.get("feature_families") if isinstance(manifest, dict) else None
            if not isinstance(manifest_families, dict):
                raise ValueError("fixture manifest must provide a feature_families object")
            missing = set(selected) - set(manifest_families)
            if missing:
                raise ValueError("fixture manifest has no family tags for: %s" % ", ".join(sorted(missing)))

        family_counts = {}
        for result in results:
            families = result.get("feature_families")
            if manifest_families is not None:
                expected_families = manifest_families[result["name"]]
                if families is not None and families != expected_families:
                    raise ValueError("result family tags disagree with the selected fixture manifest")
                families = expected_families
            if families is None:
                families = []
            if not isinstance(families, list) or any(
                not isinstance(family, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", family)
                for family in families
            ):
                raise ValueError("result feature_families must contain snake_case names")
            if len(set(families)) != len(families):
                raise ValueError("result feature_families contains duplicates")
            for family in families:
                counts = family_counts.setdefault(family, {outcome: 0 for outcome in OUTCOMES})
                counts[result["status"]] += 1
        rows.append(("acceptance_feature_families_reported", str(bool(family_counts)).lower()))
        for family, outcomes in sorted(family_counts.items()):
            family_selected = sum(outcomes.values())
            rows.append(("acceptance_feature_family.%s.selected" % family, family_selected))
            rows.append((
                "acceptance_feature_family.%s.pass_fraction" % family,
                "%.4f" % (outcomes["passed"] / family_selected) if family_selected else "n/a",
            ))
            rows.extend(
                ("acceptance_feature_family.%s.%s" % (family, outcome), outcomes[outcome])
                for outcome in OUTCOMES
            )
    return "".join("%s: %s\n" % row for row in rows)


def main(argv):
    if len(argv) not in (2, 3):
        print("usage: quality_coverage.py ACCEPTANCE_SUMMARY_JSON [FIXTURE_MANIFEST_JSON]", file=sys.stderr)
        return 2
    try:
        sys.stdout.write(summarize(argv[1], argv[2] if len(argv) == 3 else None))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print("quality coverage: %s" % error, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
