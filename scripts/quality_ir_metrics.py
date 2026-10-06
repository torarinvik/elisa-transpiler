#!/usr/bin/env python3
"""Compute per-function structural metrics from the typed-IR v16 dump."""

import sys
from collections import Counter
from pathlib import Path
import re

from quality_ir_graph import (
    _decode_hex,
    _expression_edges,
    _field_range,
    _integer,
    expression_fingerprints as _expression_fingerprints,
    statement_fingerprints as _statement_fingerprints,
    unreferenced_local_declarations as _unreferenced_local_declarations,
)


def _parse_record(line, prefix):
    parts = line.split()
    field_start = 1 if prefix == "counts" else 2
    if len(parts) < field_start or parts[0] != prefix:
        raise ValueError("malformed %s record" % prefix)
    if prefix == "counts":
        index = -1
    else:
        try:
            index = int(parts[1], 10)
        except ValueError as error:
            raise ValueError("invalid %s record index" % prefix) from error
    fields = {}
    for token in parts[field_start:]:
        if "=" not in token:
            raise ValueError("malformed %s field %r" % (prefix, token))
        name, value = token.split("=", 1)
        if not name or name in fields:
            raise ValueError("duplicate or empty %s field %r" % (prefix, name))
        fields[name] = value
    return index, fields


def _indexed_records(lines, prefix, expected):
    records = {}
    marker = prefix + " "
    for line in lines:
        if not line.startswith(marker):
            continue
        index, fields = _parse_record(line, prefix)
        if index in records:
            raise ValueError("duplicate %s record %d" % (prefix, index))
        records[index] = fields
    if len(records) != expected or sorted(records) != list(range(expected)):
        raise ValueError("%s records do not match the declared count" % prefix)
    return records


