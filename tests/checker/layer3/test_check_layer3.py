import random
import re
from fractions import Fraction

import pytest
from dd import cudd, cudd_add
from lark import Tree, Token

from odf.checker.exceptions import MissingNodeImpactError
from odf.checker.layer2.check_layer2 import calc_node_prob
from odf.checker.layer3.check_layer3 import CollectEvidenceInterpreter, \
    most_risky, total_risk, create_mtbdd, optimal_conf
from odf.models.disruption_tree import DisruptionTree


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


def test_most_risky_attack_door_basic(caplog, paper_example_disconnected):
    """Test most_risky identifies the highest-risk attack node for Door."""
    # Door attack participants: EDLU, FD, DD
    # Risk(EDLU) = prob(EDLU) * impact(EDLU) = 0.17 * 1.27 = 0.2159
    # Risk(DD) = prob(DD) * impact(DD) = 0.13 * 1.81 = 0.2353
    # Risk(FD) = P(PL or DD) * impact(FD)=2.57 = 0.13 * 2.57 = 0.3341
    result = most_risky("Door", "attack", {"DF": True},
                        *paper_example_disconnected)
    # Risk messages now include exact fractions, so use regex
    assert re.search(r"Risk for node EDLU: \d+/\d+ \(~0\.2159\)", caplog.text)
    assert re.search(r"Risk for node FD: \d+/\d+ \(~0\.3341\)", caplog.text)
    assert re.search(r"Risk for node DD: \d+/\d+ \(~0\.2353\)", caplog.text)
    assert result.name == "FD"


def test_unused_evidence(caplog, paper_example_disconnected):
    most_risky("Door", "attack", {"DF": True, "Unused": False},
               *paper_example_disconnected)
    assert "Evidence {'Unused'} is not used by the formula and will be ignored." in caplog.text


def test_most_risky_attack_lock_basic(caplog, paper_example_disconnected):
    """Test that most_risky correctly identifies PL as the risky node for Lock."""
    # Lock attack participants: PL
    # Risk(PL) = prob(PL | LP=True) * impact(PL) = 0.10 * 2.51 = 0.251
    result = most_risky("Lock", "attack", {"LP": True},
                        *paper_example_disconnected)
    assert re.search(r"Risk for node PL: \d+/\d+ \(~0\.251\)", caplog.text)
    assert result.name == "PL"


def test_most_risky_fault_door_basic(caplog, paper_example_disconnected):
    """Test that most_risky correctly identifies DSL as the highest-risk fault node for Door."""
    # Door fault participants: DGB, DSL
    # Risk(DSL) = prob(DSL) * impact(DSL) = 0.20 * 1.31 = 0.262
    # Risk(DGB) = P(DSL and LGJ) * impact(DGB) = 0.20 * 0.70 * 1.67 = 0.2338
    result = most_risky("Door", "fault", {}, *paper_example_disconnected)
    assert re.search(r"Risk for node DSL: \d+/\d+ \(~0\.262\)", caplog.text)
    assert re.search(r"Risk for node DGB: \d+/\d+ \(~0\.2338\)", caplog.text)
    assert result.name == "DSL"


def test_most_risky_fault_lock_basic(caplog, paper_example_disconnected):
    """Test that most_risky correctly identifies LGJ as the risky node for Lock."""
    # Lock fault participants: LGJ
    # Risk(LGJ) = prob(LGJ | LJ=True) * impact(LGJ) = 0.70 * 0.83 = 0.581
    result = most_risky("Lock", "fault", {"LJ": True},
                        *paper_example_disconnected)
    assert re.search(r"Risk for node LGJ: \d+/\d+ \(~0\.581\)", caplog.text)
    assert result.name == "LGJ"


def test_fd_different_impact(caplog, paper_example_disconnected):
    result = most_risky("Door", "attack", {"DF": False},
                        *paper_example_disconnected)
    assert re.search(r"Risk for node EDLU: \d+/\d+ \(~0\.2159\)", caplog.text)
    assert re.search(r"Risk for node FD: \d+/\d+ \(~0\.257\)", caplog.text)
    assert result.name == "FD"
    caplog.clear()

    attack_tree = paper_example_disconnected[0]
    attack_tree.nodes["FD"]["data"].impact = Fraction("2.15")
    result = most_risky("Door", "attack", {"DF": False},
                        *paper_example_disconnected)
    assert re.search(r"Risk for node EDLU: \d+/\d+ \(~0\.2159\)", caplog.text)
    assert re.search(r"Risk for node FD: \d+/\d+ \(~0\.215\)", caplog.text)
    assert result.name == "EDLU"


