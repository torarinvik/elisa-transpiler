#!/usr/bin/env python3
"""Unit tests for structural, per-function quality metrics."""

import unittest

from quality_ir_metrics import summarize


def sample_dump():
    return "\n".join([
        "typed-ir-v13",
        "counts exprs=7 expr_children=0 stmts=7 stmt_children=1 functions=2 switch_cases=2",
        "function 0 body=0",
        "function 1 body=4",
        "expr 0 kind=Binary lhs=1 rhs=2 third=-1 args_start=-1 args_count=0 text_hex=616e64",
        "expr 1 kind=Integer lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 text_hex=31",
        "expr 2 kind=Integer lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 text_hex=32",
        "expr 3 kind=Name lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 text_hex=73656c6563746f72",
        "expr 4 kind=Integer lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 text_hex=31",
        "expr 5 kind=Integer lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 text_hex=35",
        "expr 6 kind=Integer lhs=-1 rhs=-1 third=-1 args_start=-1 args_count=0 text_hex=36",
        "stmt 0 kind=Block expr=-1 aux=-1 aux2=-1 children_start=0 children_count=1",
        "stmt 1 kind=If expr=0 aux=2 aux2=3",
        "stmt 2 kind=Return expr=1",
        "stmt 3 kind=Return expr=2",
        "stmt 4 kind=Switch expr=3 children_start=0 children_count=2",
        "stmt 5 kind=Return expr=5",
        "stmt 6 kind=Return expr=6",
        "stmt-child 0 value=1",
        "switch-case 0 value=4 body=5 default=false",
        "switch-case 1 value=-1 body=6 default=true",
    ]) + "\n"


class QualityIrMetricTests(unittest.TestCase):
    def test_reports_reachable_per_function_distributions(self):
        report = summarize(sample_dump())
        self.assertIn("ir_functions_with_bodies: 2\n", report)
        self.assertIn("ir_expr_nodes_per_function_mean: 3.500\n", report)
        self.assertIn("ir_expr_nodes_per_function_p90: 4\n", report)
        self.assertIn("ir_stmt_nodes_per_function_mean: 3.500\n", report)
        self.assertIn("ir_decision_nodes_per_function_mean: 2.000\n", report)
        self.assertIn("ir_decision_nodes_per_function_max: 2\n", report)
        self.assertIn("ir_expr_nodes_per_decision_unit_mean: 1.167\n", report)

    def test_ignores_bodyless_functions_and_returns_n_a_for_empty_distribution(self):
        dump = "\n".join([
            "typed-ir-v13",
            "counts exprs=0 stmts=0 functions=1",
            "function 0 body=-1",
        ]) + "\n"
        report = summarize(dump)
        self.assertIn("ir_functions_with_bodies: 0\n", report)
        self.assertIn("ir_expr_nodes_per_function_mean: n/a\n", report)
        self.assertIn("ir_decision_nodes_per_function_max: n/a\n", report)

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
            "typed-ir-v13",
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

    def test_does_not_treat_scalar_name_metadata_as_an_expression_edge(self):
        dump = "\n".join([
            "typed-ir-v13",
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
            "typed-ir-v13",
            "counts exprs=1 stmts=0 functions=0",
            "expr 0 kind=ArrayIndex lhs=0 rhs=0 third=0 args_start=-1 args_count=0 value=4 text_hex=",
        ]) + "\n"
        with self.assertRaisesRegex(ValueError, "invalid side-effect edge"):
            summarize(dump)


if __name__ == "__main__":
    unittest.main()
