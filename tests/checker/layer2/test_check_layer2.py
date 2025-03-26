import pytest

from odf.checker.exceptions import MissingConfigurationError, \
    MissingNodeProbabilityError, UnknownNodeError


def test_paper_example(do_check_layer2, paper_example_models):
    assert do_check_layer2(
        "{LP: 1,LJ: 1,DF: 1,HS: 0,IU: 1} P(FD && DGB || EDLU && FBO) == 0.050078",
        *paper_example_models)


def test_basic_attack_probability(do_check_layer2, paper_example_models):
    """Test basic probability calculation for a single attack node."""
    assert do_check_layer2(
        "{LP: 1} P(PL) == 0.10",
        *paper_example_models)


def test_basic_fault_probability(do_check_layer2, paper_example_models):
    """Test basic probability calculation for a single fault node."""
    assert do_check_layer2(
        "{LJ: 1} P(LGJ) == 0.70",
        *paper_example_models)


def test_probability_bounds(do_check_layer2, paper_example_models):
    """Test different probability bound operators."""
    # PL has probability 0.10
    config = "{LP: 1}"
    assert do_check_layer2(
        f"{config} P(PL) < 0.11",
        *paper_example_models)
    assert do_check_layer2(
        f"{config} P(PL) <= 0.10",
        *paper_example_models)
    assert do_check_layer2(
        f"{config} P(PL) >= 0.10",
        *paper_example_models)
    assert do_check_layer2(
        f"{config} P(PL) > 0.09",
        *paper_example_models)


def test_attack_fault_combination(do_check_layer2, paper_example_models):
    """Test probability calculation combining attack and fault tree nodes."""
    # Attack node PL (0.10) AND fault node LGJ (0.70)
    assert do_check_layer2(
        "{LP: 1,LJ: 1} P(PL && LGJ) == 0.07",
        *paper_example_models)


def test_or_gate_attack_nodes(do_check_layer2, paper_example_models):
    """Test OR gate probability calculation with attack nodes (should take max)."""
    # PL (0.10) OR DD (0.13) should take maximum
    assert do_check_layer2(
        "{LP: 1,DF: 1} P(PL || DD) == 0.13",
        *paper_example_models)


def test_and_gate_attack_nodes(do_check_layer2, paper_example_models):
    """Test AND gate probability calculation with attack nodes."""
    # PL (0.10) AND DD (0.13)
    assert do_check_layer2(
        "{LP: 1,DF: 1} P(PL && DD) == 0.013",
        *paper_example_models)


def test_missing_object_properties(do_check_layer2, paper_example_models):
    """Test error when required object properties are missing."""
    with pytest.raises(MissingConfigurationError,
                       match="Missing object properties") as exc_info:
        do_check_layer2(
            "{LP: 1} P(PL && LGJ) > 0.5",  # Missing LJ property
            *paper_example_models)
    assert "LJ" in str(exc_info.value)


def test_unused_object_properties(capsys, do_check_layer2,
                                  paper_example_models):
    """Test warning when configuration contains unused object properties."""
    do_check_layer2(
        "{LP: 1,LJ: 0,HS: 1} P(PL) > 0.05",  # HS is not used in formula
        *paper_example_models)
    captured = capsys.readouterr()
    assert "not used in the formula" in captured.out
    assert "HS" in captured.out


def test_undefined_node(do_check_layer2, paper_example_models):
    """Test error when using undefined node in formula."""
    with pytest.raises(UnknownNodeError,
                       match="You referenced an unknown node: UndefinedNode"):
        do_check_layer2(
            "{} P(UndefinedNode) > 0.5",
            *paper_example_models)


