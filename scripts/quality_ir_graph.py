#!/usr/bin/env python3
"""Typed-IR graph helpers and stable structural fingerprints."""

import hashlib
from collections import Counter


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


def _expression_fingerprint_refs(index, expression, expr_children):
    child_fields = {
        "Binary": ("lhs", "rhs"),
        "Sequence": ("lhs", "rhs"),
        "Unary": ("lhs",),
        "Cast": ("lhs",),
        "ArrayIndex": ("lhs", "rhs", "value"),
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
    kind = expression["kind"]
    if kind not in child_fields:
        raise ValueError("expression %d has unknown kind %r" % (index, kind))

    direct = []
    for field in child_fields[kind]:
        reference = _integer(expression, field, -1)
        optional = (kind == "Call" and field == "lhs") or (
            kind == "ArrayIndex" and field == "value"
        )
        if reference < 0 and not optional:
            raise ValueError("expression %d is missing its %s edge" % (index, field))
        direct.append((field, reference))

    start = _integer(expression, "args_start", -1)
    count = _integer(expression, "args_count", 0)
    arguments = [
        _integer(expr_children[child_index], "value")
        for child_index in range(start, start + count)
    ]
    return direct, arguments


def expression_fingerprints(exprs, expr_children, expression_indexes):
    fingerprints = {}
    states = bytearray(len(exprs))
    for root in sorted(expression_indexes):
        if states[root] == 2:
            continue
        direct, arguments = _expression_fingerprint_refs(root, exprs[root], expr_children)
        children = tuple(
            [reference for _, reference in direct if reference >= 0] + arguments
        )
        if any(reference not in expression_indexes for reference in children):
            raise ValueError("reachable expression has an unreachable child edge")
        states[root] = 1
        stack = [[root, children, 0]]
        while stack:
            index, children, child_position = stack[-1]
            if child_position < len(children):
                reference = children[child_position]
                stack[-1][2] += 1
                if states[reference] == 1:
                    raise ValueError("typed-IR expression graph contains a cycle")
                if states[reference] == 0:
                    direct_child, arguments_child = _expression_fingerprint_refs(
                        reference, exprs[reference], expr_children
                    )
                    child_edges = tuple(
                        [ref for _, ref in direct_child if ref >= 0] + arguments_child
                    )
                    if any(ref not in expression_indexes for ref in child_edges):
                        raise ValueError("reachable expression has an unreachable child edge")
                    states[reference] = 1
                    stack.append([reference, child_edges, 0])
                continue

            expression = exprs[index]
            direct, arguments = _expression_fingerprint_refs(index, expression, expr_children)
            kind = expression["kind"]
            scalar_value = None if kind == "ArrayIndex" else _integer(expression, "value", -1)
            scalar_third = None if kind == "Conditional" else _integer(expression, "third", -1)
            shape = (
                kind,
                _decode_hex(expression.get("type_hex", ""), "expression type"),
                _decode_hex(expression.get("text_hex", ""), "expression text"),
                scalar_value,
                scalar_third,
                tuple(
                    (field, None if reference < 0 else fingerprints[reference])
                    for field, reference in direct
                ),
                tuple(fingerprints[reference] for reference in arguments),
            )
            fingerprints[index] = hashlib.sha256(repr(shape).encode("utf-8")).digest()
            states[index] = 2
            stack.pop()
    return fingerprints


def _statement_fingerprint_refs(index, statement, stmt_children, switch_cases):
    kind = statement["kind"]
    expression_ref = _integer(statement, "expr", -1)
    statement_slots = []
    case_slots = []

    if kind == "Block":
        start = _integer(statement, "children_start", -1)
        count = _integer(statement, "children_count", 0)
        statement_slots.extend(
            ("block_child", _integer(stmt_children[child_index], "value"))
            for child_index in range(start, start + count)
        )
    elif kind == "If":
        statement_slots.extend((
            ("then", _integer(statement, "aux", -1)),
            ("else", _integer(statement, "aux2", -1)),
        ))
    elif kind == "For":
        statement_slots.extend((
            ("initializer", _integer(statement, "children_start", -1)),
            ("body", _integer(statement, "aux", -1)),
            ("increment", _integer(statement, "aux2", -1)),
        ))
    elif kind in ("While", "DoWhile"):
        statement_slots.extend((
            ("body", _integer(statement, "aux", -1)),
            ("condition_prelude", _integer(statement, "aux2", -1)),
        ))
    elif kind == "Continue":
        statement_slots.append(("increment", _integer(statement, "aux", -1)))
    elif kind == "Label":
        statement_slots.append(("label_body", expression_ref))
        expression_ref = -1
    elif kind == "Switch":
        start = _integer(statement, "children_start", -1)
        count = _integer(statement, "children_count", 0)
        for case_index in range(start, start + count):
            case = switch_cases[case_index]
            case_slots.append((
                _integer(case, "value", -1),
                _integer(case, "body", -1),
            ))

    stmt_refs = [reference for _, reference in statement_slots if reference >= 0]
    expr_refs = [expression_ref] if expression_ref >= 0 else []
    for case_value, case_body in case_slots:
        if case_value >= 0:
            expr_refs.append(case_value)
        if case_body >= 0:
            stmt_refs.append(case_body)
    return expression_ref, statement_slots, case_slots, stmt_refs, expr_refs


def statement_fingerprints(
    stmts, expr_fingerprints, stmt_children, switch_cases, statement_indexes
):
    fingerprints = {}
    states = bytearray(len(stmts))
    for root in sorted(statement_indexes):
        if states[root] == 2:
            continue
        _, _, _, root_children, root_expr_refs = _statement_fingerprint_refs(
            root, stmts[root], stmt_children, switch_cases
        )
        if any(reference not in expr_fingerprints for reference in root_expr_refs):
            raise ValueError("reachable statement has an unreachable expression edge")
        if any(reference not in statement_indexes for reference in root_children):
            raise ValueError("reachable statement has an unreachable statement edge")
        states[root] = 1
        stack = [[root, tuple(root_children), 0]]
        while stack:
            index, children, child_position = stack[-1]
            if child_position < len(children):
                reference = children[child_position]
                stack[-1][2] += 1
                if states[reference] == 1:
                    raise ValueError("typed-IR statement graph contains a cycle")
                if states[reference] == 0:
                    _, _, _, child_refs, child_expr_refs = _statement_fingerprint_refs(
                        reference, stmts[reference], stmt_children, switch_cases
                    )
                    if any(ref not in expr_fingerprints for ref in child_expr_refs):
                        raise ValueError("reachable statement has an unreachable expression edge")
                    if any(ref not in statement_indexes for ref in child_refs):
                        raise ValueError("reachable statement has an unreachable statement edge")
                    states[reference] = 1
                    stack.append([reference, tuple(child_refs), 0])
                continue

            statement = stmts[index]
            expression_ref, statement_slots, case_slots, _, _ = (
                _statement_fingerprint_refs(index, statement, stmt_children, switch_cases)
            )
            kind = statement["kind"]
            if kind in ("Block", "If", "For", "While", "DoWhile", "Continue", "Switch"):
                scalar_aux = ()
            else:
                scalar_aux = tuple(
                    _integer(statement, field, -1) for field in ("aux", "aux2")
                )

            statement_shape = tuple(
                (role, None if reference < 0 else fingerprints[reference])
                for role, reference in statement_slots
            )
            case_shape = tuple(
                (
                    case_value < 0,
                    None if case_value < 0 else expr_fingerprints[case_value],
                    None if case_body < 0 else fingerprints[case_body],
                )
                for case_value, case_body in case_slots
            )
            shape = (
                kind,
                _decode_hex(statement.get("name_hex", ""), "statement name"),
                _decode_hex(statement.get("type_hex", ""), "statement type"),
                scalar_aux,
                None if expression_ref < 0 else expr_fingerprints[expression_ref],
                statement_shape,
                case_shape,
            )
            fingerprints[index] = hashlib.sha256(repr(shape).encode("utf-8")).digest()
            states[index] = 2
            stack.pop()
    return fingerprints


def unreferenced_local_declarations(
    exprs, stmts, expr_children, stmt_children, switch_cases, body
):
    """Count named local declarations with no Name use resolving to them.

    The typed IR does not yet carry declaration IDs on Name expressions. Rebuild
    the lexical environment while walking statement order so a reference to a
    shadowing declaration does not make an outer declaration look used. This
    deliberately reports a reference signal, not dead-store or liveness facts.
    """
    scopes = []
    scope_tokens = {}
    declarations = {}
    declaration_uses = Counter()
    events = [("statement", body)]
    visited_statements = set()
    active_statements = set()

    def schedule(actions):
        events.extend(reversed(actions))

    def schedule_statement_actions(statement_index, actions):
        events.append(("statement_leave", statement_index))
        schedule(actions)

    def scoped_statement(index, scope_key):
        return [
            ("enter", scope_key),
            ("statement", index),
            ("leave", scope_key),
        ]

    while events:
        event, value = events.pop()
        if event == "enter":
            parent_token = scopes[-1][2] if scopes else 0
            token_key = (parent_token, value)
            scope_token = scope_tokens.get(token_key)
            if scope_token is None:
                scope_token = len(scope_tokens) + 1
                scope_tokens[token_key] = scope_token
            scopes.append((value, {}, scope_token))
            continue
        if event == "leave":
            if not scopes or scopes[-1][0] != value:
                raise ValueError("typed-IR lexical scope stack is inconsistent")
            scopes.pop()
            continue
        if event == "statement_leave":
            active_statements.remove(value)
            continue
        if event == "expression":
            expression_stack = [value]
            expression_seen = set()
            while expression_stack:
                expression_index = expression_stack.pop()
                if expression_index in expression_seen:
                    continue
                expression_seen.add(expression_index)
                expression = exprs[expression_index]
                if expression["kind"] == "Name":
                    name = _decode_hex(
                        expression.get("text_hex", ""), "name expression"
                    )
                    for _, bindings, _ in reversed(scopes):
                        declaration_index = bindings.get(name)
                        if declaration_index is not None:
                            declaration_uses[declaration_index] += 1
                            break
                expression_stack.extend(
                    _expression_edges(expression_index, expression, len(exprs))
                )
                start = _integer(expression, "args_start", -1)
                count = _integer(expression, "args_count", 0)
                expression_stack.extend(
                    _integer(expr_children[child_index], "value")
                    for child_index in range(start, start + count)
                )
            continue

        statement_index = value
        if statement_index in active_statements:
            raise ValueError("typed-IR statement graph contains a cycle")
        scope_token = scopes[-1][2] if scopes else 0
        statement_context = (statement_index, scope_token)
        if statement_context in visited_statements:
            continue
        active_statements.add(statement_index)
        visited_statements.add(statement_context)
        statement = stmts[statement_index]
        kind = statement["kind"]
        expression = _integer(statement, "expr", -1)

        if kind == "Block":
            start = _integer(statement, "children_start", -1)
            count = _integer(statement, "children_count", 0)
            children = [
                _integer(stmt_children[index], "value")
                for index in range(start, start + count)
            ]
            actions = [("enter", ("block", statement_index))]
            actions.extend(("statement", child) for child in children)
            actions.append(("leave", ("block", statement_index)))
            schedule_statement_actions(statement_index, actions)
            continue

        actions = []
        if kind == "Declaration":
            name = _decode_hex(statement.get("name_hex", ""), "declaration name")
            if name:
                if not scopes:
                    raise ValueError("local declaration appears outside a lexical scope")
                declarations[statement_index] = name
                scopes[-1][1][name] = statement_index
                scope_key, bindings, parent_token = scopes[-1]
                token_key = (parent_token, ("declaration", statement_index, name))
                scope_token = scope_tokens.get(token_key)
                if scope_token is None:
                    scope_token = len(scope_tokens) + 1
                    scope_tokens[token_key] = scope_token
                scopes[-1] = (scope_key, bindings, scope_token)
        if expression >= 0 and kind != "Label":
            actions.append(("expression", expression))

        if kind == "If":
            then_index = _integer(statement, "aux", -1)
            else_index = _integer(statement, "aux2", -1)
            if then_index >= 0:
                actions.extend(scoped_statement(then_index, ("if-then", statement_index)))
            if else_index >= 0:
                actions.extend(scoped_statement(else_index, ("if-else", statement_index)))
        elif kind == "For":
            init_index = _integer(statement, "children_start", -1)
            body_index = _integer(statement, "aux", -1)
            increment_index = _integer(statement, "aux2", -1)
            loop_actions = [("enter", ("for", statement_index))]
            if init_index >= 0:
                loop_actions.append(("statement", init_index))
            if expression >= 0:
                loop_actions.append(("expression", expression))
            if body_index >= 0:
                loop_actions.extend(
                    scoped_statement(body_index, ("for-body", statement_index))
                )
            if increment_index >= 0:
                loop_actions.append(("statement", increment_index))
            loop_actions.append(("leave", ("for", statement_index)))
            actions = loop_actions
        elif kind in ("While", "DoWhile"):
            body_index = _integer(statement, "aux", -1)
            prelude_index = _integer(statement, "aux2", -1)
            body_actions = []
            if body_index >= 0:
                body_actions.extend(
                    scoped_statement(body_index, (kind, statement_index))
                )
            if kind == "DoWhile":
                actions = body_actions
                if prelude_index >= 0:
                    actions.append(("statement", prelude_index))
                if expression >= 0:
                    actions.append(("expression", expression))
            else:
                actions = []
                if prelude_index >= 0:
                    actions.append(("statement", prelude_index))
                if expression >= 0:
                    actions.append(("expression", expression))
                actions.extend(body_actions)
        elif kind == "Switch":
            start = _integer(statement, "children_start", -1)
            count = _integer(statement, "children_count", 0)
            switch_actions = []
            if expression >= 0:
                switch_actions.append(("expression", expression))
            switch_actions.append(("enter", ("switch", statement_index)))
            for case_index in range(start, start + count):
                case = switch_cases[case_index]
                case_value = _integer(case, "value", -1)
                case_body = _integer(case, "body", -1)
                if case_value >= 0:
                    switch_actions.append(("expression", case_value))
                if case_body >= 0:
                    switch_actions.append(("statement", case_body))
            switch_actions.append(("leave", ("switch", statement_index)))
            actions = switch_actions
        elif kind == "Continue":
            increment_index = _integer(statement, "aux", -1)
            if increment_index >= 0:
                actions.append(("statement", increment_index))
        elif kind == "Label":
            label_body = expression
            if label_body >= 0:
                actions.append(("statement", label_body))

        schedule_statement_actions(statement_index, actions)

    return sum(
        1
        for declaration_index, name in declarations.items()
        if declaration_uses[declaration_index] == 0
    )