def test_most_risky_attack_lock_evidence_makes_unsatisfiable(caplog,
                                                             paper_example_disconnected):
    """Test that most_risky returns None when evidence makes PL unsatisfiable."""
    # Lock attack participants: PL. Evidence: LP=False.
    # PL condition (LP) is False, making PL unsatisfiable. No other participants.
    result = most_risky("Lock", "attack", {"LP": False},
                        *paper_example_disconnected)
    assert "Evidence {'LP': False} made node 'PL' unsatisfiable." in caplog.text
    assert result is None


def test_most_risky_fault_lock_evidence_makes_unsatisfiable(caplog,
                                                            paper_example_disconnected):
    """Test that most_risky returns None when evidence makes LGJ unsatisfiable."""
    # Lock fault participants: LGJ. Evidence: LJ=False.
    # LGJ condition (LJ) is False, making LGJ unsatisfiable. No other participants.
    result = most_risky("Lock", "fault", {"LJ": False},
                        *paper_example_disconnected)
    assert "Evidence {'LJ': False} made node 'LGJ' unsatisfiable." in caplog.text
    assert result is None


def test_most_risky_fault_with_unsatisfiable_node(caplog,
                                                  paper_example_disconnected,
                                                  fault_tree_paper_example_with_unsat_node):
    # Risk(FBO) = prob(FBO) * impact(FBO) = 0.21 * 1.09 = 0.2289
    # Risk(DSL) = prob(DSL) * impact(DSL) = 0.20 * 1.31 = 0.262
    result = most_risky("House", "fault", {}, paper_example_disconnected[0],
                        fault_tree_paper_example_with_unsat_node,
                        paper_example_disconnected[2])
    assert "Node 'Fire_and_impossible_escape' is not satisfiable." in caplog.text
    assert re.search(r"Risk for node FBO: \d+/\d+ \(~0\.2289\)", caplog.text)
    assert re.search(r"Risk for node DSL: \d+/\d+ \(~0\.262\)", caplog.text)
    assert result.name == "DSL"


def test_most_risky_no_participant_nodes(caplog,
                                         paper_example_disconnected,
                                         object_graph_paper_example_with_extra):
    """Test that most_risky returns None for an object with no participant nodes."""
    result = most_risky("ExtraObject", "attack", {},
                        *paper_example_disconnected[:2],
                        object_graph_paper_example_with_extra)
    assert "There are no nodes in the attack tree that participate in the ExtraObject object." in caplog.text
    assert result is None


def test_most_risky_object_not_in_graph(caplog, paper_example_disconnected):
    """Test that most_risky returns None for an object not in the graph."""
    result = most_risky("NonexistentObject", "attack", {},
                        *paper_example_disconnected)
    assert "There are no nodes in the attack tree that participate in the NonexistentObject object." in caplog.text
    assert result is None


def test_most_risky_missing_impact_error(paper_example_disconnected):
    """Test that most_risky raises MissingNodeImpactError when a node is missing its impact."""
    # Remove PL's impact
    attack_tree = paper_example_disconnected[0]
    attack_tree.nodes["PL"]["data"].impact = None

    with pytest.raises(MissingNodeImpactError, match="PL") as exc_info:
        most_risky("Lock", "attack", {"LP": True}, *paper_example_disconnected)
    assert "attack" in str(exc_info.value)


# Helper function for comparing floats
def approx(value):
    return pytest.approx(value, abs=1e-7)


# === Tests for total_risk ===

