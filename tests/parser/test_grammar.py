from pathlib import Path

import pytest
from lark import UnexpectedInput

# Define components as variables for reuse
ATTACK = """[odg.attack_tree]
toplevel A;
A;
"""

FAULT = """[odg.fault_tree]
toplevel B;
B;
"""

OBJ = """[odg.object_graph]
toplevel C;
C;
"""

FORMULAS = """[formulas]
{}A;
"""


def test_minimal_valid_odg(parse):
    """Test a minimal valid ODG structure with all required components."""
    minimal_odg = """
[odg.attack_tree]
toplevel A;

[odg.fault_tree]
toplevel B;

[odg.object_graph]
toplevel C;

[formulas]
{}A;"""
    # Should not raise an exception
    tree = parse(minimal_odg)
    assert tree is not None


def test_complete_structure(parse):
    """Test a complete ODG structure with all components."""
    complete_odg = """
[odg.attack_tree]
toplevel Root;
Root and A B;
A;
B prob = 0.5;

[odg.fault_tree]
toplevel System;
System or C D;
C;
D prob = 0.3;

[odg.object_graph]
toplevel System;
System has Component1 Component2;
Component1 properties = [prop1, prop2];
Component2;

[formulas]
{}A && B;
{A:1} P(C) >= 0.5;
MostRiskyA(Root);"""
    # Should not raise an exception
    tree = parse(complete_odg)
    assert tree is not None


def test_valid_component_orderings(parse):
    """Test different valid orderings of components."""
    valid_orderings = [
        ATTACK + FAULT + OBJ + FORMULAS,
        OBJ + ATTACK + FAULT + FORMULAS,
        FAULT + OBJ + FORMULAS + ATTACK,
        OBJ + FORMULAS + ATTACK + FAULT,
        FORMULAS + ATTACK + OBJ + FAULT,
        FAULT + FORMULAS + OBJ + ATTACK,
        ATTACK + OBJ + FAULT + FORMULAS,
        FORMULAS + OBJ + FAULT + ATTACK
    ]

    for case in valid_orderings:
        tree = parse(case)
        assert tree is not None


def test_invalid_structures(parse):
    """Test that invalid structures are rejected."""
    invalid_cases = [
        # Missing fault tree
        ATTACK + OBJ + FORMULAS,
        # Missing object graph
        ATTACK + FAULT + FORMULAS,
        # Missing formulas
        ATTACK + FAULT + OBJ,
        # Missing attack tree
        FAULT + OBJ + FORMULAS,
    ]

    for case in invalid_cases:
        with pytest.raises(UnexpectedInput):
            parse(case)


def test_individual_attack_tree(parse_rule):
    """Test parsing just an attack tree."""
    tree = """
[odg.attack_tree]
toplevel Root;
Root and A B;
A;
B prob = 0.5;"""
    result = parse_rule(tree, "attack_tree")
    assert result is not None


def test_individual_fault_tree(parse_rule):
    """Test parsing just a fault tree."""
    tree = """
[odg.fault_tree]
toplevel Root;
Root or A B;
A;
B prob = 0.3;"""
    result = parse_rule(tree, "fault_tree")
    assert result is not None


def test_individual_object_graph(parse_rule):
    """Test parsing just an object graph."""
    graph = """
[odg.object_graph]
toplevel System;
System has Component1 Component2;
Component1 properties = [prop1];
Component2;"""
    result = parse_rule(graph, "object_graph")
    assert result is not None


def test_individual_formulas(parse_rule):
    """Test parsing just ODGLog formulas."""
    formulas = """
[formulas]
{}A && B;
{A:1} P(C) >= 0.5;
MostRiskyA(Root);"""
    result = parse_rule(formulas, "odglog")
    assert result is not None


def test_whitespace_handling(parse):
    """Test that whitespace is handled correctly."""
    odg_with_whitespace = """

    [odg.attack_tree]
        toplevel A;
            A;
    
    [odg.fault_tree]
        toplevel B;
            B;
    
    [odg.object_graph]
        toplevel C;
            C;
    
    [formulas]
        {}A;"""
    tree = parse(odg_with_whitespace)
    assert tree is not None


def test_comment_handling(parse):
    """Test that comments are handled correctly."""
    odg_with_comments = """
[odg.attack_tree]
// This is a comment
toplevel A; // End of line comment
A; // Basic node

[odg.fault_tree]
toplevel B;
B;  // Another comment

[odg.object_graph]
toplevel C;
C;

[formulas]
{}A 
// Comment within formula
&& B;"""
    tree = parse(odg_with_comments)
    assert tree is not None


