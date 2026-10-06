#!/usr/bin/env python3
"""Unit tests for structural, per-function quality metrics."""

import unittest

from quality_ir_metrics import summarize


def sample_dump():
    return "\n".join([
        "typed-ir-v16",
        "counts exprs=7 expr_children=0 stmts=8 stmt_children=2 functions=2 switch_cases=2",
        "function 0 body=0",
        "function 1 body=4",
        "expr 0 kind=Binary lhs=1 rhs=2 third=-1 args_start=-1 args_count=0 text_hex=616e64",
        "expr 1 kind=Integer lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 text_hex=31",
        "expr 2 kind=Integer lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 text_hex=32",
        "expr 3 kind=Name lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 text_hex=73656c6563746f72",
        "expr 4 kind=Integer lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 text_hex=31",
        "expr 5 kind=Integer lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 text_hex=35",
        "expr 6 kind=Integer lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 text_hex=36",
        "stmt 0 kind=Block expr=-1 aux=-1 aux2=-1 children_start=0 children_count=2",
        "stmt 1 kind=If expr=0 aux=2 aux2=3",
        "stmt 2 kind=Return expr=1",
        "stmt 3 kind=Return expr=2",
        "stmt 4 kind=Switch expr=3 children_start=0 children_count=2",
        "stmt 5 kind=Return expr=5",
        "stmt 6 kind=Return expr=6",
        "stmt 7 kind=Declaration expr=-1 aux=-1 aux2=-1 children_start=-1 children_count=0 name_hex=6c6f63616c",
        "stmt-child 0 value=1",
        "stmt-child 1 value=7",
        "switch-case 0 value=4 body=5 default=false",
        "switch-case 1 value=-1 body=6 default=true",
    ]) + "\n"