def test_total_risk_door_max_no_evidence(paper_example_disconnected):
    """Calculate max total risk for Door with no evidence."""
    # Let's calculate for the best config {LP: 1, DF: 1, LJ: 1} using correct AT OR logic (max)
    # Risk(EDLU) = 0.17 * 1.27 = 0.2159
    # Risk(FD): P(PL or DD | LP=1, DF=1) = max(P(PL|LP=1), P(DD|DF=1)) = max(0.10, 0.13) = 0.13. Risk = 0.13 * 2.57 = 0.3341
    # Risk(DD) = P(DD | DF=1) * 1.81 = 0.13 * 1.81 = 0.2353
    # Risk(DGB): P(DSL and LGJ | LJ=1) = 0.20 * 0.70 = 0.14. Risk = 0.14 * 1.67 = 0.2338
    # Risk(DSL) = 0.20 * 1.31 = 0.262
    # Total = 0.2159 + 0.3341 + 0.2353 + 0.2338 + 0.262 = 1.2811
    result = total_risk("Door", max, {}, *paper_example_disconnected)
    assert result == approx(1.2811)


def test_total_risk_door_min_no_evidence(paper_example_disconnected):
    """Calculate min total risk for Door with no evidence."""
    # Let's calculate for the worst config {LP: 0, DF: 0, LJ: 0}
    # Risk(EDLU) = 0.17 * 1.27 = 0.2159
    # Risk(FD): P(PL or DD | LP=0, DF=0) = max(0, 0) = 0. Risk = 0
    # Risk(DD) = P(DD | DF=0) * 1.81 = 0. Risk = 0
    # Risk(DGB): P(DSL and LGJ | LJ=0) = 0. Risk = 0
    # Risk(DSL) = 0.20 * 1.31 = 0.262
    # Total = 0.2159 + 0 + 0 + 0 + 0.262 = 0.4779
    result = total_risk("Door", min, {}, *paper_example_disconnected)
    assert result == approx(0.4779)


def test_total_risk_lock_max_with_evidence(paper_example_disconnected):
    """Calculate max total risk for Lock with evidence LP=True, LJ=False."""
    # Expected: Risk(PL | LP=1) + Risk(LGJ | LJ=0) = (0.10 * 2.51) + 0 = 0.251
    result = total_risk("Lock", max, {"LP": True, "LJ": False},
                        *paper_example_disconnected)
    assert result == approx(0.251)


def test_total_risk_lock_min_with_evidence(paper_example_disconnected):
    """Calculate min total risk for Lock with evidence LP=True, LJ=False."""
    # Same calculation as max case due to fixed properties.
    result = total_risk("Lock", min, {"LP": True, "LJ": False},
                        *paper_example_disconnected)
    assert result == approx(0.251)


def test_total_risk_door_sum_with_evidence(paper_example_disconnected):
    """Calculate sum of risks for Door under a specific configuration {DF:1, LP:1, LJ:0}."""
    # Risk(EDLU) = 0.17 * 1.27 = 0.2159
    # Risk(FD | LP=1, DF=1) = max(P(PL|LP=1), P(DD|DF=1)) * 2.57 = max(0.10, 0.13) * 2.57 = 0.3341
    # Risk(DD | DF=1) = 0.13 * 1.81 = 0.2353
    # Risk(DGB | LJ=0) = P(DSL and LGJ | LJ=0) * 1.67 = (0.20 * 0) * 1.67 = 0
    # Risk(DSL) = 0.20 * 1.31 = 0.262
    # Total (Sum) = 0.2159 + 0.3341 + 0.2353 + 0 + 0.262 = 1.0473
    result = total_risk("Door", sum, {"DF": True, "LP": True, "LJ": False},
                        *paper_example_disconnected)
    assert result == approx(1.0473)


def test_total_risk_evidence_makes_pl_unsatisfiable(paper_example_disconnected):
    """Calculate max total risk for Lock when evidence {LP:0, LJ:1} makes PL unsat."""
    # Expected: Risk(PL | LP=0) + Risk(LGJ | LJ=1) = 0 + (0.70 * 0.83) = 0.581
    result = total_risk("Lock", max, {"LP": False, "LJ": True},
                        *paper_example_disconnected)
    assert result == approx(0.581)


