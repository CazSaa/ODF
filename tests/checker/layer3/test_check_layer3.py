from fractions import Fraction

import pytest
from lark import Tree, Token

from odf.checker.exceptions import MissingNodeImpactError
from odf.checker.layer3.check_layer3 import CollectEvidenceInterpreter, \
    most_risky


def test_no_evidence():
    """Test that formulas without evidence return empty evidence dict and correct formula type"""
    interpreter = CollectEvidenceInterpreter()

    # MostRiskyA formula
    tree = Tree("layer3_query", [
        Tree("most_risky_a", [
            Token("NODE_NAME", "Attack1")
        ])
    ])
    evidence = interpreter.visit(tree)[0]
    assert evidence == {}
    assert interpreter.formula_type == "most_risky_a"

    # MostRiskyF formula  
    interpreter = CollectEvidenceInterpreter()
    tree = Tree("layer3_query", [
        Tree("most_risky_f", [
            Token("NODE_NAME", "Fault1")
        ])
    ])
    evidence = interpreter.visit(tree)[0]
    assert evidence == {}
    assert interpreter.formula_type == "most_risky_f"

    # OptimalConf formula
    interpreter = CollectEvidenceInterpreter()
    tree = Tree("layer3_query", [
        Tree("optimal_conf", [
            Token("NODE_NAME", "Object1")
        ])
    ])
    evidence = interpreter.visit(tree)[0]
    assert evidence == {}
    assert interpreter.formula_type == "optimal_conf"

    # MaxTotalRisk formula
    interpreter = CollectEvidenceInterpreter()
    tree = Tree("layer3_query", [
        Tree("max_total_risk", [
            Token("NODE_NAME", "Risk1")
        ])
    ])
    evidence = interpreter.visit(tree)[0]
    assert evidence == {}
    assert interpreter.formula_type == "max_total_risk"

    # MinTotalRisk formula
    interpreter = CollectEvidenceInterpreter()
    tree = Tree("layer3_query", [
        Tree("min_total_risk", [
            Token("NODE_NAME", "Risk1")
        ])
    ])
    evidence = interpreter.visit(tree)[0]
    assert evidence == {}
    assert interpreter.formula_type == "min_total_risk"


def test_single_evidence():
    """Test that formulas with one piece of evidence properly collect it and formula type"""
    interpreter = CollectEvidenceInterpreter()

    tree = Tree("layer3_query", [
        Tree("with_boolean_evidence", [
            Tree("most_risky_a", [
                Token("NODE_NAME", "Attack1")
            ]),
            Tree("boolean_evidence", [
                Tree("boolean_mapping", [
                    Token("NODE_NAME", "Property1"),
                    Token("TRUTH_VALUE", "1")
                ])
            ])
        ])
    ])

    evidence = interpreter.visit(tree)[0]
    assert evidence == {"Property1": True}
    assert interpreter.formula_type == "most_risky_a"


def test_multiple_evidence():
    """Test that formulas with multiple pieces of evidence collect all of them and formula type"""
    interpreter = CollectEvidenceInterpreter()

    tree = Tree("layer3_query", [
        Tree("with_boolean_evidence", [
            Tree("most_risky_f", [
                Token("NODE_NAME", "Fault1")
            ]),
            Tree("boolean_evidence", [
                Tree("boolean_mapping", [
                    Token("NODE_NAME", "Property1"),
                    Token("TRUTH_VALUE", "1")
                ]),
                Tree("boolean_mapping", [
                    Token("NODE_NAME", "Property2"),
                    Token("TRUTH_VALUE", "0")
                ])
            ])
        ])
    ])

    evidence = interpreter.visit(tree)[0]
    assert evidence == {
        "Property1": True,
        "Property2": False
    }
    assert interpreter.formula_type == "most_risky_f"


def test_nested_evidence():
    """Test that formulas with nested evidence collect all levels and formula type"""
    interpreter = CollectEvidenceInterpreter()

    tree = Tree("layer3_query", [
        Tree("with_boolean_evidence", [
            Tree("with_boolean_evidence", [
                Tree("optimal_conf", [
                    Token("NODE_NAME", "Object1")
                ]),
                Tree("boolean_evidence", [
                    Tree("boolean_mapping", [
                        Token("NODE_NAME", "Property1"),
                        Token("TRUTH_VALUE", "1")
                    ])
                ])
            ]),
            Tree("boolean_evidence", [
                Tree("boolean_mapping", [
                    Token("NODE_NAME", "Property2"),
                    Token("TRUTH_VALUE", "0")
                ])
            ])
        ])
    ])

    evidence = interpreter.visit(tree)[0]
    assert evidence == {
        "Property1": True,
        "Property2": False
    }
    assert interpreter.formula_type == "optimal_conf"