class QualityIrMetricTests(unittest.TestCase):
    def test_structurally_flags_loop_switch_goto_dispatch_candidates(self):
        dump = "\n".join([
            "typed-ir-v16",
            "counts exprs=4 stmts=12 stmt_children=4 functions=1 switch_cases=3 labels=3",
            "function 0 body=0",
            "expr 0 kind=Integer lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 value=1 text_hex=31",
            "expr 1 kind=Name lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 value=0 text_hex=7374617465",
            "expr 2 kind=Integer lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 value=0 text_hex=30",
            "expr 3 kind=Integer lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 value=1 text_hex=32",
            "stmt 0 kind=Block expr=-1 aux=-1 aux2=-1 children_start=0 children_count=4",
            "stmt 1 kind=While expr=0 aux=2 aux2=-1",
            "stmt 2 kind=Switch expr=1 children_start=0 children_count=3",
            "stmt 3 kind=Goto expr=-1 aux=0 aux2=-1",
            "stmt 4 kind=Goto expr=-1 aux=1 aux2=-1",
            "stmt 5 kind=Goto expr=-1 aux=2 aux2=-1",
            "stmt 6 kind=Label expr=7 aux=0 name_hex=73746174655f30",
            "stmt 7 kind=Return expr=2 aux=-1 aux2=-1",
            "stmt 8 kind=Label expr=9 aux=1 name_hex=73746174655f31",
            "stmt 9 kind=Return expr=2 aux=-1 aux2=-1",
            "stmt 10 kind=Label expr=11 aux=2 name_hex=73746174655f32",
            "stmt 11 kind=Return expr=2 aux=-1 aux2=-1",
            "stmt-child 0 value=1",
            "stmt-child 1 value=6",
            "stmt-child 2 value=8",
            "stmt-child 3 value=10",
            "switch-case 0 value=2 body=3 default=false",
            "switch-case 1 value=3 body=4 default=false",
            "switch-case 2 value=-1 body=5 default=true",
        ]) + "\n"
        report = summarize(dump)
        self.assertIn("ir_loop_switch_goto_candidate_functions: 1\n", report)
        self.assertIn("ir_loop_switch_goto_candidate_switches: 1\n", report)
        self.assertIn("ir_loop_switch_goto_candidate_function_fraction: 1.0000\n", report)
        self.assertIn("ir_loop_switch_goto_candidate_switches_per_function_mean: 1.000\n", report)
        self.assertIn("ir_loop_switch_goto_candidate_case_arms: 3\n", report)
        self.assertIn("ir_loop_switch_goto_candidate_nondefault_arms: 2\n", report)
        self.assertIn("ir_loop_switch_goto_candidate_state_label_targets: 3\n", report)
        self.assertIn("ir_loop_switch_goto_candidate_state_label_targets_per_function_mean: 3.000\n", report)
        self.assertIn("ir_loop_switch_goto_candidate_state_label_targets_per_decision_unit_mean: 0.600\n", report)
        self.assertIn("ir_loop_switch_goto_candidate_state_label_targets_per_switch_mean: 3.000\n", report)
        self.assertIn("ir_loop_switch_goto_candidate_max_state_label_targets_per_switch: 3\n", report)
        self.assertIn("ir_loop_switch_goto_candidate_switches_with_multiple_state_targets: 1\n", report)
        self.assertIn("ir_loop_switch_goto_candidate_nondefault_arms_per_decision_unit_mean: 0.400\n", report)

    def test_multiple_dispatch_arms_to_one_label_count_as_one_candidate_target(self):
        dump = "\n".join([
            "typed-ir-v16",
            "counts exprs=4 stmts=7 stmt_children=2 functions=1 switch_cases=2 labels=1",
            "function 0 body=0",
            "expr 0 kind=Integer lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 value=1 text_hex=31",
            "expr 1 kind=Name lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 value=0 text_hex=7374617465",
            "expr 2 kind=Integer lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 value=0 text_hex=30",
            "expr 3 kind=Integer lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 value=1 text_hex=32",
            "stmt 0 kind=Block expr=-1 aux=-1 aux2=-1 children_start=0 children_count=2",
            "stmt 1 kind=While expr=0 aux=2 aux2=-1",
            "stmt 2 kind=Switch expr=1 children_start=0 children_count=2",
            "stmt 3 kind=Goto expr=-1 aux=0 aux2=-1",
            "stmt 4 kind=Goto expr=-1 aux=0 aux2=-1",
            "stmt 5 kind=Label expr=6 aux=0 name_hex=7374617465",
            "stmt 6 kind=Return expr=2 aux=-1 aux2=-1",
            "stmt-child 0 value=1",
            "stmt-child 1 value=5",
            "switch-case 0 value=2 body=3 default=false",
            "switch-case 1 value=3 body=4 default=false",
        ]) + "\n"
        report = summarize(dump)
        self.assertIn("ir_loop_switch_goto_candidate_case_arms: 2\n", report)
        self.assertIn("ir_loop_switch_goto_candidate_state_label_targets: 1\n", report)
        self.assertIn("ir_loop_switch_goto_candidate_switches_with_multiple_state_targets: 0\n", report)

    def test_does_not_call_unrelated_jumps_and_loop_switch_a_dispatcher(self):
        dump = "\n".join([
            "typed-ir-v16",
            "counts exprs=3 stmts=8 stmt_children=3 functions=1 switch_cases=2 labels=2",
            "function 0 body=0",
            "expr 0 kind=Integer lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 value=1 text_hex=31",
            "expr 1 kind=Name lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 value=0 text_hex=73656c6563746f72",
            "expr 2 kind=Integer lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 value=0 text_hex=30",
            "stmt 0 kind=Block expr=-1 aux=-1 aux2=-1 children_start=0 children_count=3",
            "stmt 1 kind=While expr=0 aux=2 aux2=-1",
            "stmt 2 kind=Switch expr=1 children_start=0 children_count=2",
            "stmt 3 kind=Goto expr=-1 aux=1 aux2=-1",
            "stmt 4 kind=Return expr=2 aux=-1 aux2=-1",
            "stmt 5 kind=Goto expr=-1 aux=0 aux2=-1",
            "stmt 6 kind=Label expr=7 aux=0 name_hex=6c6162656c",
            "stmt 7 kind=Return expr=2 aux=-1 aux2=-1",
            "stmt-child 0 value=1",
            "stmt-child 1 value=5",
            "stmt-child 2 value=6",
            "switch-case 0 value=2 body=3 default=false",
            "switch-case 1 value=-1 body=4 default=true",
        ]) + "\n"
        report = summarize(dump)
        self.assertIn("ir_functions_with_reachable_goto_or_label: 1\n", report)
        self.assertIn("ir_loop_switch_goto_candidate_functions: 0\n", report)
        self.assertIn("ir_loop_switch_goto_candidate_switches: 0\n", report)
        self.assertIn("ir_loop_switch_goto_candidate_case_arms: 0\n", report)
        self.assertIn("ir_loop_switch_goto_candidate_function_fraction: 0.0000\n", report)
        self.assertIn("ir_loop_switch_goto_candidate_nondefault_arms_per_decision_unit_mean: 0.000\n", report)

    def test_counts_rewrite_events_before_ir_header_with_paths_containing_spaces(self):
        dump = "\n".join([
            "rewrite-event source=/tmp/source dir/input.c range-start=1 range-end=9 expression=3 rule=constant-condition decision=applied proof=target-abi-integer-constant-condition",
            "rewrite-event source=/tmp/source dir/input.c range-start=10 range-end=17 expression=4 rule=identity-binary decision=declined reason=side-effecting-operand",
            sample_dump().rstrip("\n"),
        ]) + "\n"
        report = summarize(dump)
        self.assertIn("ir_rewrite_events_total: 2\n", report)
        self.assertIn("ir_rewrite_events_applied: 1\n", report)
        self.assertIn("ir_rewrite_events_declined: 1\n", report)
        self.assertIn("ir_rewrite_events_per_1000_ir_exprs: 285.714\n", report)
        self.assertIn("ir_rewrite_rule_constant-condition_applied: 1\n", report)
        self.assertIn("ir_rewrite_rule_identity-binary_declined: 1\n", report)

    def test_rejects_malformed_rewrite_event_records(self):
        malformed = "rewrite-event source=input.c range-start=1 range-end=2 expression=0 rule=bad decision=maybe proof=unknown\n"
        with self.assertRaisesRegex(ValueError, "malformed rewrite-event"):
            summarize(malformed + sample_dump())

    def test_reports_reachable_per_function_distributions(self):
        report = summarize(sample_dump())
        self.assertIn("ir_functions_with_bodies: 2\n", report)
        self.assertIn("ir_expr_nodes_per_function_mean: 3.500\n", report)
        self.assertIn("ir_expr_nodes_per_function_p90: 4\n", report)
        self.assertIn("ir_stmt_nodes_per_function_mean: 4.000\n", report)
        self.assertIn("ir_stmt_nodes_per_function_p90: 5\n", report)
        self.assertIn("ir_stmt_nodes_per_function_max: 5\n", report)
        self.assertIn("ir_decision_nodes_per_function_mean: 2.000\n", report)
        self.assertIn("ir_decision_nodes_per_function_max: 2\n", report)
        self.assertIn("ir_declaration_nodes_per_function_mean: 0.500\n", report)
        self.assertIn("ir_declaration_nodes_per_function_p90: 1\n", report)
        self.assertIn("ir_declaration_nodes_per_function_max: 1\n", report)
        self.assertIn("ir_expr_nodes_per_decision_unit_mean: 1.167\n", report)
        self.assertIn("ir_declaration_nodes_per_decision_unit_mean: 0.167\n", report)
        self.assertIn("ir_unreferenced_local_declarations_per_function_mean: 0.500\n", report)
        self.assertIn("ir_duplicate_statement_shape_excess: 0\n", report)
        self.assertIn("ir_duplicate_statement_excess_per_1000_statements: 0.000\n", report)

    def test_counts_exact_repeated_statement_shapes_only_within_each_function(self):
        dump = "\n".join([
            "typed-ir-v16",
            "counts exprs=4 expr_children=0 stmts=6 stmt_children=4 functions=2",
            "function 0 body=0",
            "function 1 body=3",
            "expr 0 kind=Name lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 value=0 text_hex=76616c7565",
            "expr 1 kind=Name lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 value=0 text_hex=76616c7565",
            "expr 2 kind=Name lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 value=0 text_hex=6f74686572",
            "expr 3 kind=Name lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 value=0 text_hex=76616c7565",
            "stmt 0 kind=Block expr=-1 aux=-1 aux2=-1 children_start=0 children_count=2",
            "stmt 1 kind=Return expr=0 aux=-1 aux2=-1",
            "stmt 2 kind=Return expr=1 aux=-1 aux2=-1",
            "stmt 3 kind=Block expr=-1 aux=-1 aux2=-1 children_start=2 children_count=2",
            "stmt 4 kind=Return expr=2 aux=-1 aux2=-1",
            "stmt 5 kind=Return expr=3 aux=-1 aux2=-1",
            "stmt-child 0 value=1",
            "stmt-child 1 value=2",
            "stmt-child 2 value=4",
            "stmt-child 3 value=5",
        ]) + "\n"
        report = summarize(dump)
        self.assertIn("ir_repeated_statement_shapes_per_function_mean: 0.500\n", report)
        self.assertIn("ir_duplicate_statement_shape_excess: 1\n", report)
        self.assertIn("ir_duplicate_statement_excess_per_decision_unit_mean: 0.500\n", report)
        self.assertIn("ir_duplicate_statement_excess_per_1000_statements: 166.667\n", report)

    def test_reports_local_names_absent_from_name_nodes_without_string_false_matches(self):
        dump = "\n".join([
            "typed-ir-v16",
            "counts exprs=2 expr_children=0 stmts=5 stmt_children=4 functions=1",
            "function 0 body=0",
            "expr 0 kind=Name lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 value=0 text_hex=75736564",
            "expr 1 kind=String lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 text_hex=64656164",
            "stmt 0 kind=Block expr=-1 aux=-1 aux2=-1 children_start=0 children_count=4",
            "stmt 1 kind=Declaration expr=-1 aux=-1 aux2=-1 name_hex=64656164 type_hex=693332",
            "stmt 2 kind=Declaration expr=-1 aux=-1 aux2=-1 name_hex=75736564 type_hex=693332",
            "stmt 3 kind=Return expr=0 aux=-1 aux2=-1",
            "stmt 4 kind=Return expr=1 aux=-1 aux2=-1",
            "stmt-child 0 value=1",
            "stmt-child 1 value=2",
            "stmt-child 2 value=3",
            "stmt-child 3 value=4",
        ]) + "\n"
        report = summarize(dump)
        self.assertIn("ir_unreferenced_local_declarations_per_function_mean: 1.000\n", report)
        self.assertIn("ir_unreferenced_local_declarations_per_decision_unit_mean: 1.000\n", report)
        self.assertIn("ir_unreferenced_local_declarations_per_1000_declarations: 500.000\n", report)

    def test_unreferenced_local_metric_resolves_shadowed_name_to_inner_binding(self):
        dump = "\n".join([
            "typed-ir-v16",
            "counts exprs=1 stmts=5 stmt_children=4 functions=1",
            "function 0 body=0",
            "expr 0 kind=Name lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 text_hex=78",
            "stmt 0 kind=Block expr=-1 children_start=0 children_count=2",
            "stmt 1 kind=Declaration expr=-1 name_hex=78 type_hex=693332",
            "stmt 2 kind=Block expr=-1 children_start=2 children_count=2",
            "stmt 3 kind=Declaration expr=-1 name_hex=78 type_hex=693332",
            "stmt 4 kind=Return expr=0",
            "stmt-child 0 value=1",
            "stmt-child 1 value=2",
            "stmt-child 2 value=3",
            "stmt-child 3 value=4",
        ]) + "\n"
        report = summarize(dump)
        self.assertIn("ir_unreferenced_local_declarations_per_function_mean: 1.000\n", report)

    def test_unreferenced_local_metric_does_not_leak_bindings_between_sibling_blocks(self):
        dump = "\n".join([
            "typed-ir-v16",
            "counts exprs=1 stmts=5 stmt_children=4 functions=1",
            "function 0 body=0",
            "expr 0 kind=Name lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 text_hex=78",
            "stmt 0 kind=Block expr=-1 children_start=0 children_count=2",
            "stmt 1 kind=Block expr=-1 children_start=2 children_count=1",
            "stmt 2 kind=Declaration expr=-1 name_hex=78 type_hex=693332",
            "stmt 3 kind=Block expr=-1 children_start=3 children_count=1",
            "stmt 4 kind=Return expr=0",
            "stmt-child 0 value=1",
            "stmt-child 1 value=3",
            "stmt-child 2 value=2",
            "stmt-child 3 value=4",
        ]) + "\n"
        report = summarize(dump)
        self.assertIn("ir_unreferenced_local_declarations_per_function_mean: 1.000\n", report)

    def test_unreferenced_local_metric_tracks_environment_changes_for_shared_statements(self):
        dump = "\n".join([
            "typed-ir-v16",
            "counts exprs=1 stmts=3 stmt_children=3 functions=1",
            "function 0 body=0",
            "expr 0 kind=Name lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 text_hex=78",
            "stmt 0 kind=Block expr=-1 children_start=0 children_count=3",
            "stmt 1 kind=Declaration expr=-1 name_hex=78 type_hex=693332",
            "stmt 2 kind=Return expr=0",
            "stmt-child 0 value=2",
            "stmt-child 1 value=1",
            "stmt-child 2 value=2",
        ]) + "\n"
        report = summarize(dump)
        self.assertIn("ir_unreferenced_local_declarations_per_function_mean: 0.000\n", report)

    def test_unreferenced_local_metric_counts_outer_and_inner_uses_separately(self):
        dump = "\n".join([
            "typed-ir-v16",
            "counts exprs=2 stmts=6 stmt_children=5 functions=1",
            "function 0 body=0",
            "expr 0 kind=Name lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 text_hex=78",
            "expr 1 kind=Name lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 text_hex=78",
            "stmt 0 kind=Block expr=-1 children_start=0 children_count=3",
            "stmt 1 kind=Declaration expr=-1 name_hex=78 type_hex=693332",
            "stmt 2 kind=Block expr=-1 children_start=3 children_count=2",
            "stmt 3 kind=Declaration expr=-1 name_hex=78 type_hex=693332",
            "stmt 4 kind=Return expr=0",
            "stmt 5 kind=Return expr=1",
            "stmt-child 0 value=1",
            "stmt-child 1 value=2",
            "stmt-child 2 value=5",
            "stmt-child 3 value=3",
            "stmt-child 4 value=4",
        ]) + "\n"
        report = summarize(dump)
        self.assertIn("ir_unreferenced_local_declarations_per_function_mean: 0.000\n", report)

    def test_unreferenced_local_metric_respects_for_initializer_scope(self):
        dump = "\n".join([
            "typed-ir-v16",
            "counts exprs=2 stmts=4 stmt_children=1 functions=1",
            "function 0 body=0",
            "expr 0 kind=Name lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 text_hex=69",
            "expr 1 kind=Name lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 text_hex=69",
            "stmt 0 kind=Block expr=-1 children_start=0 children_count=1",
            "stmt 1 kind=For expr=0 aux=2 aux2=-1 children_start=3",
            "stmt 2 kind=Return expr=1",
            "stmt 3 kind=Declaration expr=-1 name_hex=69 type_hex=693332",
            "stmt-child 0 value=1",
        ]) + "\n"
        report = summarize(dump)
        self.assertIn("ir_unreferenced_local_declarations_per_function_mean: 0.000\n", report)

    def test_for_initializer_binding_does_not_leak_after_loop(self):
        dump = "\n".join([
            "typed-ir-v16",
            "counts exprs=2 stmts=5 stmt_children=2 functions=1",
            "function 0 body=0",
            "expr 0 kind=Integer lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 value=1 text_hex=31",
            "expr 1 kind=Name lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 text_hex=69",
            "stmt 0 kind=Block expr=-1 children_start=0 children_count=2",
            "stmt 1 kind=For expr=0 aux=2 aux2=-1 children_start=4",
            "stmt 2 kind=Null expr=-1",
            "stmt 3 kind=Return expr=1",
            "stmt 4 kind=Declaration expr=-1 name_hex=69 type_hex=693332",
            "stmt-child 0 value=1",
            "stmt-child 1 value=3",
        ]) + "\n"
        report = summarize(dump)
        self.assertIn("ir_unreferenced_local_declarations_per_function_mean: 1.000\n", report)

    def test_local_scope_walk_handles_deep_statement_nesting_iteratively(self):
        statement_count = 1200
        lines = [
            "typed-ir-v16",
            "counts exprs=1 stmts=%d stmt_children=%d functions=1" % (
                statement_count, statement_count - 1
            ),
            "function 0 body=0",
            "expr 0 kind=Name lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 text_hex=78",
        ]
        lines.extend(
            "stmt %d kind=Block expr=-1 children_start=%d children_count=1"
            % (index, index)
            for index in range(statement_count - 1)
        )
        lines.append("stmt %d kind=Return expr=0" % (statement_count - 1))
        lines.extend(
            "stmt-child %d value=%d" % (index, index + 1)
            for index in range(statement_count - 1)
        )
        report = summarize("\n".join(lines) + "\n")
        self.assertIn("ir_unreferenced_local_declarations_per_function_mean: 0.000\n", report)

    def test_duplicate_fingerprints_fail_closed_on_expression_or_statement_cycles(self):
        expression_cycle = "\n".join([
            "typed-ir-v16",
            "counts exprs=1 stmts=1 functions=1",
            "function 0 body=0",
            "expr 0 kind=Unary lhs=0 rhs=-1 third=-1 args_start=-1 args_count=0",
            "stmt 0 kind=Return expr=0",
        ]) + "\n"
        with self.assertRaisesRegex(ValueError, "expression graph contains a cycle"):
            summarize(expression_cycle)

        statement_cycle = "\n".join([
            "typed-ir-v16",
            "counts exprs=1 stmts=2 stmt_children=1 functions=1",
            "function 0 body=0",
            "expr 0 kind=Integer lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0",
            "stmt 0 kind=Block expr=-1 children_start=0 children_count=1",
            "stmt 1 kind=If expr=0 aux=0 aux2=-1",
            "stmt-child 0 value=1",
        ]) + "\n"
        with self.assertRaisesRegex(ValueError, "statement graph contains a cycle"):
            summarize(statement_cycle)

    def test_fingerprints_handle_deep_expression_chains_without_python_recursion(self):
        expression_count = 1500
        lines = [
            "typed-ir-v16",
            "counts exprs=%d stmts=1 functions=1" % expression_count,
            "function 0 body=0",
            "expr 0 kind=Integer lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 value=0 text_hex=31",
        ]
        lines.extend(
            "expr %d kind=Unary lhs=%d rhs=-1 third=-1 args_start=-1 args_count=0 value=0 text_hex=2d"
            % (index, index - 1)
            for index in range(1, expression_count)
        )
        lines.append("stmt 0 kind=Return expr=%d" % (expression_count - 1))
        report = summarize("\n".join(lines) + "\n")
        self.assertIn("ir_expr_nodes_per_function_mean: 1500.000\n", report)

    def test_ignores_bodyless_functions_and_returns_n_a_for_empty_distribution(self):
        dump = "\n".join([
            "typed-ir-v16",
            "counts exprs=0 stmts=0 functions=1",
            "function 0 body=-1",
        ]) + "\n"
        report = summarize(dump)
        self.assertIn("ir_functions_with_bodies: 0\n", report)
        self.assertIn("ir_expr_nodes_per_function_mean: n/a\n", report)
        self.assertIn("ir_decision_nodes_per_function_max: n/a\n", report)
        self.assertIn("ir_reachable_goto_nodes_per_function_mean: n/a\n", report)
        self.assertIn("ir_loop_switch_goto_candidate_function_fraction: n/a\n", report)
        self.assertIn("ir_loop_switch_goto_candidate_switches_per_function_mean: n/a\n", report)
        self.assertIn("ir_loop_switch_goto_candidate_state_label_targets_per_function_mean: n/a\n", report)
        self.assertIn("ir_loop_switch_goto_candidate_state_label_targets_per_switch_mean: n/a\n", report)
        self.assertIn("ir_loop_switch_goto_candidate_max_state_label_targets_per_switch: n/a\n", report)
        self.assertIn("ir_loop_switch_goto_candidate_nondefault_arms_per_decision_unit_mean: n/a\n", report)
        self.assertIn("ir_reachable_label_nodes_per_function_mean: n/a\n", report)
        self.assertIn("ir_functions_with_reachable_goto_or_label_fraction: n/a\n", report)
        self.assertIn("ir_declaration_nodes_per_function_max: n/a\n", report)
        self.assertIn("ir_unreferenced_local_declarations_per_function_mean: n/a\n", report)
        self.assertIn("ir_unreferenced_local_declarations_per_1000_declarations: n/a\n", report)
        self.assertIn("ir_duplicate_statement_shape_excess: 0\n", report)
        self.assertIn("ir_duplicate_statement_excess_per_1000_statements: n/a\n", report)

    def test_rejects_malformed_edges_instead_of_underreporting(self):
        dump = sample_dump().replace("stmt-child 0 value=1", "stmt-child 0 value=99")
        with self.assertRaisesRegex(ValueError, "invalid statement edge"):
            summarize(dump)

    def test_rejects_duplicate_ids(self):
        dump = sample_dump().replace(
            "function 1 body=4", "function 0 body=4"
        )
        with self.assertRaisesRegex(ValueError, "duplicate function record"):
            summarize(dump)

    def test_follows_array_index_side_effect_expression(self):
        dump = "\n".join([
            "typed-ir-v16",
            "counts exprs=5 stmts=1 functions=1",
            "function 0 body=0",
            "expr 0 kind=ArrayIndex lhs=2 rhs=3 third=1 args_start=-1 args_count=0 value=4 text_hex=",
            "expr 1 kind=Call lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 value=0 text_hex=",
            "expr 2 kind=Name lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 value=0 text_hex=78",
            "expr 3 kind=Integer lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 value=0 text_hex=31",
            "expr 4 kind=Call lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 value=0 text_hex=",
            "stmt 0 kind=Return expr=0",
        ]) + "\n"
        report = summarize(dump)
        self.assertIn("ir_expr_nodes_per_function_mean: 4.000\n", report)

    def test_reports_reachable_goto_and_label_nodes_as_dispatch_proxies(self):
        dump = "\n".join([
            "typed-ir-v16",
            "counts exprs=1 stmts=6 stmt_children=2 functions=2 labels=2",
            "function 0 body=0",
            "function 1 body=-1",
            "expr 0 kind=Integer lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 value=0 text_hex=31",
            "stmt 0 kind=Block expr=-1 children_start=0 children_count=2",
            "stmt 1 kind=Goto expr=-1 aux=0",
            "stmt 2 kind=Label expr=3 aux=0 name_hex=646f6e65",
            "stmt 3 kind=Return expr=0",
            "stmt 4 kind=Goto expr=-1 aux=1",
            "stmt 5 kind=Label expr=3 aux=1 name_hex=756e72656163686564",
            "stmt-child 0 value=1",
            "stmt-child 1 value=2",
        ]) + "\n"
        report = summarize(dump)
        self.assertIn("ir_reachable_goto_nodes_per_function_mean: 1.000\n", report)
        self.assertIn("ir_reachable_label_nodes_per_function_mean: 1.000\n", report)
        self.assertIn("ir_functions_with_reachable_goto_or_label: 1\n", report)
        self.assertIn("ir_functions_with_reachable_goto_or_label_fraction: 1.0000\n", report)
        self.assertIn("ir_goto_label_nodes_per_decision_unit_mean: 2.000\n", report)

    def test_does_not_treat_scalar_name_metadata_as_an_expression_edge(self):
        dump = "\n".join([
            "typed-ir-v16",
            "counts exprs=2 stmts=1 functions=1 globals=1",
            "function 0 body=0",
            "expr 0 kind=Name lhs=-1 rhs=-1 third=0 args_start=-1 args_count=0 value=3 text_hex=76616c7565",
            "expr 1 kind=Call lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 value=0 text_hex=",
            "stmt 0 kind=Return expr=0",
        ]) + "\n"
        report = summarize(dump)
        self.assertIn("ir_expr_nodes_per_function_mean: 1.000\n", report)

    def test_rejects_invalid_array_index_side_effect_edge(self):
        dump = "\n".join([
            "typed-ir-v16",
            "counts exprs=1 stmts=0 functions=0",
            "expr 0 kind=ArrayIndex lhs=0 rhs=0 third=0 args_start=-1 args_count=0 value=4 text_hex=",
        ]) + "\n"
        with self.assertRaisesRegex(ValueError, "invalid side-effect edge"):
            summarize(dump)

    def test_deterministic_mutation_corpus_rejects_truncation_and_record_corruption(self):
        lines = sample_dump().splitlines()
        mutations = ["\n".join(lines[1:])]  # Missing version header.
        mutations.extend("\n".join(lines[:cut]) for cut in range(1, len(lines)))
        for index in range(1, len(lines)):
            removed = lines[:index] + lines[index + 1:]
            mutations.append("\n".join(removed))
            line = lines[index]
            if line.startswith(("counts ", "function ", "expr ", "stmt ", "stmt-child ", "switch-case ")):
                duplicated = lines[:index] + [line] + lines[index:]
                mutations.append("\n".join(duplicated))
        mutations.extend([
            sample_dump().replace("typed-ir-v16", "typed-ir-v999"),
            sample_dump().replace("kind=Binary", "kind=Unknown"),
            sample_dump().replace("counts exprs=7", "counts exprs=-1"),
            sample_dump().replace("stmt-child 0 value=1", "stmt-child 0 value=999"),
            sample_dump().replace("switch-case 0 value=4 body=5", "switch-case 0 value=4 body=999"),
        ])

        self.assertGreaterEqual(len(mutations), 60)
        for index, mutation in enumerate(mutations):
            with self.subTest(mutation=index):
                with self.assertRaises(ValueError):
                    summarize(mutation)


if __name__ == "__main__":
    unittest.main()