def test_total_risk_evidence_makes_all_lock_unsatisfiable(caplog,
                                                          paper_example_disconnected):
    """Test total_risk for Lock when evidence {LP:0, LJ:0} makes all nodes unsat."""
    result_max = total_risk("Lock", max, {"LP": False, "LJ": False},
                            *paper_example_disconnected)
    assert result_max == approx(0.0)
    assert "Evidence {'LP': False} made node 'PL' unsatisfiable." in caplog.text
    assert "Evidence {'LJ': False} made node 'LGJ' unsatisfiable." in caplog.text
    caplog.clear()

    result_min = total_risk("Lock", min, {"LP": False, "LJ": False},
                            *paper_example_disconnected)
    assert result_min == approx(0.0)
    assert "Evidence {'LP': False} made node 'PL' unsatisfiable." in caplog.text
    assert "Evidence {'LJ': False} made node 'LGJ' unsatisfiable." in caplog.text
    caplog.clear()

    result_sum = total_risk("Lock", sum, {"LP": False, "LJ": False},
                            *paper_example_disconnected)
    assert result_sum == approx(0.0)
    assert "Evidence {'LP': False} made node 'PL' unsatisfiable." in caplog.text
    assert "Evidence {'LJ': False} made node 'LGJ' unsatisfiable." in caplog.text


def test_total_risk_no_participants(caplog,
                                    paper_example_disconnected,
                                    object_graph_paper_example_with_extra):
    """Test total_risk returns None for an object with no participant nodes."""
    result = total_risk("ExtraObject", max, {}, paper_example_disconnected[0],
                        paper_example_disconnected[1],
                        object_graph_paper_example_with_extra)
    assert result is None
    assert "There are no nodes in the attack or fault tree that participate in the ExtraObject object." in caplog.text


def test_total_risk_object_not_in_graph(caplog, paper_example_disconnected):
    """Test total_risk returns None for an object not in the graph."""
    result = total_risk("NonexistentObject", max, {},
                        *paper_example_disconnected)
    assert result is None
    assert "There are no nodes in the attack or fault tree that participate in the NonexistentObject object." in caplog.text


def test_total_risk_missing_impact_error(paper_example_disconnected):
    """Test total_risk raises MissingNodeImpactError."""
    # Need to copy models if fixture scope is broad or use a dedicated fixture
    attack_tree = paper_example_disconnected[0]
    attack_tree.nodes["PL"]["data"].impact = None  # Remove impact

    with pytest.raises(MissingNodeImpactError, match="PL") as exc_info:
        total_risk("Lock", max, {"LP": True}, *paper_example_disconnected)
    assert "attack or fault" in str(exc_info.value)


def test_total_risk_unused_evidence(caplog, paper_example_disconnected):
    result_with_unused = total_risk("Door", max,
                                    {"DF": True, "UnusedProp": False},
                                    *paper_example_disconnected)
    result_without_unused = total_risk("Door", max, {"DF": True},
                                       *paper_example_disconnected)
    assert result_with_unused == approx(result_without_unused)
    assert "Evidence {'UnusedProp'} is not used by the formula and will be ignored." in caplog.text


# === Tests for create_mtbdd ===

def _check_mtbdd_structure(bdd_node: cudd.Function,
                           mtbdd_node: cudd_add.Function,
                           object_properties: set[str],
                           attack_tree: DisruptionTree,
                           fault_tree: DisruptionTree,
                           impact: Fraction,
                           is_complement: bool):  # Tracks negation down the BDD path
    """Recursively checks if MTBDD structure matches BDD based on OP vars.

    WARNING: this method of testing is not perfect; if different nodes in the
    BDD have the same risk value, this can be exploited in the MTBDD which will
    result in a different structure, even though it still represents the same,
    correct, mapping of configurations to risk values.
    """
    if bdd_node.var is None:
        # If BDD is terminal, MTBDD must be terminal with risk = P(BDD) * impact
        assert mtbdd_node.var is None
        # calc_node_prob expects a non-terminal BDD to start traversal,
        # but if the original BDD itself was terminal, the risk is simple.
        expected_prob = 1.0 if (
                                       bdd_node == bdd_node.bdd.true) ^ is_complement else 0.0
        expected_risk = expected_prob * float(impact)
        assert mtbdd_node.value == approx(expected_risk)
        return

    is_op = bdd_node.var in object_properties

    if is_op:
        # If BDD node is OP, MTBDD node must be internal with the same var
        assert not mtbdd_node.var is None
        assert mtbdd_node.var == bdd_node.var

        # Recurse: High child (no change in complement)
        _check_mtbdd_structure(bdd_node.high,
                               mtbdd_node.high,
                               object_properties,
                               attack_tree, fault_tree, impact,
                               is_complement)

        # Recurse: Low child (handle potential BDD negation)
        _check_mtbdd_structure(bdd_node.low.regular,
                               mtbdd_node.low,
                               object_properties,
                               attack_tree, fault_tree, impact,
                               is_complement ^ bdd_node.low.negated)
    else:
        # If BDD node is not OP, MTBDD node must be terminal
        assert mtbdd_node.var is None

        expected_prob = calc_node_prob(attack_tree, fault_tree, bdd_node,
                                       is_complement, {})
        expected_risk = expected_prob * float(impact)

        assert mtbdd_node.value == approx(expected_risk)