def test_complex_nested_formula(do_check_layer2, paper_example_models):
    """Test probability calculation with deeply nested formula.

    For ((PL || DD) && LGJ) || (EDLU && FBO), under config {LP: 1,LJ: 1,DF: 1}:
    
    DSL LGJ FBO | Prob(bF)   | PA                    | Product
    0   0   0   | 0.1896     | 0 (no LGJ, no FBO)    | 0
    0   0   1   | 0.0504     | 0.17 (EDLU&FBO)       | 0.008568
    0   1   0   | 0.4424     | 0.13 (PL||DD&LGJ)     | 0.057512
    0   1   1   | 0.1176     | 0.17 (max path)       | 0.019992
    1   0   0   | 0.0474     | 0 (no LGJ, no FBO)    | 0
    1   0   1   | 0.0126     | 0.17 (EDLU&FBO)       | 0.002142
    1   1   0   | 0.1106     | 0.13 (PL||DD&LGJ)     | 0.014378
    1   1   1   | 0.0294     | 0.17 (max path)       | 0.004998
                                               Total = 0.107590
    """
    assert do_check_layer2(
        "{LP: 1,LJ: 1,DF: 1,HS: 0,IU: 1} P((PL || DD) && LGJ || (EDLU && FBO)) == 0.107590",
        *paper_example_models)


def test_negated_complex_nested_formula(do_check_layer2, paper_example_models):
    """Test probability calculation with negated deeply nested formula.
    The root node of the BDD for this formula is complemented.
    
    For !((PL || DD) && LGJ || (EDLU && FBO)), under config {LP: 1,LJ: 1,DF: 1}:
    
    DSL LGJ FBO | Prob(bF)   | PA                     | Product
    0   0   0   | 0.1896     | 1 (no attack needed)   | 0.1896
    0   0   1   | 0.0504     | 1 (no attack needed)   | 0.0504
    0   1   0   | 0.4424     | 1 (no attack needed)   | 0.4424
    0   1   1   | 0.1176     | 1 (no attack needed)   | 0.1176
    1   0   0   | 0.0474     | 1 (no attack needed)   | 0.0474
    1   0   1   | 0.0126     | 1 (no attack needed)   | 0.0126
    1   1   0   | 0.1106     | 1 (no attack needed)   | 0.1106
    1   1   1   | 0.0294     | 1 (no attack needed)   | 0.0294
                                               Total = 1.0000
    """
    assert do_check_layer2(
        "{LP: 1,LJ: 1,DF: 1,HS: 0,IU: 1} P(!((PL || DD) && LGJ || (EDLU && FBO))) == 1.0",
        *paper_example_models)


def test_partially_negated_complex_nested_formula(do_check_layer2,
                                                  paper_example_models):
    """The BDD for this formula has two negated edges in the object property path."""
    assert do_check_layer2(
        "{LP: 1,LJ: 1,DF: 1,HS: 0,IU: 1} P(!((PL || DD) && LGJ) || (EDLU && FBO)) == 1.0",
        *paper_example_models)


def test_partially_negated_complex_nested_formula2(do_check_layer2,
                                                   paper_example_models):
    """The BDD for this formula has one negated edge in the object property path."""
    assert do_check_layer2(
        "{LP: 1,LJ: 1,DF: 1,HS: 0,IU: 1} P(!((PL || DD) && LGJ) || (EDLU && !FBO)) == 1.0",
        *paper_example_models)


def test_object_property_conditions(do_check_layer2, paper_example_models):
    """Test how object property conditions affect probability calculation."""
    # PL requires LP, LGJ requires LJ
    # When conditions not met, probability should be 0
    assert do_check_layer2(
        "{LP: 0} P(PL) == 0",  # LP condition not met
        *paper_example_models)
    assert do_check_layer2(
        "{LJ: 0} P(LGJ) == 0",  # LJ condition not met
        *paper_example_models)