def _parse_dump(text):
    lines = text.splitlines()
    headers = [index for index, line in enumerate(lines) if line.startswith("typed-ir-v")]
    if len(headers) != 1:
        raise ValueError("expected exactly one typed-IR version header")
    if lines[headers[0]] != "typed-ir-v16":
        raise ValueError("expected typed-ir-v16 dump")
    count_lines = [line for line in lines if line.startswith("counts ")]
    if len(count_lines) != 1:
        raise ValueError("expected exactly one counts record")
    _, counts = _parse_record(count_lines[0], "counts")

    expr_count = _integer(counts, "exprs")
    stmt_count = _integer(counts, "stmts")
    function_count = _integer(counts, "functions")
    expr_child_count = _integer(counts, "expr_children", 0)
    stmt_child_count = _integer(counts, "stmt_children", 0)
    switch_case_count = _integer(counts, "switch_cases", 0)
    label_count = _integer(counts, "labels", 0)
    if min(expr_count, stmt_count, function_count, expr_child_count,
           stmt_child_count, switch_case_count, label_count) < 0:
        raise ValueError("typed-IR counts must be non-negative")

    exprs = _indexed_records(lines, "expr", expr_count)
    stmts = _indexed_records(lines, "stmt", stmt_count)
    functions = _indexed_records(lines, "function", function_count)
    expr_children = _indexed_records(lines, "expr-child", expr_child_count)
    stmt_children = _indexed_records(lines, "stmt-child", stmt_child_count)
    switch_cases = _indexed_records(lines, "switch-case", switch_case_count)

    for index, expression in exprs.items():
        if "kind" not in expression:
            raise ValueError("expression %d has no kind" % index)
        _expression_edges(index, expression, expr_count)
        child_indexes = _field_range(
            expression, "args_start", "args_count", expr_child_count,
            "expression %d argument" % index,
        )
        for child_index in child_indexes:
            child = _integer(expr_children[child_index], "value")
            if child < 0 or child >= expr_count:
                raise ValueError("expression %d has an invalid argument edge" % index)

    for index, statement in stmts.items():
        kind = statement.get("kind")
        if not kind:
            raise ValueError("statement %d has no kind" % index)
        if kind not in {
            "Block", "Return", "Declaration", "If", "Expression", "For",
            "While", "DoWhile", "Break", "Continue", "Goto", "Label",
            "Switch", "SwitchBreak", "Null",
        }:
            raise ValueError("statement %d has unknown kind %r" % (index, kind))
        expression = _integer(statement, "expr", -1)
        if kind == "Label":
            if expression < 0 or expression >= stmt_count:
                raise ValueError("label %d has an invalid body edge" % index)
        elif expression < -1 or expression >= expr_count:
            raise ValueError("statement %d has an invalid expression edge" % index)
        if kind in ("If", "While", "DoWhile", "Switch", "Expression") and expression < 0:
            raise ValueError("%s statement %d is missing its expression edge" % (kind, index))
        if kind == "For" and expression < 0:
            raise ValueError("for statement %d is missing its condition edge" % index)

        if kind == "Block":
            child_indexes = _field_range(
                statement, "children_start", "children_count", stmt_child_count,
                "block %d" % index,
            )
            for child_index in child_indexes:
                child = _integer(stmt_children[child_index], "value")
                if child < 0 or child >= stmt_count:
                    raise ValueError("block %d has an invalid statement edge" % index)
        elif kind == "Switch":
            child_indexes = _field_range(
                statement, "children_start", "children_count", switch_case_count,
                "switch %d" % index,
            )
            for child_index in child_indexes:
                case = switch_cases[child_index]
                case_value = _integer(case, "value", -1)
                case_body = _integer(case, "body", -1)
                if case_value < -1 or case_value >= expr_count:
                    raise ValueError("switch %d has an invalid case value" % index)
                if case_body < -1 or case_body >= stmt_count:
                    raise ValueError("switch %d has an invalid case body" % index)
        elif kind == "For":
            for field in ("children_start", "aux", "aux2"):
                reference = _integer(statement, field, -1)
                if reference < -1 or reference >= stmt_count:
                    raise ValueError("for statement %d has an invalid %s edge" % (index, field))
            if _integer(statement, "aux", -1) < 0:
                raise ValueError("for statement %d is missing its body edge" % index)
        elif kind in ("If", "While", "DoWhile"):
            for field in ("aux", "aux2"):
                reference = _integer(statement, field, -1)
                if reference < -1 or reference >= stmt_count:
                    raise ValueError("%s statement %d has an invalid %s edge" % (kind, index, field))
            if _integer(statement, "aux", -1) < 0:
                raise ValueError("%s statement %d is missing its body edge" % (kind, index))
        elif kind == "Continue":
            reference = _integer(statement, "aux", -1)
            if reference < -1 or reference >= stmt_count:
                raise ValueError("continue statement %d has an invalid increment edge" % index)
        elif kind == "Goto":
            label = _integer(statement, "aux", -1)
            if label < 0 or label >= label_count:
                raise ValueError("goto statement %d has an invalid label edge" % index)
        elif kind == "Label":
            label = _integer(statement, "aux", -1)
            if label < 0 or label >= label_count:
                raise ValueError("label statement %d has an invalid label ID" % index)

    for index, case in switch_cases.items():
        case_value = _integer(case, "value", -1)
        case_body = _integer(case, "body", -1)
        if case_value < -1 or case_value >= expr_count:
            raise ValueError("switch case %d has an invalid value edge" % index)
        if case_body < 0 or case_body >= stmt_count:
            raise ValueError("switch case %d has an invalid body edge" % index)

    for index, function in functions.items():
        body = _integer(function, "body", -1)
        if body < -1 or body >= stmt_count:
            raise ValueError("function %d has an invalid body edge" % index)

    for index, child in expr_children.items():
        value = _integer(child, "value")
        if value < 0 or value >= expr_count:
            raise ValueError("expression-child %d has an invalid value" % index)
    for index, child in stmt_children.items():
        value = _integer(child, "value")
        if value < 0 or value >= stmt_count:
            raise ValueError("statement-child %d has an invalid value" % index)

    return exprs, stmts, functions, expr_children, stmt_children, switch_cases


def _rewrite_events(lines):
    event_pattern = re.compile(
        r"^rewrite-event source=.* range-start=-?[0-9]+ range-end=-?[0-9]+ "
        r"expression=-?[0-9]+ rule=([a-z][a-z0-9-]*) "
        r"decision=(applied|declined)(?: proof=| reason=).*$"
    )
    events = Counter()
    for line_number, line in enumerate(lines, 1):
        if not line.startswith("rewrite-event "):
            continue
        match = event_pattern.fullmatch(line)
        if not match:
            raise ValueError("malformed rewrite-event record on line %d" % line_number)
        events[(match.group(1), match.group(2))] += 1
    return events