def test_create_mtbdd_structure_simple(caplog, paper_example_disconnected):
    """Test MTBDD structure for a simple BDD with OP and non-OP vars."""
    attack_tree, fault_tree, object_graph = paper_example_disconnected
    object_properties = set(object_graph.object_properties)
    impact = Fraction("1.5")

    # Get BDD for a formula like: LP and (DSL or EDLU)
    # LP is OP, DSL and EDLU are not.
    bdd_manager = cudd.BDD()
    bdd_manager.configure(reordering=False)
    bdd_manager.declare(*object_properties, "LP", "DSL", "EDLU")
    lp_bdd = bdd_manager.var("LP")
    dsl_bdd = bdd_manager.var("DSL")
    edlu_bdd = bdd_manager.var("EDLU")
    non_op_bdd = dsl_bdd | edlu_bdd
    bdd = lp_bdd & non_op_bdd

    mtbdd_manager = cudd_add.ADD()
    mtbdd_manager.declare(*object_properties)

    mtbdd = create_mtbdd(mtbdd_manager, attack_tree, fault_tree,
                         object_properties, bdd, impact)

    # Start the recursive check
    _check_mtbdd_structure(bdd, mtbdd, object_properties, attack_tree,
                           fault_tree, impact, bdd.negated)


def test_create_mtbdd_structure_only_op(paper_example_disconnected):
    """Test MTBDD structure for a BDD with only OP variables."""
    attack_tree, fault_tree, object_graph = paper_example_disconnected
    object_properties = set(object_graph.object_properties)
    impact = Fraction("2.0")

    # BDD for LP & LJ (both OP)
    bdd_manager = cudd.BDD()
    bdd_manager.configure(reordering=False)
    bdd_manager.declare(*object_properties)
    lp_bdd = bdd_manager.var("LP")
    lj_bdd = bdd_manager.var("LJ")
    bdd = lp_bdd & lj_bdd

    mtbdd_manager = cudd_add.ADD()
    mtbdd_manager.declare(*object_properties)

    mtbdd = create_mtbdd(mtbdd_manager, attack_tree, fault_tree,
                         object_properties, bdd, impact)

    _check_mtbdd_structure(bdd, mtbdd, object_properties, attack_tree,
                           fault_tree, impact, bdd.negated)


def test_create_mtbdd_structure_only_non_op(paper_example_disconnected):
    """Test MTBDD structure for a BDD with only non-OP variables."""
    attack_tree, fault_tree, object_graph = paper_example_disconnected
    object_properties = set(object_graph.object_properties)
    impact = Fraction("1.2")

    # BDD for DSL & EDLU (both non-OP)
    bdd_manager = cudd.BDD()
    bdd_manager.configure(reordering=False)
    bdd_manager.declare("DSL", "EDLU")  # Only declare needed non-OP vars
    dsl_bdd = bdd_manager.var("DSL")
    edlu_bdd = bdd_manager.var("EDLU")
    bdd = dsl_bdd & edlu_bdd

    mtbdd_manager = cudd_add.ADD()
    # No OP properties to declare for the MTBDD manager in this specific case

    mtbdd = create_mtbdd(mtbdd_manager, attack_tree, fault_tree,
                         object_properties, bdd, impact)

    # The entire BDD is non-OP, so the MTBDD should be a single terminal
    assert mtbdd.var is None
    expected_prob = calc_node_prob(attack_tree, fault_tree, bdd, False, {})
    expected_risk = expected_prob * float(impact)
    assert mtbdd.value == approx(expected_risk)