def test_complemented_pattern2(do_check_layer2, paper_example_models):
    # YES
    """BDD with negated and non-negated node.

    For (PL && LGJ && DSL) || !((PL && LGJ) || (DSL && FBO)), under config {LP: 1,LJ: 1,HS: 0,IU: 1}:

    DSL LGJ FBO | Prob(bF)   | Expression Evaluation                                  | Product
    0   0   0   | 0.1896     | !((0 && 0) || (0 && 0)) = 1                            | 0.1896
    0   0   1   | 0.0504     | !((0 && 0) || (0 && 1)) = 1                            | 0.0504
    0   1   0   | 0.4424     | (0 && 1 && 0) || !((0 && 1) || (0 && 0)) = 1           | 0.4424
    0   1   1   | 0.1176     | (0 && 1 && 0) || !((0 && 1) || (0 && 1)) = 1           | 0.1176
    1   0   0   | 0.0474     | (0 && 0 && 1) || !((0 && 0) || (1 && 0)) = 1           | 0.0474
    1   0   1   | 0.0126     | (0 && 0 && 1) || !((0 && 0) || (1 && 1)) = 0           | 0
    1   1   0   | 0.1106     | (0 && 1 && 1) || !((0 && 1) || (1 && 0)) = 1           | 0.1106
    1   1   1   | 0.0294     | (0.10 && 1 && 1) || !((0.10 && 1) || (1 && 1)) = 0.10  | 0.00294
                                                                                Total = 0.96094
    """
    assert do_check_layer2(
        "{LP: 1,LJ: 1,HS: 0,IU: 1} P((PL && LGJ && DSL) || !((PL && LGJ) || (DSL && FBO))) == 0.96094",
        *paper_example_models)


def test_neg_complemented_pattern2(do_check_layer2, paper_example_models):
    """
    For !((PL && LGJ && DSL) || !((PL && LGJ) || (DSL && FBO))), under config {LP: 1,LJ: 1,HS: 0,IU: 1}
    = (!PL || !LGJ || !DSL) && ((PL && LGJ) || (DSL && FBO)):

    DSL LGJ FBO | Prob(bF)   | Expression Evaluation                                   | Product
    0   0   0   | 0.1896     | (1 || 1 || 1) && (0 || 0) = 0                           | 0
    0   0   1   | 0.0504     | (1 || 1 || 1) && (0 || 0) = 0                           | 0
    0   1   0   | 0.4424     | (0 || 0 || 1) && (0.10 || 0) = 0.10                     | 0.04424
    0   1   1   | 0.1176     | (0 || 0 || 1) && (0.10 || 0) = 0.10                     | 0.01176
    1   0   0   | 0.0474     | (1 || 1 || 0) && (0 || 0) = 0                           | 0
    1   0   1   | 0.0126     | (1 || 1 || 0) && (0 || 1) = 1                           | 0.0126
    1   1   0   | 0.1106     | (0 || 0 || 0) && (0.10 || 0) = 0                        | 0
    1   1   1   | 0.0294     | (1 || 0 || 0) && (0 || 1) = 1                           | 0.0294
                                                                                 Total = 0.098
    """
    assert do_check_layer2(
        "{LP: 1,LJ: 1,HS: 0,IU: 1} P(!((PL && LGJ && DSL) || !((PL && LGJ) || (DSL && FBO)))) == 0.098",
        *paper_example_models)


def test_complemented_pattern4(do_check_layer2, paper_example_models):
    """BDD with multiple negated edges in a row.

    For (PL && !DD) || (DD && !PL) || (LGJ && !DSL) || (DSL && !LGJ), under config {LP: 1,LJ: 1,DF: 1}:

    DSL LGJ | Prob(bF)   | Expression Evaluation                                      | Product
    0   0   | 0.24       | (0.10 && 0) || (0.13 && 0) = 0.13                          | 0.0312
    0   1   | 0.56       | (0.10 && 0) || (0.13 && 0) || (1 && 1) = 1                 | 0.5600
    1   0   | 0.06       | (0.10 && 0) || (0.13 && 0) || (0 && 1) || (1 && 1) = 1     | 0.0600
    1   1   | 0.14       | (0.10 && 0) || (0.13 && 0) || (1 && 0) || (0 && 0) = 0.13  | 0.0182
                                                                                Total = 0.6694
    """
    assert do_check_layer2(
        "{LP: 1,LJ: 1,DF: 1} P((PL && !DD) || (DD && !PL) || (LGJ && !DSL) || (DSL && !LGJ)) == 0.6694",
        *paper_example_models)