def _statement_children(statement, stmt_children, switch_cases):
    """Return structural statement edges, excluding jump-target guesses."""
    kind = statement["kind"]
    if kind == "Block":
        start = _integer(statement, "children_start", -1)
        count = _integer(statement, "children_count", 0)
        return [
            _integer(stmt_children[child_index], "value")
            for child_index in range(start, start + count)
        ]
    if kind == "If":
        return [
            child for child in (_integer(statement, "aux", -1),
                                _integer(statement, "aux2", -1))
            if child >= 0
        ]
    if kind == "For":
        return [
            child for child in (_integer(statement, "children_start", -1),
                                _integer(statement, "aux", -1),
                                _integer(statement, "aux2", -1))
            if child >= 0
        ]
    if kind in ("While", "DoWhile"):
        return [
            child for child in (_integer(statement, "aux", -1),
                                _integer(statement, "aux2", -1))
            if child >= 0
        ]
    if kind == "Continue":
        child = _integer(statement, "aux", -1)
        return [child] if child >= 0 else []
    if kind == "Label":
        child = _integer(statement, "expr", -1)
        return [child] if child >= 0 else []
    if kind == "Switch":
        start = _integer(statement, "children_start", -1)
        count = _integer(statement, "children_count", 0)
        return [
            body for case_index in range(start, start + count)
            if (body := _integer(switch_cases[case_index], "body", -1)) >= 0
        ]
    return []


def _switches_nested_in_loops(body, stmts, stmt_children, switch_cases):
    """Find reachable switches under a loop in linear graph time."""
    loop_kinds = {"For", "While", "DoWhile"}
    visited = set()
    switches = set()
    stack = [(body, False)]
    while stack:
        index, inside_loop = stack.pop()
        state = (index, inside_loop)
        if state in visited:
            continue
        visited.add(state)
        statement = stmts[index]
        kind = statement["kind"]
        nested = inside_loop or kind in loop_kinds
        if kind == "Switch" and inside_loop:
            switches.add(index)
        stack.extend(
            (child, nested)
            for child in _statement_children(statement, stmt_children, switch_cases)
        )
    return switches


def _case_body_goto_targets(body, stmts, stmt_children):
    """Collect direct goto target IDs from a case or its immediate block."""
    statement = stmts[body]
    if statement["kind"] == "Goto":
        return {_integer(statement, "aux", -1)}
    if statement["kind"] != "Block":
        return set()
    start = _integer(statement, "children_start", -1)
    count = _integer(statement, "children_count", 0)
    return {
        _integer(child, "aux", -1)
        for child_index in range(start, start + count)
        if (child := stmts[_integer(stmt_children[child_index], "value")])["kind"] == "Goto"
    }