def test_create_mtbdd_structure_nested(paper_example_disconnected):
    """Test MTBDD structure for a BDD with nested OP and non-OP vars."""
    attack_tree, fault_tree, object_graph = paper_example_disconnected
    object_properties = set(object_graph.object_properties)
    impact = Fraction("1.8")

    # BDD for LP & (LJ | (DSL & EDLU))
    bdd_manager = cudd.BDD()
    bdd_manager.configure(reordering=False)
    bdd_manager.declare(*object_properties, "DSL", "EDLU")
    lp_bdd = bdd_manager.var("LP")
    lj_bdd = bdd_manager.var("LJ")
    dsl_bdd = bdd_manager.var("DSL")
    edlu_bdd = bdd_manager.var("EDLU")
    inner_non_op = dsl_bdd & edlu_bdd
    mixed_or = lj_bdd | inner_non_op
    bdd = lp_bdd & mixed_or

    mtbdd_manager = cudd_add.ADD()
    mtbdd_manager.declare(*object_properties)

    mtbdd = create_mtbdd(mtbdd_manager, attack_tree, fault_tree,
                         object_properties, bdd, impact)

    # Check structure recursively
    _check_mtbdd_structure(bdd, mtbdd, object_properties, attack_tree,
                           fault_tree, impact, bdd.negated)


def test_create_mtbdd_structure_negation(paper_example_disconnected):
    """Test MTBDD structure for a BDD involving negation."""
    attack_tree, fault_tree, object_graph = paper_example_disconnected
    object_properties = set(object_graph.object_properties)
    impact = Fraction("1.1")

    # BDD for LP & ~DSL
    bdd_manager = cudd.BDD()
    bdd_manager.configure(reordering=False)
    bdd_manager.declare(*object_properties, "DSL")
    lp_bdd = bdd_manager.var("LP")
    dsl_bdd = bdd_manager.var("DSL")
    bdd = lp_bdd & ~dsl_bdd

    mtbdd_manager = cudd_add.ADD()
    mtbdd_manager.declare(*object_properties)

    mtbdd = create_mtbdd(mtbdd_manager, attack_tree, fault_tree,
                         object_properties, bdd, impact)

    _check_mtbdd_structure(bdd, mtbdd, object_properties, attack_tree,
                           fault_tree, impact, bdd.negated)


def test_create_mtbdd_structure_terminal_true(paper_example_disconnected):
    """Test MTBDD structure when the input BDD is True."""
    attack_tree, fault_tree, object_graph = paper_example_disconnected
    object_properties = set(object_graph.object_properties)
    impact = Fraction("1.6")

    bdd_manager = cudd.BDD()
    bdd = bdd_manager.true  # Terminal BDD

    mtbdd_manager = cudd_add.ADD()

    mtbdd = create_mtbdd(mtbdd_manager, attack_tree, fault_tree,
                         object_properties, bdd, impact)

    # Should be a terminal node with risk = 1.0 * impact
    assert mtbdd.var is None
    assert mtbdd.value == approx(1.0 * float(impact))


def test_create_mtbdd_structure_terminal_false(paper_example_disconnected):
    """Test MTBDD structure when the input BDD is False."""
    attack_tree, fault_tree, object_graph = paper_example_disconnected
    object_properties = set(object_graph.object_properties)
    impact = Fraction("1.7")

    bdd_manager = cudd.BDD()
    bdd = bdd_manager.false  # Terminal BDD

    mtbdd_manager = cudd_add.ADD()

    mtbdd = create_mtbdd(mtbdd_manager, attack_tree, fault_tree,
                         object_properties, bdd, impact)

    # Should be a terminal node with risk = 0.0 * impact
    assert mtbdd.var is None
    assert mtbdd.value == approx(0.0)