def test_neg_complemented_pattern4(do_check_layer2, paper_example_models):
    """BDD with multiple negated edges in a row.

    For !((PL && !DD) || (DD && !PL) || (LGJ && !DSL) || (DSL && !LGJ)), under config {LP: 1,LJ: 1,DF: 1}
    = (!PL || DD) && (!DD || PL) && (!LGJ || DSL) && (!DSL || LGJ):

    DSL LGJ | Prob(bF)   | Expression Evaluation                                        | Product
    0   0   | 0.24       | (1 || 0.13) && (1 || 0.10) && (1 || 0) && (1 || 0) = 1      | 0.24
    0   1   | 0.56       | (1 || 0.13) && (1 || 0.10) && (0 || 0) && (1 || 1) = 0      | 0
    1   0   | 0.06       | (1 || 0.13) && (1 || 0.10) && (1 || 1) && (0 || 0) = 0      | 0
    1   1   | 0.14       | (1 || 0.13) && (1 || 0.10) && (0 || 1) && (0 || 1) = 1      | 0.14
                                                                                  Total = 0.38
    """
    assert do_check_layer2(
        "{LP: 1,LJ: 1,DF: 1} P(!((PL && !DD) || (DD && !PL) || (LGJ && !DSL) || (DSL && !LGJ))) == 0.38",
        *paper_example_models)


def test_implies_operator(do_check_layer2, paper_example_models):
    """Test probability calculation with implies operator.

    For PL => LGJ under config {LP: 1,LJ: 1}:
    The implication is equivalent to !PL || LGJ

    LGJ | Prob(bF)   | PA (maximizing probability)           | Product
    0   | 0.30       | !PL = Don't attempt PL = 1.0          | 0.30
    1   | 0.70       | Any strategy satisfies formula = 1.0   | 0.70
                                                      Total = 1.00
    """
    # P(PL => LGJ) tests if successful lock picking implies lock jam
    assert do_check_layer2(
        "{LP: 1,LJ: 1} P(PL => LGJ) == 1.0",
        *paper_example_models)


def test_only_fault_tree_nodes(do_check_layer2, paper_example_models):
    """Test probability calculation with only fault tree nodes.
    Complex combination of LGJ, DSL, and FBO with negations.

    For (LGJ && !DSL) || (!LGJ && DSL && FBO) || (DSL && !FBO), under config {LJ: 1}:

    DSL LGJ FBO | Prob(bF)   | Expression Evaluation                                    | Product
    0   0   0   | 0.1896     | (0 && 1) || (1 && 0 && 0) || (0 && 1) = 0                | 0
    0   0   1   | 0.0504     | (0 && 1) || (1 && 0 && 1) || (0 && 0) = 0                | 0
    0   1   0   | 0.4424     | (1 && 1) || (0 && 0 && 0) || (0 && 1) = 1                | 0.4424
    0   1   1   | 0.1176     | (1 && 1) || (0 && 0 && 1) || (0 && 0) = 1                | 0.1176
    1   0   0   | 0.0474     | (0 && 0) || (1 && 1 && 0) || (1 && 1) = 1                | 0.0474
    1   0   1   | 0.0126     | (0 && 0) || (1 && 1 && 1) || (1 && 0) = 1                | 0.0126
    1   1   0   | 0.1106     | (1 && 0) || (0 && 1 && 0) || (1 && 1) = 1                | 0.1106
    1   1   1   | 0.0294     | (1 && 0) || (0 && 1 && 1) || (1 && 0) = 0                | 0
                                                                                  Total = 0.7306
    """
    assert do_check_layer2(
        "{LJ: 1,IU: 1,HS: 0} P((LGJ && !DSL) || (!LGJ && DSL && FBO) || (DSL && !FBO)) == 0.7306",
        *paper_example_models)