def test_layer2_formula_configuration(parse_rule):
    """Test that layer 2 formulas require a configuration."""
    valid_formula = "{A:1} P(C) >= 0.5"
    result = parse_rule(valid_formula, "odglog_formula")
    assert result is not None

    invalid_formula = "P(C) >= 0.5"
    with pytest.raises(UnexpectedInput):
        parse_rule(invalid_formula, "odglog_formula")

    complex_valid = "{A:0, B:1} !P(X && Y) < 0.3 && P(Z) >= 0.7"
    result = parse_rule(complex_valid, "odglog_formula")
    assert result is not None

    complex_invalid = "!P(X && Y) < 0.3 && P(Z) >= 0.7"
    with pytest.raises(UnexpectedInput):
        parse_rule(complex_invalid, "odglog_formula")


def test_complex_nested_formulas(parse_rule):
    """Test parsing complex nested ODGLog formulas."""
    formulas = [
        # Layer 1 - Basic boolean expressions
        "{}MRS(!((A && B) || (C => D)))",
        "{}!(A && B) => (C || !D)",
        "{}(A || B) && (C => D) && !(E == F)",
        "{}(!A && B) || (C && !D) == (E || !F)",
        "{}!(A => B) || (C == !D) && (E || F)",

        # Layer 1 - Evidence
        "{}A && B [X:1]",
        "{}(A || B) && C [X:1, Y:0]",

        # Layer 1 - MRS with evidence
        "{}MRS(A && B) [X:1]",
        "{}MRS(A || B) [X:1, Y:0]",

        # Layer 1 - Evidence inside MRS
        "{}MRS(A && B [X:1])",
        "{}MRS((A || B) [X:1, Y:0])",

        # Layer 1 - Multiple MRS/evidence combinations
        "{}(MRS(A) [X:1]) && MRS(B) [Y:0]",
        "{}((MRS((A))) [X:1]) && MRS(B) [Y:0]",
        "{}MRS((A) [X:1]) || MRS(B [Y:0])",
        "{}(MRS(A) && MRS(B)) [X:1, Y:0]",
        "{}(MRS(A [X:1]) => MRS(B [Y:0]) [D:0]) && C [Z:1]",

        # Layer 2 with configurations
        "{A:1} !P(X && Y) < 0.3 && P(Z) >= 0.7",
        "{A:0} P(!X || Y) == 0.5 => P(Z) > 0.2",
        "{A:1, B:0} (P(X) >= 0.3 && P(Y) < 0.7) || P(Z) == 0.5",

        # Layer 2 with probability evidence
        "{A:1} P(X) >= 0.5 [X=0.7]",
        "{A:0} P(X && Y) < 0.3 [X=0.4, Y=0.6]",
        "{A:1, B:0} (P(X) >= 0.3 [X=0.8]) && (P(X) < 0.7 [X=0.2])",

        # Layer 3
        "MostRiskyF(Door) [DF:1]",
        "OptimalConf(House) [HS:1, IU:0]",
        "OptimalConf(House) [HS:1][IU:0]",
    ]

    for formula in formulas:
        result = parse_rule(formula, "odglog_formula")
        assert result is not None, f"Failed to parse: {formula}"

    invalid_formulas = [
        # Layer 1 MRS without configuration
        "MRS(A)",
        # Layer 2 wrong probability evidence syntax
        "{A:1, B:0} (P(X) >= 0.3 [X:0.8]) && (P(X) < 0.7 [X:0.2])",
        "{A:1, B:0} (P(X) >= 0.3 {X=0.8}) && (P(X) < 0.7 {X=0.2})",
        # Layer 2 without configuration
        "P(X) >= 0.5",
        "P(X && Y) < 0.3 [X=0.4]",
        # Probability evidence inside probability formula
        "{A:1} P(X [X=0.5]) >= 0.5",
        # Probability evidence on non-Layer 2 formula
        "A && B [X=0.5]",
        # Layer 3
        "MostRiskyF(A[A: 0])",
    ]

    for formula in invalid_formulas:
        with pytest.raises(UnexpectedInput):
            parse_rule(formula, "odglog_formula")


def test_parse_example_odgl(parse):
    """Test parsing the complete odglog-example.odgl file."""
    with open(Path(__file__).parent.parent.parent
              / "docs" / "odf-example.odf",
              "r") as f:
        example_odg = f.read()

    tree = parse(example_odg)
    assert tree is not None


def test_case_insensitivity(parse):
    """Test that keywords are case insensitive."""
    case_variations = """
[ODG.ATTACK_TREE]
TOPLEVEL A;
A AND B C;
B;
C;

[ODG.FAULT_TREE]
Toplevel D;
D oR E F;
E;
F PROB = 0.3 oBjects=[obj1, obj2] conD=(a || b);

[ODG.OBJECT_GRAPH]
Toplevel System;
System Has Component;
Component Properties = [prop1];

[FORMULAS]
{A:1}
MRS(A);"""
    tree = parse(case_variations)
    assert tree is not None