# Run this a couple times with random variable ordering
@pytest.mark.parametrize('_ct', range(10))
def test_create_mtbdd_structure_complex_nested(complex_test_models, _ct):
    attack_tree, fault_tree, object_graph = complex_test_models
    object_properties = set(object_graph.object_properties)
    impact = Fraction("2.5")

    bdd_manager = cudd.BDD()
    bdd_manager.configure(reordering=False)

    ops = ['OP1', 'OP2', 'OP3', 'OP4', 'OP5', 'OP6', 'OP7', 'OP8']
    random.shuffle(ops)
    non_ops = ['NON_OP1', 'NON_OP2', 'NON_OP3', 'NON_OP4', 'NON_OP5']
    random.shuffle(non_ops)

    all_vars = ops + non_ops
    print(*all_vars)  # Print for diagnostics if test fails
    bdd_manager.declare(*all_vars)

    nodes = {name: bdd_manager.var(name) for name in all_vars}

    # Formula:
    # ( ~OP1 | (~OP2 & NON_OP1) ) &
    # ( ~OP3 | (OP4 & ~NON_OP2) ) &
    # ( (~OP5 | NON_OP3) | (NON_OP4 & ~OP6) ) &
    # ( ~OP7 | (NON_OP5 & ~OP8) )
    part1 = ~nodes['OP1'] | (~nodes['OP2'] & nodes['NON_OP1'])
    part2 = ~nodes['OP3'] | (nodes['OP4'] & ~nodes['NON_OP2'])
    part3 = (~nodes['OP5'] | nodes['NON_OP3']) | (
            nodes['NON_OP4'] & ~nodes['OP6'])
    part4 = ~nodes['OP7'] | (nodes['NON_OP5'] & ~nodes['OP8'])

    bdd = part1 & part2 & part3 & part4

    mtbdd_manager = cudd_add.ADD()
    mtbdd_manager.configure(reordering=False)
    mtbdd_manager.declare(*ops)

    mtbdd = create_mtbdd(mtbdd_manager, attack_tree, fault_tree,
                         object_properties, bdd, impact)

    # Start the recursive check
    _check_mtbdd_structure(bdd, mtbdd, object_properties, attack_tree,
                           fault_tree, impact, bdd.negated)

    # Sanity check
    assert mtbdd_manager.apply('+', mtbdd_manager.zero, mtbdd) == mtbdd


Path = dict[str, bool]


def _satisfying_path(paths: list[Path], path: Path) -> bool:
    """Check if a path satisfies a list of path constraints."""
    for p_constraint in paths:
        if all(p_constraint.get(k, v) == v for k, v in path.items()):
            return True
    return False


def test_satisfying_paths():
    assert _satisfying_path([{"DF": False}], {"DF": False})
    assert not _satisfying_path([{"DF": False}], {"DF": True})

    assert _satisfying_path([{"DF": False, "LP": True}],
                            {"DF": False, "LP": True})
    assert not _satisfying_path([{"DF": False, "LP": True}],
                                {"DF": False, "LP": False})

    assert _satisfying_path([{"DF": False, "LP": True}, {"DF": True}],
                            {"DF": False, "LP": True})
    assert _satisfying_path([{"DF": False, "LP": True}, {"DF": True}],
                            {"DF": True, "LP": False})
    assert not _satisfying_path([{"DF": False, "LP": True}, {"DF": True}],
                                {"DF": False, "LP": False})
    assert _satisfying_path([{"DF": False, "LP": True}, {"DF": True}],
                            {"DF": True})
    assert _satisfying_path([{"DF": False, "LP": True}, {"DF": True}],
                            {"DF": False})
    assert _satisfying_path([{"DF": False, "LP": True}, {"DF": True}],
                            {"LP": False})


def test_optimal_conf(caplog, paper_example_disconnected):
    attack_tree = paper_example_disconnected[0]
    attack_tree.nodes['EDLU']['data'].probability = Fraction('0.09')

    paths = optimal_conf("House", {}, *paper_example_disconnected)

    assert _satisfying_path(paths, {"DF": False, "LP": False, "IU": False})
    assert _satisfying_path(paths, {"DF": False, "LP": False, "HS": True})
    assert not _satisfying_path(paths, {"DF": True})
    assert not _satisfying_path(paths, {"LP": True})
    assert not _satisfying_path(paths, {"HS": False, "IU": True})