def _function_metrics(exprs, stmts, functions, expr_children, stmt_children, switch_cases):
    rows = []
    for function_index, function in functions.items():
        body = _integer(function, "body", -1)
        if body < 0:
            continue

        statement_ids = set()
        expression_roots = set()
        statement_stack = [body]
        while statement_stack:
            index = statement_stack.pop()
            if index in statement_ids:
                continue
            statement_ids.add(index)
            statement = stmts[index]
            kind = statement["kind"]
            expression = _integer(statement, "expr", -1)
            if expression >= 0 and kind != "Label":
                expression_roots.add(expression)

            if kind == "Switch":
                start = _integer(statement, "children_start", -1)
                count = _integer(statement, "children_count", 0)
                for case_index in range(start, start + count):
                    case_value = _integer(switch_cases[case_index], "value", -1)
                    if case_value >= 0:
                        expression_roots.add(case_value)
            statement_stack.extend(
                _statement_children(statement, stmt_children, switch_cases)
            )

        expression_ids = set()
        expression_stack = list(expression_roots)
        while expression_stack:
            index = expression_stack.pop()
            if index in expression_ids:
                continue
            expression_ids.add(index)
            expression = exprs[index]
            expression_stack.extend(_expression_edges(index, expression, len(exprs)))
            start = _integer(expression, "args_start", -1)
            count = _integer(expression, "args_count", 0)
            expression_stack.extend(
                _integer(expr_children[child_index], "value")
                for child_index in range(start, start + count)
            )

        decisions = 0
        declarations = 0
        for index in statement_ids:
            statement = stmts[index]
            kind = statement["kind"]
            if kind == "Declaration":
                declarations += 1
            if kind in ("If", "For", "While", "DoWhile"):
                decisions += 1
            elif kind == "Switch":
                decisions += _integer(statement, "children_count", 0)
        for index in expression_ids:
            expression = exprs[index]
            kind = expression["kind"]
            if kind == "Conditional":
                decisions += 1
            elif kind == "Binary":
                opcode_hex = expression.get("text_hex", "")
                if _decode_hex(opcode_hex, "expression operator") in ("and", "or"):
                    decisions += 1

        unreferenced_declarations = _unreferenced_local_declarations(
            exprs, stmts, expr_children, stmt_children, switch_cases, body
        )
        goto_nodes = sum(1 for index in statement_ids if stmts[index]["kind"] == "Goto")
        label_nodes = sum(1 for index in statement_ids if stmts[index]["kind"] == "Label")
        dispatch_switches = set()
        dispatch_case_arms = 0
        dispatch_nondefault_arms = 0
        dispatch_state_label_targets = 0
        dispatch_max_state_label_targets = 0
        dispatch_switches_with_multiple_state_targets = 0
        reachable_label_ids = {
            _integer(stmts[index], "aux", -1)
            for index in statement_ids
            if stmts[index]["kind"] == "Label"
        }
        if goto_nodes and reachable_label_ids:
            for switch_index in _switches_nested_in_loops(
                body, stmts, stmt_children, switch_cases
            ):
                switch = stmts[switch_index]
                start = _integer(switch, "children_start", -1)
                count = _integer(switch, "children_count", 0)
                goto_arms = 0
                nondefault_goto_arms = 0
                switch_state_label_targets = set()
                for case_index in range(start, start + count):
                    case = switch_cases[case_index]
                    case_body = _integer(case, "body", -1)
                    case_targets = (
                        _case_body_goto_targets(case_body, stmts, stmt_children)
                        if case_body >= 0 else set()
                    )
                    matched_targets = case_targets & reachable_label_ids
                    if matched_targets:
                        goto_arms += 1
                        nondefault_goto_arms += _integer(case, "value", -1) >= 0
                        switch_state_label_targets.update(matched_targets)
                if goto_arms:
                    dispatch_switches.add(switch_index)
                    dispatch_case_arms += goto_arms
                    dispatch_nondefault_arms += nondefault_goto_arms
                    # Count distinct destination labels, not case arms. This is
                    # still only a structural state-label proxy: equal labels
                    # may merge source states, and not every label is a state.
                    target_count = len(switch_state_label_targets)
                    dispatch_state_label_targets += target_count
                    dispatch_max_state_label_targets = max(
                        dispatch_max_state_label_targets, target_count
                    )
                    dispatch_switches_with_multiple_state_targets += target_count > 1

        rows.append({
            "function": function_index,
            "expressions": len(expression_ids),
            "statements": len(statement_ids),
            "decisions": decisions,
            "declarations": declarations,
            "unreferenced_declarations": unreferenced_declarations,
            "goto_nodes": goto_nodes,
            "label_nodes": label_nodes,
            "dispatch_switches": len(dispatch_switches),
            "dispatch_case_arms": dispatch_case_arms,
            "dispatch_nondefault_arms": dispatch_nondefault_arms,
            "dispatch_state_label_targets": dispatch_state_label_targets,
            "dispatch_max_state_label_targets": dispatch_max_state_label_targets,
            "dispatch_switches_with_multiple_state_targets": dispatch_switches_with_multiple_state_targets,
            "statement_ids": statement_ids,
            "expression_ids": expression_ids,
        })

    reachable_statements = set().union(*(row["statement_ids"] for row in rows)) if rows else set()
    reachable_expressions = set().union(*(row["expression_ids"] for row in rows)) if rows else set()
    expression_fingerprints = _expression_fingerprints(
        exprs, expr_children, reachable_expressions
    )
    statement_fingerprints = _statement_fingerprints(
        stmts, expression_fingerprints, stmt_children, switch_cases, reachable_statements
    )
    for row in rows:
        statement_shape_counts = Counter(
            statement_fingerprints[index]
            for index in row["statement_ids"]
            if stmts[index]["kind"] not in ("Break", "Continue", "SwitchBreak", "Null")
        )
        row["duplicate_statement_shapes"] = sum(
            count > 1 for count in statement_shape_counts.values()
        )
        row["duplicate_statement_excess"] = sum(
            count - 1 for count in statement_shape_counts.values()
        )
        row.pop("statement_ids")
        row.pop("expression_ids")
    expression_fingerprints.clear()
    statement_fingerprints.clear()
    reachable_statements.clear()
    reachable_expressions.clear()
    return rows


def _mean(values):
    return "%.3f" % (sum(values) / len(values)) if values else "n/a"


