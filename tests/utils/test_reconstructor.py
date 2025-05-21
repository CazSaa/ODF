"""Tests for the formula reconstructor."""

import pytest
from lark import Tree, Token

from odf.utils.reconstructor import reconstruct


@pytest.mark.parametrize(
    "formula,expected",
    [
        # Layer 1 check queries
        ("{A: 1} B", "{A: 1} B"),
        ("{A: 1, B: 0} C && D", "{A: 1, B: 0} C && D"),
        ("{} A => B", "{} A => B"),
        # Layer 1 compute all queries
        ("{A: 1} [[B]]", "{A: 1} [[B]]"),
        ("{} [[A && B]]", "{} [[A && B]]"),
        ("{A: 1, B: 0} [[C || D]]", "{A: 1, B: 0} [[C || D]]"),
        # Layer 1 with boolean evidence
        ("{A: 1} B [C: 1]", "{A: 1} (B [C: 1])"),
        ("{} A && B [C: 1, D: 0]", "{} (A && B [C: 1, D: 0])"),
        # Layer 1 with MRS
        ("{A: 1} MRS(B)", "{A: 1} MRS(B)"),
        ("{} MRS(A && B)", "{} MRS(A && B)"),
        # Layer 2 probability queries
        ("{A: 1} P(B) > 0.5", "{A: 1} P(B) > 0.5"),
        ("{} P(A && B) <= 0.7", "{} P(A && B) <= 0.7"),
        # Layer 2 with probability evidence
        ("{A: 1} P(B) > 0.5 [C=0.3]", "{A: 1} (P(B) > 0.5 [C=0.3])"),
        (
                "{} (P(A && B) <= 0.7 [C=0.1, D=0.2])",
                "{} (P(A && B) <= 0.7 [C=0.1, D=0.2])",
        ),
        # Complex boolean formulas
        ("{} A && B || C", "{} A && B || C"),
        ("{} A => B && C", "{} A => B && C"),
        ("{} !A && B", "{} !A && B"),
        ("{} A == B", "{} A == B"),
        ("{} A != B", "{} A != B"),
        # Layer 3 queries
        ("MostRiskyA(A)", "MostRiskyA(A)"),
        ("MostRiskyF(A)", "MostRiskyF(A)"),
        ("OptimalConf(A)", "OptimalConf(A)"),
        ("MaxTotalRisk(A)", "MaxTotalRisk(A)"),
        ("MinTotalRisk(A)", "MinTotalRisk(A)"),
    ],
)
def test_reconstruct_formula(parse_rule, formula: str, expected: str) -> None:
    """Test that formulas are reconstructed correctly."""
    tree = parse_rule(formula, "doglog_formula")

    # Reconstruct the formula and compare with expected
    assert reconstruct(tree) == expected


def test_reconstruct_node_atom() -> None:
    """Test reconstruction of a node atom."""
    # Create a token for a node name
    token = Token("NODE_NAME", "A")
    tree = Tree("node_atom", [token])

    assert reconstruct(tree) == "A"