def test_nested_evidence_with_conflict():
    """Test that inner evidence overrides outer evidence for the same property and formula type"""
    interpreter = CollectEvidenceInterpreter()

    tree = Tree("layer3_query", [
        Tree("with_boolean_evidence", [
            Tree("with_boolean_evidence", [
                Tree("max_total_risk", [
                    Token("NODE_NAME", "Risk1")
                ]),
                Tree("boolean_evidence", [
                    Tree("boolean_mapping", [
                        Token("NODE_NAME", "Property1"),
                        Token("TRUTH_VALUE", "1")
                        # Inner evidence sets Property1 to True
                    ])
                ])
            ]),
            Tree("boolean_evidence", [
                Tree("boolean_mapping", [
                    Token("NODE_NAME", "Property1"),
                    # Outer evidence tries to set Property1 to False
                    Token("TRUTH_VALUE", "0")
                    # but inner evidence should take precedence
                ]),
                Tree("boolean_mapping", [
                    Token("NODE_NAME", "Property2"),
                    Token("TRUTH_VALUE", "0")
                ])
            ])
        ])
    ])
    evidence = interpreter.visit(tree)[0]
    assert evidence == {
        "Property1": True,  # Should keep inner evidence value
        "Property2": False
    }
    assert interpreter.formula_type == "max_total_risk"


def test_most_risky_attack_door_basic(paper_example_models):
    """Test most_risky identifies the highest-risk attack node for Door."""
    # Door attack participants: EDLU, FD, DD
    # Risk(EDLU) = prob(EDLU) * impact(EDLU) = 0.17 * 1.27 = 0.2159
    # Risk(DD) = prob(DD) * impact(DD) = 0.13 * 1.81 = 0.2353
    # Risk(FD) = P(PL or DD) * impact(FD)=2.57 = 0.13 * 2.57 = 0.3341
    result = most_risky("Door", "attack", {"DF": True}, *paper_example_models)
    assert result.name == "FD"


def test_unused_evidence(caplog, paper_example_models):
    most_risky("Door", "attack", {"DF": True, "Unused": False},
               *paper_example_models)
    assert "these elements can be removed: {'Unused'}" in caplog.text


def test_most_risky_attack_lock_basic(paper_example_models):
    """Test that most_risky correctly identifies PL as the risky node for Lock."""
    # Lock attack participants: PL
    # Risk(PL) = prob(PL | LP=True) * impact(PL) = 0.10 * 2.51 = 0.251
    result = most_risky("Lock", "attack", {"LP": True}, *paper_example_models)
    assert result.name == "PL"


def test_most_risky_fault_door_basic(paper_example_models):
    """Test that most_risky correctly identifies DSL as the highest-risk fault node for Door."""
    # Door fault participants: DGB, DSL
    # Risk(DSL) = prob(DSL) * impact(DSL) = 0.20 * 1.31 = 0.262
    # Risk(DGB) = P(DSL and LGJ) * impact(DGB) = 0.20 * 0.70 * 1.67 = 0.2338
    result = most_risky("Door", "fault", {}, *paper_example_models)
    assert result.name == "DSL"


def test_most_risky_fault_lock_basic(paper_example_models):
    """Test that most_risky correctly identifies LGJ as the risky node for Lock."""
    # Lock fault participants: LGJ
    # Risk(LGJ) = prob(LGJ | LJ=True) * impact(LGJ) = 0.70 * 0.83 = 0.581
    result = most_risky("Lock", "fault", {"LJ": True}, *paper_example_models)
    assert result.name == "LGJ"


def test_fd_different_impact(
        paper_example_models):
    result = most_risky("Door", "attack", {"DF": False}, *paper_example_models)
    assert result.name == "FD"

    attack_tree = paper_example_models[0]
    attack_tree.nodes["FD"]["data"].impact = Fraction("2.15")
    result = most_risky("Door", "attack", {"DF": False}, *paper_example_models)
    assert result.name == "EDLU"


def test_most_risky_attack_lock_evidence_makes_unsatisfiable(
        paper_example_models):
    """Test that most_risky returns None when evidence makes PL unsatisfiable."""
    # Lock attack participants: PL. Evidence: LP=False.
    # PL condition (LP) is False, making PL unsatisfiable. No other participants.
    result = most_risky("Lock", "attack", {"LP": False}, *paper_example_models)
    assert result is None


def test_most_risky_fault_lock_evidence_makes_unsatisfiable(
        paper_example_models):
    """Test that most_risky returns None when evidence makes LGJ unsatisfiable."""
    # Lock fault participants: LGJ. Evidence: LJ=False.
    # LGJ condition (LJ) is False, making LGJ unsatisfiable. No other participants.
    result = most_risky("Lock", "fault", {"LJ": False}, *paper_example_models)
    assert result is None


def test_most_risky_no_participant_nodes(paper_example_models,
                                         object_graph_paper_example_with_extra):
    """Test that most_risky returns None for an object with no participant nodes."""
    result = most_risky("ExtraObject", "attack", {}, *paper_example_models[:2],
                        object_graph_paper_example_with_extra)
    assert result is None


def test_most_risky_object_not_in_graph(paper_example_models):
    """Test that most_risky returns None for an object not in the graph."""
    result = most_risky("NonexistentObject", "attack", {},
                        *paper_example_models)
    assert result is None


def test_most_risky_missing_impact_error(paper_example_models):
    """Test that most_risky raises MissingNodeImpactError when a node is missing its impact."""
    # Remove PL's impact
    attack_tree = paper_example_models[0]
    attack_tree.nodes["PL"]["data"].impact = None

    with pytest.raises(MissingNodeImpactError, match="PL") as exc_info:
        most_risky("Lock", "attack", {"LP": True}, *paper_example_models)
    assert "attack" in str(exc_info.value)
