#!/usr/bin/env python3
"""Compute per-function structural metrics from the typed-IR v13 dump."""

import sys
from pathlib import Path


def _integer(fields, name, default=None):
    value = fields.get(name)
    if value is None:
        if default is not None:
            return default
        raise ValueError("missing %s field" % name)
    try:
        return int(value, 10)
    except ValueError as error:
        raise ValueError("invalid integer field %s=%r" % (name, value)) from error


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


def _field_range(fields, start_name, count_name, upper_bound, label):
    start = _integer(fields, start_name, -1)
    count = _integer(fields, count_name, 0)
    if start < -1 or count < 0 or start > upper_bound:
        raise ValueError("%s range is outside its child table" % label)
    if count and (start < 0 or start + count > upper_bound):
        raise ValueError("%s range is outside its child table" % label)
    return range(start, start + count) if count else range(0)


def _decode_hex(value, label):
    try:
        return bytes.fromhex(value).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as error:
        raise ValueError("invalid %s hex field" % label) from error


def _expression_edges(index, expression, expression_count):
    kind = expression["kind"]
    edge_fields = {
        "Binary": ("lhs", "rhs"),
        "Sequence": ("lhs", "rhs"),
        "Unary": ("lhs",),
        "Cast": ("lhs",),
        "ArrayIndex": ("lhs", "rhs"),
        "Conditional": ("lhs", "rhs", "third"),
        "Member": ("lhs",),
        "Call": ("lhs",),
        "Name": (),
        "Integer": (),
        "Floating": (),
        "String": (),
        "Character": (),
        "Sizeof": (),
        "ObjectSizeRemaining": (),
        "Aggregate": (),
        "Null": (),
        "Zeroed": (),
    }
    if kind not in edge_fields:
        raise ValueError("expression %d has unknown kind %r" % (index, kind))

    edges = []
    for field in edge_fields[kind]:
        reference = _integer(expression, field, -1)
        if reference == -1 and kind == "Call" and field == "lhs":
            continue
        if reference < 0 or reference >= expression_count:
            raise ValueError("expression %d has an invalid %s edge" % (index, field))
        edges.append(reference)

    if kind == "ArrayIndex":
        side_effect = _integer(expression, "value", -1)
        if side_effect < -1 or side_effect >= expression_count:
            raise ValueError("array-index expression %d has an invalid side-effect edge" % index)
        if side_effect >= 0:
            edges.append(side_effect)
    return edges


def _parse_dump(text):
    lines = text.splitlines()
    if not lines or lines[0] != "typed-ir-v13":
        raise ValueError("expected typed-ir-v13 dump")
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

            if kind == "Block":
                start = _integer(statement, "children_start", -1)
                count = _integer(statement, "children_count", 0)
                statement_stack.extend(
                    _integer(stmt_children[child_index], "value")
                    for child_index in range(start, start + count)
                )
            elif kind == "If":
                statement_stack.extend(
                    child for child in (_integer(statement, "aux", -1),
                                        _integer(statement, "aux2", -1)) if child >= 0
                )
            elif kind == "For":
                statement_stack.extend(
                    child for child in (_integer(statement, "children_start", -1),
                                        _integer(statement, "aux", -1),
                                        _integer(statement, "aux2", -1)) if child >= 0
                )
            elif kind in ("While", "DoWhile"):
                statement_stack.extend(
                    child for child in (_integer(statement, "aux", -1),
                                        _integer(statement, "aux2", -1)) if child >= 0
                )
            elif kind == "Continue":
                child = _integer(statement, "aux", -1)
                if child >= 0:
                    statement_stack.append(child)
            elif kind == "Label":
                child = _integer(statement, "expr", -1)
                if child >= 0:
                    statement_stack.append(child)
            elif kind == "Switch":
                start = _integer(statement, "children_start", -1)
                count = _integer(statement, "children_count", 0)
                for case_index in range(start, start + count):
                    case = switch_cases[case_index]
                    case_value = _integer(case, "value", -1)
                    case_body = _integer(case, "body", -1)
                    if case_value >= 0:
                        expression_roots.add(case_value)
                    if case_body >= 0:
                        statement_stack.append(case_body)

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
        for index in statement_ids:
            statement = stmts[index]
            kind = statement["kind"]
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

        rows.append({
            "function": function_index,
            "expressions": len(expression_ids),
            "statements": len(statement_ids),
            "decisions": decisions,
        })
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
    rows = _function_metrics(*parsed)
    expressions = [row["expressions"] for row in rows]
    statements = [row["statements"] for row in rows]
    decisions = [row["decisions"] for row in rows]
    normalized_expressions = [
        row["expressions"] / (1 + row["decisions"]) for row in rows
    ]
    result = [
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
        ("ir_expr_nodes_per_decision_unit_mean", _mean(normalized_expressions)),
    ]
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