def test_only_attack_tree_nodes(do_check_layer2, paper_example_models):
    """Test probability calculation with only attack tree nodes.
    Complex combination of PL, DD, and EDLU with negations.

    For (PL && !DD) || (!PL && DD && EDLU) || (DD && !EDLU), under config {LP: 1,DF: 1}:
    Since this formula only contains attack nodes, we find the maximum probability:

    Strategy 1: (PL && !DD) = Attempt PL (0.10), don't attempt DD (1.0) = 0.10
    Strategy 2: (!PL && DD && EDLU) = Don't attempt PL (1.0), attempt DD (0.13), attempt EDLU (0.17) = 0.13 * 0.17 = 0.0221
    Strategy 3: (DD && !EDLU) = Attempt DD (0.13), don't attempt EDLU (1.0) = 0.13

    The maximum probability is 0.13 from Strategy 3.
    """
    assert do_check_layer2(
        "{LP: 1,DF: 1} P((PL && !DD) || (!PL && DD && EDLU) || (DD && !EDLU)) == 0.13",
        *paper_example_models)


def test_tautology(do_check_layer2, paper_example_models):
    """Test probability calculation of a tautology using multiple variables.
    Formula structure: (A && B) || !(A && B) is always true.

    For (PL && DD) || !(PL && DD), under config {LP: 1,DF: 1}:

    This is a tautology (always true) regardless of whether the attacker attempts PL or DD.
    No matter what strategy the attacker chooses, the formula will always be satisfied.
    Therefore, the probability is 1.0.
    """
    assert do_check_layer2(
        "{} P((PL && DD) || !(PL && DD)) == 1",
        *paper_example_models)

    assert do_check_layer2(
        "{} P((LGJ && DSL) || !(LGJ && DSL)) == 1",
        *paper_example_models)


def test_contradiction(do_check_layer2, paper_example_models):
    """Test probability calculation of a contradiction using multiple variables.
    Formula structure: (A && B) && !(A && B) is always false.

    For (PL && DD) && !(PL && DD), under config {LP: 1,DF: 1}:

    This is a contradiction (always false) regardless of whether the attacker attempts PL or DD.
    No matter what strategy the attacker chooses, the formula will never be satisfied.
    Therefore, the probability is 0.0.
    """
    assert do_check_layer2(
        "{} P((PL && DD) && !(PL && DD)) == 0",
        *paper_example_models)

    assert do_check_layer2(
        "{} P((LGJ && DSL) && !(LGJ && DSL)) == 0",
        *paper_example_models)


def test_attack_tree_independent(do_check_layer2, paper_example_models):
    """Test formula where fault tree nodes don't affect the result.
    The attack tree part (PL && !PL) is always false.

    For (PL && !PL) || ((LGJ && !DSL) || (!LGJ && DSL && FBO)), under config {LP: 1,LJ: 1}:

    The attack tree part (PL && !PL) is a contradiction, so it's always 0.
    The formula simplifies to: (LGJ && !DSL) || (!LGJ && DSL && FBO)

    DSL LGJ FBO | Prob(bF)   | Expression Evaluation                        | Product
    0   0   0   | 0.1896     | (0 && 1) || (1 && 0 && 0) = 0                | 0
    0   0   1   | 0.0504     | (0 && 1) || (1 && 0 && 1) = 0                | 0
    0   1   0   | 0.4424     | (1 && 1) || (0 && 0 && 0) = 1                | 0.4424
    0   1   1   | 0.1176     | (1 && 1) || (0 && 0 && 1) = 1                | 0.1176
    1   0   0   | 0.0474     | (0 && 0) || (1 && 1 && 0) = 0                | 0
    1   0   1   | 0.0126     | (0 && 0) || (1 && 1 && 1) = 1                | 0.0126
    1   1   0   | 0.1106     | (1 && 0) || (0 && 1 && 0) = 0                | 0
    1   1   1   | 0.0294     | (1 && 0) || (0 && 1 && 1) = 0                | 0
                                                                      Total = 0.5726
    """
    assert do_check_layer2(
        "{LJ: 1,HS: 0,IU: 1} P((PL && !PL) || ((LGJ && !DSL) || (!LGJ && DSL && FBO))) == 0.5726",
        *paper_example_models)