def _p90(values):
    if not values:
        return "n/a"
    ordered = sorted(values)
    return str(ordered[(9 * len(ordered) + 9) // 10 - 1])


def summarize(text):
    parsed = _parse_dump(text)
    rewrite_events = _rewrite_events(text.splitlines())
    rows = _function_metrics(*parsed)
    expressions = [row["expressions"] for row in rows]
    statements = [row["statements"] for row in rows]
    decisions = [row["decisions"] for row in rows]
    declarations = [row["declarations"] for row in rows]
    unreferenced_declarations = [row["unreferenced_declarations"] for row in rows]
    normalized_expressions = [
        row["expressions"] / (1 + row["decisions"]) for row in rows
    ]
    normalized_declarations = [
        row["declarations"] / (1 + row["decisions"]) for row in rows
    ]
    normalized_unreferenced_declarations = [
        row["unreferenced_declarations"] / (1 + row["decisions"]) for row in rows
    ]
    duplicate_shapes = [row["duplicate_statement_shapes"] for row in rows]
    duplicate_excess = [row["duplicate_statement_excess"] for row in rows]
    goto_nodes = [row["goto_nodes"] for row in rows]
    label_nodes = [row["label_nodes"] for row in rows]
    goto_label_nodes = [row["goto_nodes"] + row["label_nodes"] for row in rows]
    dispatch_switches = [row["dispatch_switches"] for row in rows]
    dispatch_case_arms = [row["dispatch_case_arms"] for row in rows]
    dispatch_nondefault_arms = [row["dispatch_nondefault_arms"] for row in rows]
    dispatch_state_label_targets = [row["dispatch_state_label_targets"] for row in rows]
    dispatch_max_state_label_targets = [row["dispatch_max_state_label_targets"] for row in rows]
    dispatch_switches_with_multiple_state_targets = [
        row["dispatch_switches_with_multiple_state_targets"] for row in rows
    ]
    normalized_dispatch_state_label_targets = [
        row["dispatch_state_label_targets"] / (1 + row["decisions"])
        for row in rows
    ]
    dispatch_switch_count = sum(dispatch_switches)
    dispatch_functions = sum(value > 0 for value in dispatch_switches)
    normalized_dispatch_nondefault_arms = [
        row["dispatch_nondefault_arms"] / (1 + row["decisions"])
        for row in rows
    ]
    normalized_goto_label_nodes = [
        (row["goto_nodes"] + row["label_nodes"]) / (1 + row["decisions"])
        for row in rows
    ]
    functions_with_jumps = sum(nodes > 0 for nodes in goto_label_nodes)
    normalized_duplicate_excess = [
        row["duplicate_statement_excess"] / (1 + row["decisions"]) for row in rows
    ]
    total_statements = sum(statements)
    result = [
        ("ir_rewrite_events_total", str(sum(rewrite_events.values()))),
        (
            "ir_rewrite_events_applied",
            str(sum(count for (rule, decision), count in rewrite_events.items()
                    if decision == "applied")),
        ),
        (
            "ir_rewrite_events_declined",
            str(sum(count for (rule, decision), count in rewrite_events.items()
                    if decision == "declined")),
        ),
        (
            "ir_rewrite_events_per_1000_ir_exprs",
            "%.3f" % (1000 * sum(rewrite_events.values()) / len(parsed[0]))
            if parsed[0] else "n/a",
        ),
        ("ir_functions_with_bodies", str(len(rows))),
        ("ir_expr_nodes_per_function_mean", _mean(expressions)),
        ("ir_expr_nodes_per_function_p90", _p90(expressions)),
        ("ir_expr_nodes_per_function_max", str(max(expressions)) if expressions else "n/a"),
        ("ir_stmt_nodes_per_function_mean", _mean(statements)),
        ("ir_stmt_nodes_per_function_p90", _p90(statements)),
        ("ir_stmt_nodes_per_function_max", str(max(statements)) if statements else "n/a"),
        ("ir_decision_nodes_per_function_mean", _mean(decisions)),
        ("ir_decision_nodes_per_function_p90", _p90(decisions)),
        ("ir_decision_nodes_per_function_max", str(max(decisions)) if decisions else "n/a"),
        ("ir_declaration_nodes_per_function_mean", _mean(declarations)),
        ("ir_declaration_nodes_per_function_p90", _p90(declarations)),
        ("ir_declaration_nodes_per_function_max", str(max(declarations)) if declarations else "n/a"),
        ("ir_reachable_goto_nodes_per_function_mean", _mean(goto_nodes)),
        ("ir_reachable_goto_nodes_per_function_p90", _p90(goto_nodes)),
        ("ir_reachable_goto_nodes_per_function_max", str(max(goto_nodes)) if goto_nodes else "n/a"),
        ("ir_reachable_label_nodes_per_function_mean", _mean(label_nodes)),
        ("ir_reachable_label_nodes_per_function_p90", _p90(label_nodes)),
        ("ir_reachable_label_nodes_per_function_max", str(max(label_nodes)) if label_nodes else "n/a"),
        ("ir_functions_with_reachable_goto_or_label", str(functions_with_jumps)),
        (
            "ir_functions_with_reachable_goto_or_label_fraction",
            "%.4f" % (functions_with_jumps / len(rows)) if rows else "n/a",
        ),
        ("ir_goto_label_nodes_per_decision_unit_mean", _mean(normalized_goto_label_nodes)),
        ("ir_loop_switch_goto_candidate_functions", str(sum(value > 0 for value in dispatch_switches))),
        (
            "ir_loop_switch_goto_candidate_function_fraction",
            "%.4f" % (dispatch_functions / len(rows)) if rows else "n/a",
        ),
        ("ir_loop_switch_goto_candidate_switches", str(sum(dispatch_switches))),
        ("ir_loop_switch_goto_candidate_switches_per_function_mean", _mean(dispatch_switches)),
        ("ir_loop_switch_goto_candidate_case_arms", str(sum(dispatch_case_arms))),
        ("ir_loop_switch_goto_candidate_nondefault_arms", str(sum(dispatch_nondefault_arms))),
        (
            "ir_loop_switch_goto_candidate_state_label_targets",
            str(sum(dispatch_state_label_targets)),
        ),
        (
            "ir_loop_switch_goto_candidate_state_label_targets_per_function_mean",
            _mean(dispatch_state_label_targets),
        ),
        (
            "ir_loop_switch_goto_candidate_state_label_targets_per_decision_unit_mean",
            _mean(normalized_dispatch_state_label_targets),
        ),
        (
            "ir_loop_switch_goto_candidate_state_label_targets_per_switch_mean",
            "%.3f" % (sum(dispatch_state_label_targets) / dispatch_switch_count)
            if dispatch_switch_count else "n/a",
        ),
        (
            "ir_loop_switch_goto_candidate_max_state_label_targets_per_switch",
            str(max(dispatch_max_state_label_targets)) if rows else "n/a",
        ),
        (
            "ir_loop_switch_goto_candidate_switches_with_multiple_state_targets",
            str(sum(dispatch_switches_with_multiple_state_targets)),
        ),
        (
            "ir_loop_switch_goto_candidate_nondefault_arms_per_decision_unit_mean",
            _mean(normalized_dispatch_nondefault_arms),
        ),
        ("ir_expr_nodes_per_decision_unit_mean", _mean(normalized_expressions)),
        ("ir_declaration_nodes_per_decision_unit_mean", _mean(normalized_declarations)),
        (
            "ir_unreferenced_local_declarations_per_function_mean",
            _mean(unreferenced_declarations),
        ),
        (
            "ir_unreferenced_local_declarations_per_decision_unit_mean",
            _mean(normalized_unreferenced_declarations),
        ),
        (
            "ir_unreferenced_local_declarations_per_1000_declarations",
            "%.3f" % (1000 * sum(unreferenced_declarations) / sum(declarations))
            if sum(declarations) else "n/a",
        ),
        ("ir_repeated_statement_shapes_per_function_mean", _mean(duplicate_shapes)),
        ("ir_duplicate_statement_shape_excess", str(sum(duplicate_excess))),
        (
            "ir_duplicate_statement_excess_per_decision_unit_mean",
            _mean(normalized_duplicate_excess),
        ),
        (
            "ir_duplicate_statement_excess_per_1000_statements",
            "%.3f" % (1000 * sum(duplicate_excess) / total_statements)
            if total_statements else "n/a",
        ),
    ]
    for (rule, decision), count in sorted(rewrite_events.items()):
        result.append(("ir_rewrite_rule_%s_%s" % (rule, decision), str(count)))
    return "".join("%s: %s\n" % row for row in result)


def main(argv):
    if len(argv) != 2:
        print("usage: quality_ir_metrics.py TYPED_IR_DUMP", file=sys.stderr)
        return 2
    try:
        sys.stdout.write(summarize(Path(argv[1]).read_text(encoding="utf-8")))
    except (OSError, UnicodeError, ValueError) as error:
        print("quality IR metrics: %s" % error, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