def test_fault_tree_independent(do_check_layer2, paper_example_models):
    """Test formula where attack tree nodes don't affect the result.
    The fault tree part (LGJ && !LGJ) is always false.

    For (LGJ && !LGJ) || ((PL && !DD) || (DD && !PL) || EDLU), under config {LP: 1,LJ: 1,DF: 1}:

    The fault tree part (LGJ && !LGJ) is a contradiction, so it's always 0.
    The formula simplifies to: (PL && !DD) || (DD && !PL) || EDLU

    Strategy 1: (PL && !DD) = Attempt PL (0.10), don't attempt DD (1.0) = 0.10
    Strategy 2: (DD && !PL) = Attempt DD (0.13), don't attempt PL (1.0) = 0.13
    Strategy 3: EDLU = Attempt EDLU (0.17) = 0.17

    The maximum probability is 0.17 from Strategy 3.
    """
    assert do_check_layer2(
        "{LP: 1,DF: 1} P((LGJ && !LGJ) || ((PL && !DD) || (DD && !PL) || EDLU)) == 0.17",
        *paper_example_models)


def test_missing_probability_attack_tree(do_check_layer2,
                                         transform_disruption_tree_str,
                                         fault_tree_paper_example,
                                         object_graph_paper_example):
    """Test error when an attack tree node is missing its probability."""
    # Create attack tree with PL node missing probability
    attack_tree = transform_disruption_tree_str("""
    toplevel Attacker_breaks_in_house;
    Attacker_breaks_in_house or EDLU FD;
    FD or PL DD;
    
    Attacker_breaks_in_house objects=[House,Inhabitant];
    EDLU objects=[Door] prob=0.17;
    FD objects=[Door];
    PL objects=[Lock] cond=(LP);  // Missing probability
    DD objects=[Door] cond=(DF) prob=0.13;
    """)

    with pytest.raises(MissingNodeProbabilityError) as exc_info:
        do_check_layer2(
            "{LP: 1,DF: 1} P(PL) > 0.5",
            attack_tree, fault_tree_paper_example, object_graph_paper_example)
    assert "PL" in str(exc_info.value)
    assert "attack tree" in str(exc_info.value)


def test_missing_probability_fault_tree(do_check_layer2,
                                        attack_tree_paper_example,
                                        transform_disruption_tree_str,
                                        object_graph_paper_example):
    """Test error when a fault tree node is missing its probability."""
    # Create fault tree with LGJ node missing probability
    fault_tree = transform_disruption_tree_str("""
    toplevel Fire_and_impossible_escape;
    Fire_and_impossible_escape and FBO DGB;
    DGB and DSL LGJ;
    
    Fire_and_impossible_escape objects=[House,Inhabitant] cond=(Inhab_in_House);
    FBO objects=[House,Inhabitant] cond=(!HS && IU) prob=0.21;
    DGB objects=[Door];
    DSL objects=[Door] prob=0.20;
    LGJ objects=[Lock] cond=(LJ);  // Missing probability
    """)

    with pytest.raises(MissingNodeProbabilityError) as exc_info:
        do_check_layer2(
            "{LP: 1,LJ: 1} P(LGJ) > 0.5",
            attack_tree_paper_example, fault_tree, object_graph_paper_example)
    assert "LGJ" in str(exc_info.value)
    assert "fault tree" in str(exc_info.value)
