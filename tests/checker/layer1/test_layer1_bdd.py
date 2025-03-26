import pytest
from dd import cudd
from lark import Tree, Token

from odf.checker.exceptions import (NodeAncestorEvidenceError,
                                    EvidenceAncestorEvidenceError,
                                    NonModuleNodeError,
                                    InvalidNodeEvidenceError)
from odf.checker.layer1.layer1_bdd import Layer1BDDInterpreter, \
    ConditionTransformer
from odf.transformers.disruption_tree import DisruptionTreeTransformer


def test_basic_node_bdd_creation(parse_and_get_bdd):
    """Test creating BDD for a basic node reference."""
    transformer, bdd = parse_and_get_bdd("BasicAttack")

    expected = transformer.bdd.var('BasicAttack')
    assert bdd == expected


def test_basic_node_negation(parse_and_get_bdd):
    """Test creating BDD for a negated basic node."""
    transformer, bdd = parse_and_get_bdd("!BasicAttack")

    expected = ~transformer.bdd.var('BasicAttack')
    assert bdd == expected


def test_object_property_bdd(parse_and_get_bdd):
    """Test creating BDD for an object property."""
    transformer, bdd = parse_and_get_bdd("obj_prop1")

    expected = transformer.bdd.var('obj_prop1')
    assert bdd == expected


def test_complex_node_bdd(parse_and_get_bdd):
    """Test creating BDD for a complex node (which uses AND gate and conditions)."""
    transformer, bdd = parse_and_get_bdd("ComplexAttack")

    # ComplexAttack is (SubAttack1 AND SubAttack2) AND (obj_prop1 AND obj_prop2)
    expected = (transformer.bdd.var('SubAttack1') & transformer.bdd.var(
        'SubAttack2')) & \
               (transformer.bdd.var('obj_prop1') & transformer.bdd.var(
                   'obj_prop2'))
    assert bdd == expected


def test_combined_formula_bdd(parse_and_get_bdd):
    """Test creating BDD for a formula combining multiple nodes and operators."""
    formula = "(BasicAttack && ComplexFault) || obj_prop3"
    transformer, bdd = parse_and_get_bdd(formula)

    # ComplexFault is (SubFault1 AND SubFault2) AND (obj_prop4 AND obj_prop5)
    complex_fault = (
                            transformer.bdd.var('SubFault1') &
                            (transformer.bdd.var('SubFault2') &
                             transformer.bdd.var('obj_prop6'))
                    ) & (transformer.bdd.var('obj_prop4') &
                         transformer.bdd.var('obj_prop5'))
    expected = ((transformer.bdd.var('BasicAttack') & complex_fault)
                | transformer.bdd.var('obj_prop3'))
    assert bdd == expected


def test_condition_transformer():
    """Test the ConditionTransformer directly."""
    bdd_manager = cudd.BDD()
    bdd_manager.declare('obj_prop1', 'obj_prop2')
    transformer = ConditionTransformer(bdd_manager)

    # Create a simple condition tree: obj_prop1 && obj_prop2
    condition_tree = Tree('and_formula', [
        Tree('node_atom', [Token('NODE_NAME', 'obj_prop1')]),
        Tree('node_atom', [Token('NODE_NAME', 'obj_prop2')])
    ])

    bdd = transformer.transform(condition_tree)
    expected = bdd_manager.var('obj_prop1') & bdd_manager.var('obj_prop2')
    assert bdd == expected


def test_intermediate_node_bdd(attack_tree1):
    """Test intermediate_node_to_bdd function directly."""
    # Create BDD manager and test intermediate node conversion
    transformer = Layer1BDDInterpreter(attack_tree1, None, None)
    bdd_manager = transformer.bdd
    bdd_manager.declare('SubAttack1', 'SubAttack2', 'obj_prop1', 'obj_prop2')

    # Test ComplexAttack node which has an AND gate and conditions
    bdd = transformer.intermediate_node_to_bdd(attack_tree1, 'ComplexAttack')
    expected = (bdd_manager.var('SubAttack1') & bdd_manager.var('SubAttack2')) & \
               (bdd_manager.var('obj_prop1') & bdd_manager.var('obj_prop2'))
    assert bdd == expected


def test_deeply_nested_nodes(parse_rule):
    """Test creating BDD for deeply nested nodes with mixed gates and conditions."""
    # Create a complex attack tree with 4 levels of nesting and various conditions
    attack_tree_str = """[odg.attack_tree]
    toplevel Root;
    Root and Level1A Level1B;
    Level1A or Level2A Level2B;
    Level1B and Level2C Level2D;
    Level2A and Level3A Level3B;
    Level2B or Basic1 Level3C;
    Level2C and Level3D Level3E;
    Level2D or Basic2 Basic3;
    Level3A and Level4A Level4B;
    Level3B or Basic4 Basic5;
    Level3C and Basic6 Basic7;
    Level3D or Basic8 Basic9;
    Level3E and Basic10 Basic11;
    Level4A or Basic12 Basic13;
    Level4B and Basic14 Basic15;
    
    Root cond = (prop1 && prop2);
    Level1A cond = (prop3 || prop4);
    Level1B cond = (!prop5 && prop6);
    Level2A cond = (prop7 && !prop8);
    Level2B cond = (prop9 || prop10);
    Level2C cond = (!prop11 || prop12);
    Level2D cond = (prop13 && prop14);
    Level3A cond = (prop15 || !prop16);
    Level3B cond = (prop17 && prop18);
    Level3C cond = (!prop19 || prop20);
    Level3D cond = (prop21 && !prop22);
    Level3E cond = (prop23 || prop24);
    Level4A cond = (!prop25 && prop26);
    Level4B cond = (prop27 || !prop28);
    
    Basic1 prob = 0.1 cond = (prop29 => prop30);
    Basic2 prob = 0.2;
    Basic3 prob = 0.3 cond = (prop31 == prop32);
    Basic4 prob = 0.1;
    Basic5 prob = 0.2 cond = (prop33 != prop34);
    Basic6 prob = 0.3;
    Basic7 prob = 0.1 cond = ((prop35 => prop36) && !prop37);
    Basic8 prob = 0.2;
    Basic9 prob = 0.3 cond = ((prop38 == prop39) || prop40);
    Basic10 prob = 0.1;
    Basic11 prob = 0.2 cond = ((prop41 != prop42) && (prop43 => prop44));
    Basic12 prob = 0.3;
    Basic13 prob = 0.1 cond = (prop45 == (prop46 != prop47));
    Basic14 prob = 0.2;
    Basic15 prob = 0.3;"""

    attack_tree = DisruptionTreeTransformer().transform(
        parse_rule(attack_tree_str, "attack_tree"))

    # Initialize transformer with empty trees/graph since we only need the BDD manager
    transformer = Layer1BDDInterpreter(None, None, None)
    bdd_manager = transformer.bdd

    # Declare all variables
    basic_nodes = [f"Basic{i}" for i in range(1, 16)]
    props = [f"prop{i}" for i in range(1, 48)]
    bdd_manager.declare(*basic_nodes, *props)

    # Test the root node which should combine everything
    bdd = transformer.intermediate_node_to_bdd(attack_tree, 'Root')

    # Build expected BDD bottom-up following the tree structure
    def v(name): return bdd_manager.var(name)

    # Helper for implies
    def implies(a, b): return ~a | b

    # Level 4
    basic13_cond = bdd_manager.apply('equiv', v('prop45'),
                                     bdd_manager.apply('xor', v('prop46'),
                                                       v('prop47')))
    l4a = (v('Basic12') | (v('Basic13') & basic13_cond)) & (
            ~v('prop25') & v('prop26'))
    l4b = (v('Basic14') & v('Basic15')) & (v('prop27') | ~v('prop28'))

    # Level 3
    l3a = (l4a & l4b) & (v('prop15') | ~v('prop16'))

    basic5_cond = bdd_manager.apply('xor', v('prop33'), v('prop34'))
    l3b = (v('Basic4') | (v('Basic5') & basic5_cond)) & (
            v('prop17') & v('prop18'))

    basic7_cond = (implies(v('prop35'), v('prop36')) & ~v('prop37'))
    l3c = (v('Basic6') & (v('Basic7') & basic7_cond)) & (
            ~v('prop19') | v('prop20'))

    basic9_cond = (bdd_manager.apply('equiv', v('prop38'), v('prop39')) | v(
        'prop40'))
    basic11_cond = (
            bdd_manager.apply('xor', v('prop41'), v('prop42')) & implies(
        v('prop43'), v('prop44')))
    l3d = (v('Basic8') | (v('Basic9') & basic9_cond)) & (
            v('prop21') & ~v('prop22'))
    l3e = (v('Basic10') & (v('Basic11') & basic11_cond)) & (
            v('prop23') | v('prop24'))

    # Level 2
    l2a = (l3a & l3b) & (v('prop7') & ~v('prop8'))

    basic1_cond = implies(v('prop29'), v('prop30'))
    l2b = ((v('Basic1') & basic1_cond) | l3c) & (v('prop9') | v('prop10'))

    l2c = (l3d & l3e) & (~v('prop11') | v('prop12'))

    basic3_cond = bdd_manager.apply('equiv', v('prop31'), v('prop32'))
    l2d = (v('Basic2') | (v('Basic3') & basic3_cond)) & (
            v('prop13') & v('prop14'))

    # Level 1 and Root
    l1a = (l2a | l2b) & (v('prop3') | v('prop4'))
    l1b = (l2c & l2d) & (~v('prop5') & v('prop6'))
    expected = (l1a & l1b) & (v('prop1') & v('prop2'))

    assert bdd == expected


# Test cases for formulas with boolean evidence
def test_basic_evidence_substitution(parse_and_get_bdd):
    """Test basic substitution of nodes with boolean evidence."""
    # Set BasicAttack to true
    transformer, bdd = parse_and_get_bdd(
        "BasicAttack [BasicAttack: 1]")
    assert bdd == transformer.bdd.true

    # Set BasicAttack to false
    transformer, bdd = parse_and_get_bdd(
        "BasicAttack [BasicAttack: 0]")
    assert bdd == transformer.bdd.false


def test_complex_formula_with_evidence(parse_and_get_bdd):
    """Test evidence in a complex formula affecting multiple nodes."""
    formula = "(BasicAttack || BasicFault) && ComplexAttack [BasicAttack: 1, BasicFault: 0]"
    transformer, bdd = parse_and_get_bdd(formula)

    # With BasicAttack=true and BasicFault=false, the formula reduces to just ComplexAttack
    expected = (transformer.bdd.var('SubAttack1') & transformer.bdd.var(
        'SubAttack2')) & \
               (transformer.bdd.var('obj_prop1') & transformer.bdd.var(
                   'obj_prop2'))
    assert bdd == expected


# @pytest.mark.xfail(
#     reason="Currently failing due to incorrect handling of intermediate nodes")
def test_intermediate_node_evidence(parse_and_get_bdd):
    """Test evidence on intermediate nodes affecting their basic events."""
    transformer, bdd = parse_and_get_bdd(
        "ComplexAttack || BasicAttack [ComplexAttack: 1]")
    expected = transformer.bdd.true  # Formula is true regardless of BasicAttack
    assert bdd == expected

    transformer, bdd = parse_and_get_bdd(
        "ComplexAttack || BasicAttack [ComplexAttack: 0]")
    expected = transformer.bdd.var(
        'BasicAttack')  # Formula reduces to just BasicAttack
    assert bdd == expected

    transformer, bdd = parse_and_get_bdd(
        "ComplexAttack || BasicFault [ComplexAttack: 1]")
    expected = transformer.bdd.true  # Formula is true regardless of BasicFault
    assert bdd == expected

    transformer, bdd = parse_and_get_bdd(
        "ComplexAttack || BasicFault [ComplexAttack: 0]")
    expected = transformer.bdd.var(
        'BasicFault')  # Formula reduces to just BasicFault
    assert bdd == expected


def test_object_property_evidence(parse_and_get_bdd):
    """Test evidence on object properties."""
    # Test with ComplexAttack which has object property conditions
    transformer, bdd = parse_and_get_bdd(
        "ComplexAttack [obj_prop1: 1, obj_prop2: 1]")
    # Only the gates and basic events remain, conditions are satisfied
    expected = transformer.bdd.var('SubAttack1') & transformer.bdd.var(
        'SubAttack2')
    assert bdd == expected


# @pytest.mark.xfail(
#     reason="Currently failing due to incorrect handling of intermediate nodes")
def test_multiple_evidence_combined(parse_and_get_bdd):
    """Test multiple pieces of evidence affecting different parts of the formula."""
    formula = "(ComplexAttack || BasicFault) && (BasicAttack || ComplexFault)"
    evidence = "[ComplexAttack: 1, BasicFault: 0, obj_prop4: 1, obj_prop5: 1]"

    transformer, bdd = parse_and_get_bdd(f"{formula} {evidence}")

    # First part reduces to true (ComplexAttack: 1), second part becomes (BasicAttack || (SubFault1 && SubFault2))
    expected = transformer.bdd.var('BasicAttack') | \
               (transformer.bdd.var('SubFault1') &
                (transformer.bdd.var('SubFault2') & transformer.bdd.var(
                    'obj_prop6')))
    assert bdd == expected


def test_multiple_intermediate_evidence(parse_and_get_bdd):
    """Test evidence applied on multiple intermediate nodes in different branches.
    In the formula "ComplexAttack || ComplexFault [ComplexAttack: 1, ComplexFault: 0]",
    forcing ComplexAttack to true makes the overall formula evaluate to true even if 
    ComplexFault is forced to false.
    """
    transformer, bdd = parse_and_get_bdd(
        "ComplexAttack && !ComplexFault [ComplexAttack: 1, ComplexFault: 0]")
    # Here, forcing ComplexAttack to 1 should make the OR resolve to true.
    assert bdd == transformer.bdd.true


def test_object_property_with_condition_evidence(parse_and_get_bdd):
    """Test that evidence on an object property overrides its condition in a node.
    For instance, if ComplexAttack uses conditions on obj_prop1 and obj_prop2,
    forcing obj_prop1 to false (with evidence) should make the overall condition unsatisfied.
    """
    transformer, bdd = parse_and_get_bdd("ComplexAttack [obj_prop1: 0]")
    expected = transformer.bdd.false
    assert bdd == expected


def test_conflicting_nested_evidence(parse_and_get_bdd):
    formula = "ComplexAttack [SubAttack1: 1] [SubAttack1: 0, SubAttack2: 1]"
    transformer, bdd = parse_and_get_bdd(formula)
    expected = transformer.bdd.var("obj_prop1") & transformer.bdd.var(
        "obj_prop2")
    assert bdd == expected


def test_vice_versa_nested_evidence(parse_and_get_bdd):
    formula = "(ComplexAttack [SubAttack1: 0]) [SubAttack1: 1, SubAttack2: 1]"
    transformer, bdd = parse_and_get_bdd(formula)
    expected = transformer.bdd.false
    assert bdd == expected


def test_evidence_on_mixed_gates_tree(parse_and_get_bdd,
                                      attack_tree_mixed_gates):
    transformer, bdd = parse_and_get_bdd("RootA [PathA: 1]",
                                         attack_tree=attack_tree_mixed_gates)
    assert bdd == transformer.bdd.true
    transformer, bdd = parse_and_get_bdd("RootA [PathB: 1]",
                                         attack_tree=attack_tree_mixed_gates)
    assert bdd == transformer.bdd.true

    transformer, bdd = parse_and_get_bdd("PathC [SubPathC1: 0]",
                                         attack_tree=attack_tree_mixed_gates)
    assert bdd == transformer.bdd.false
    transformer, bdd = parse_and_get_bdd("PathC [SubPathC2: 0]",
                                         attack_tree=attack_tree_mixed_gates)
    assert bdd == transformer.bdd.false
    transformer, bdd = parse_and_get_bdd("PathC [SubPathC2: 1]",
                                         attack_tree=attack_tree_mixed_gates)
    manager = transformer.bdd
    assert bdd == (
            manager.var('Attack7') & manager.var('obj_prop1') | manager.var(
        'Attack8') & manager.var('obj_prop2')) & manager.var('SubPathC3')
    transformer, bdd = parse_and_get_bdd("PathC [SubPathC1: 1]",
                                         attack_tree=attack_tree_mixed_gates)
    manager = transformer.bdd
    assert bdd == (
            manager.var('Attack9') & (
            manager.var('Attack10') | manager.var('Attack11'))
    ) & manager.var('SubPathC3')


def test_evidence_mixed_gates_and_mrs(parse_and_get_bdd,
                                      attack_tree_mixed_gates):
    transformer, bdd = parse_and_get_bdd("MRS(PathC) [SubPathC1: 1]",
                                         attack_tree=attack_tree_mixed_gates)
    manager = transformer.bdd
    assert bdd == manager.var("Attack9") & manager.var("SubPathC3") & \
           manager.apply('xor', manager.var("Attack10"),
                         manager.var("Attack11"))

    transformer, bdd = parse_and_get_bdd("MRS(PathC) [SubPathC1: 0]",
                                         attack_tree=attack_tree_mixed_gates)
    manager = transformer.bdd
    assert bdd == manager.false  # PathC requires SubPathC1 which is forced to 0

    transformer, bdd = parse_and_get_bdd("MRS(PathC [SubPathC1: 1])",
                                         attack_tree=attack_tree_mixed_gates)
    manager = transformer.bdd
    assert bdd == manager.var("Attack9") & manager.var("SubPathC3") & \
           manager.apply('xor', manager.var("Attack10"),
                         manager.var("Attack11"))

    transformer, bdd = parse_and_get_bdd("MRS(PathC [SubPathC1: 0])",
                                         attack_tree=attack_tree_mixed_gates)
    manager = transformer.bdd
    assert bdd == manager.false  # SubPathC1=0 makes PathC unsatisfiable

    transformer, complex_neg = parse_and_get_bdd(
        "MRS(PathA && !PathB) [StepA1: 1, SubPathB1: 0]",
        attack_tree=attack_tree_mixed_gates)
    manager = transformer.bdd
    assert complex_neg == (
            manager.var('StepA2') & ~manager.var('Attack5') & ~manager.var(
        'Attack6'))

    transformer, complex_neg = parse_and_get_bdd(
        "MRS(PathA && !PathB) [StepA1: 1, SubPathB1: 1]",
        attack_tree=attack_tree_mixed_gates)
    manager = transformer.bdd
    assert complex_neg == manager.false  # PathB becomes true via SubPathB1

    transformer, complex_neg = parse_and_get_bdd(
        "MRS(PathA && PathB) [StepA1: 1, SubPathB1: 0]",
        attack_tree=attack_tree_mixed_gates)
    manager = transformer.bdd
    assert complex_neg == (manager.var('StepA2') & (
            manager.var('Attack5') & manager.var('Attack6')))

    transformer, complex_neg = parse_and_get_bdd(
        "MRS(PathA && PathB) [StepA1: 1, SubPathB1: 1]",
        attack_tree=attack_tree_mixed_gates)
    manager = transformer.bdd
    assert complex_neg == (manager.var('StepA2') & (
            ~manager.var('Attack5') & ~manager.var('Attack6')))

    transformer, complex_neg = parse_and_get_bdd(
        "MRS(PathA || !PathB) [StepA1: 1, SubPathB1: 0]",
        attack_tree=attack_tree_mixed_gates)
    manager = transformer.bdd
    assert complex_neg == manager.false

    transformer, complex_neg = parse_and_get_bdd(
        "MRS(PathA || !PathB) [StepA1: 0, SubPathB1: 0]",
        attack_tree=attack_tree_mixed_gates)
    manager = transformer.bdd
    assert complex_neg == ~manager.var('StepA2') & (
            ~manager.var('Attack5') & ~manager.var('Attack6'))

    transformer, complex_neg = parse_and_get_bdd(
        "MRS(PathA || PathB [StepA1: 1, SubPathB1: 0])",
        attack_tree=attack_tree_mixed_gates)
    manager = transformer.bdd
    assert complex_neg == manager.apply(
        'xor',
        manager.var('StepA2') & ~manager.var('Attack5') & ~manager.var(
            'Attack6'),
        ~manager.var('StepA2') & manager.var('Attack5') & manager.var(
            'Attack6'))

    transformer, complex_neg = parse_and_get_bdd(
        "MRS(PathA || PathB) [StepA1: 1, SubPathB1: 0]",
        attack_tree=attack_tree_mixed_gates)
    manager = transformer.bdd
    assert complex_neg == manager.var('StepA2') & ~manager.var(
        'Attack5') & ~manager.var(
        'Attack6')

    transformer, complex_neg = parse_and_get_bdd(
        "MRS(PathA || PathB) [StepA1: 1, SubPathB1: 1]",
        attack_tree=attack_tree_mixed_gates)
    manager = transformer.bdd
    assert complex_neg == manager.false


def test_nested_contradicting_evidence(parse_and_get_bdd):
    """Test handling of nested contradicting evidence."""
    # Inner evidence should override outer evidence
    formula = "(ComplexAttack [SubAttack1: 0]) [SubAttack1: 1, SubAttack2: 1]"
    transformer, bdd = parse_and_get_bdd(formula)
    # Inner evidence makes SubAttack1 false
    expected = transformer.bdd.false  # ComplexAttack is false because SubAttack1 is false
    assert bdd == expected

    formula = "ComplexAttack [SubAttack1: 1, SubAttack2: 1]"
    transformer, bdd = parse_and_get_bdd(formula)
    expected = transformer.bdd.var('obj_prop1') & transformer.bdd.var(
        'obj_prop2')
    assert bdd == expected

    # Multiple layers of contradicting evidence
    formula = """
        (((ComplexAttack [SubAttack1: 1, SubAttack2: 1]) [SubAttack1: 0]) || 
         (BasicAttack [BasicAttack: 0])) [BasicAttack: 1]
    """
    transformer, bdd = parse_and_get_bdd(formula)
    # For ComplexAttack: innermost makes both subs true, then SubAttack1: 0 takes precedence
    # For BasicAttack: inner false overrides outer true
    # obj_prop1 && obj_prop2 still required for ComplexAttack
    expected = transformer.bdd.var('obj_prop1') & transformer.bdd.var(
        'obj_prop2')
    assert bdd == expected

    formula = """
        (((ComplexAttack [SubAttack1: 1, SubAttack2: 1]) [SubAttack1: 0]) && 
         (BasicAttack [BasicAttack: 0])) [BasicAttack: 1]
    """
    transformer, bdd = parse_and_get_bdd(formula)
    # For ComplexAttack: innermost makes both subs true, then SubAttack1: 0 takes precedence
    # For BasicAttack: inner false overrides outer true
    # obj_prop1 && obj_prop2 still required for ComplexAttack
    expected = transformer.bdd.false
    assert bdd == expected


def test_evidence_with_node_conditions(parse_and_get_bdd):
    """Test evidence affecting nodes that have conditions."""
    # ComplexFault has condition (obj_prop4 && obj_prop5)
    # SubFault2 has condition (obj_prop6)
    transformer, bdd = parse_and_get_bdd(
        "ComplexFault [SubFault1: 1, obj_prop4: 1]")

    # Still need SubFault2 and obj_prop5 to be true
    expected = transformer.bdd.var('SubFault2') & \
               transformer.bdd.var('obj_prop5') & \
               transformer.bdd.var('obj_prop6')
    assert bdd == expected


# @pytest.mark.xfail(
#     reason="Currently failing due to maybe incorrect handling of evidence")
def test_evidence_overrides_conditions(parse_and_get_bdd):
    """Test that evidence on a node overrides its conditions."""
    # ComplexFault has conditions but we set it directly to true
    transformer, bdd = parse_and_get_bdd(
        "(SubFault2 && BasicAttack) || BasicFault [SubFault2: 1]")

    # Formula reduces to (true && BasicAttack) || BasicFault
    expected = transformer.bdd.var('BasicAttack') | transformer.bdd.var(
        'BasicFault')
    # Currently, below is happening:
    # expected = (transformer.bdd.var('obj_prop6') & transformer.bdd.var('BasicAttack')) | transformer.bdd.var('BasicFault')

    assert bdd == expected


def test_mrs_simple_formula(parse_and_get_bdd):
    """Test MRS with a simple formula consisting of a single basic node."""
    formula = "MRS(BasicAttack)"
    transformer, bdd = parse_and_get_bdd(formula)

    var_name = 'BasicAttack'
    prime_var = f"{var_name}'1"

    expected_formula = transformer.bdd.add_expr(
        f"{var_name} & ~(\\E {prime_var}: ({prime_var} => {var_name}) & ({prime_var} ^ {var_name}) & {prime_var})")

    assert bdd == expected_formula


def test_mrs_disjunction(parse_and_get_bdd):
    """Test MRS with a disjunction of two basic nodes."""
    formula = "MRS(BasicAttack || BasicFault)"
    transformer, bdd = parse_and_get_bdd(formula)

    # For MRS(A | B), we want the formula to be true, and no proper subset of variables to make it true
    # In a disjunction, proper subsets would be just A or just B being true
    a_var = transformer.bdd.var('BasicAttack')
    b_var = transformer.bdd.var('BasicFault')

    disjunction = a_var | b_var
    proper_subset_a = a_var & ~b_var  # Just A being true
    proper_subset_b = ~a_var & b_var  # Just B being true
    proper_subsets = proper_subset_a | proper_subset_b

    expected = disjunction & proper_subsets

    assert bdd == expected


def test_mrs_with_object_properties(parse_and_get_bdd):
    """Test that MRS has no effect on object properties."""
    formula = "MRS(obj_prop1 || obj_prop2)"
    transformer, bdd = parse_and_get_bdd(formula)

    op1 = transformer.bdd.var('obj_prop1')
    op2 = transformer.bdd.var('obj_prop2')

    expected = op1 | op2

    assert bdd == expected


def test_mrs_nested(parse_and_get_bdd):
    """Test nested MRS operations."""
    formula = "MRS(MRS(BasicAttack || obj_prop1))"
    transformer, bdd = parse_and_get_bdd(formula)

    # First, compute the inner MRS: MRS(BasicAttack || obj_prop1)
    a_var = transformer.bdd.var('BasicAttack')
    op1 = transformer.bdd.var('obj_prop1')

    inner_disjunction = a_var | op1
    inner_proper_subset_a = a_var & ~op1
    inner_proper_subset_op1 = ~a_var & op1
    inner_proper_subsets = inner_proper_subset_a | inner_proper_subset_op1

    inner_mrs = inner_disjunction & inner_proper_subsets

    # The outer MRS should have no effect
    expected = inner_mrs

    assert bdd == expected


def test_mrs_with_evidence(parse_and_get_bdd):
    """Test MRS with boolean evidence."""
    formula = "MRS(BasicAttack || BasicFault) [BasicFault: 1]"
    transformer, bdd = parse_and_get_bdd(formula)

    # With BasicFault=1, the formula MRS(BasicAttack || BasicFault) becomes MRS(BasicAttack || True)
    # Since MRS checks for minimal sets, and BasicFault=True is already sufficient,
    # BasicAttack would need to be False for a minimal set
    expected = ~transformer.bdd.var('BasicAttack')

    assert bdd == expected


@pytest.fixture
def complex_attack_tree(transform_disruption_tree_str):
    """Create an attack tree with a more complex structure having both AND and OR gates."""
    return transform_disruption_tree_str("""
    toplevel Root;
    Root and MixedGateNode SimpleNode;
    MixedGateNode or AndGateNode1 AndGateNode2;
    AndGateNode1 and BasicAttack1 BasicAttack2;
    AndGateNode2 and BasicAttack3 OrGateNode;
    OrGateNode or BasicAttack4 BasicAttack5;
    SimpleNode and BasicAttack6 BasicAttack7;
    
    BasicAttack1 prob = 0.1;
    BasicAttack2 prob = 0.2;
    BasicAttack3 prob = 0.3;
    BasicAttack4 prob = 0.4;
    BasicAttack5 prob = 0.5;
    BasicAttack6 prob = 0.6;
    BasicAttack7 prob = 0.7;
    
    MixedGateNode cond = (obj_prop1) objects=[Object1];
    AndGateNode2 cond = (obj_prop2) objects=[Object1];
    """)


def test_mrs_complex_intermediate_node(complex_attack_tree, parse_and_get_bdd):
    """Test MRS with a complex intermediate node that has both AND and OR gate descendants."""
    formula = "MRS(MixedGateNode)"
    transformer, bdd = parse_and_get_bdd(formula,
                                         attack_tree=complex_attack_tree)

    # Break down the structure of MixedGateNode:
    # MixedGateNode = (AndGateNode1 | AndGateNode2) & obj_prop1
    # AndGateNode1 = BasicAttack1 & BasicAttack2
    # AndGateNode2 = BasicAttack3 & OrGateNode & obj_prop2
    # OrGateNode = BasicAttack4 | BasicAttack5

    ba1 = transformer.bdd.var('BasicAttack1')
    ba2 = transformer.bdd.var('BasicAttack2')
    ba3 = transformer.bdd.var('BasicAttack3')
    ba4 = transformer.bdd.var('BasicAttack4')
    ba5 = transformer.bdd.var('BasicAttack5')
    op1 = transformer.bdd.var('obj_prop1')
    op2 = transformer.bdd.var('obj_prop2')

    # Generate all possible minimal combinations of variables that might satisfy the formula
    combinations = [
        # For the left branch: (ba1 & ba2) & op1
        [ba1, ba2, op1, ~ba3, ~ba4, ~ba5, ~op2],
        [ba1, ba2, op1, ~ba3, ~ba4, ~ba5, op2],  # op2 can have either value

        # For the right branch, with ba4: (ba3 & ba4 & op2) & op1
        [ba3, ba4, op2, op1, ~ba1, ~ba2, ~ba5],

        # For the right branch, with ba5: (ba3 & ba5 & op2) & op1
        [ba3, ba5, op2, op1, ~ba1, ~ba2, ~ba4]
    ]

    proper_subsets = transformer.bdd.false

    # For each combination that makes the formula true
    for combination in combinations:
        subset = transformer.bdd.true
        for i in range(len(combination)):
            subset = subset & combination[i]
        proper_subsets = proper_subsets | subset

    expected = proper_subsets

    assert bdd == expected

    # Create the MRS formula directly as expressed in the implementation
    # Define the original MixedGateNode formula
    mixed_gate_expr = "((BasicAttack1 & BasicAttack2) | (BasicAttack3 & (BasicAttack4 | BasicAttack5) & obj_prop2)) & obj_prop1"

    # Define primed variables (using prime_count=1 as in the first call to mrs)
    primed_vars = ["BasicAttack1'1", "BasicAttack2'1", "BasicAttack3'1",
                   "BasicAttack4'1", "BasicAttack5'1"]

    # Create implications part: (p'i => xi)
    implications = " & ".join([f"({pv} => {pv[:-2]})" for pv in primed_vars])

    # Create XOR part: (p'i ^ xi) | (p'j ^ xj) | ...
    xor_terms = " | ".join([f"({pv} ^ {pv[:-2]})" for pv in primed_vars])

    # Create primed formula by replacing each variable with its primed version
    primed_formula = mixed_gate_expr
    for var in ["BasicAttack1", "BasicAttack2", "BasicAttack3", "BasicAttack4",
                "BasicAttack5"]:
        primed_formula = primed_formula.replace(var, f"{var}'1")

    # Build the full MRS formula
    existential_part = f"\\E {', '.join(primed_vars)}: ({implications}) & ({xor_terms}) & ({primed_formula})"
    mrs_expr = f"({mixed_gate_expr}) & ~({existential_part})"

    expected_literal = transformer.bdd.add_expr(mrs_expr)

    assert bdd == expected_literal


def test_intermediate_evidence_with_direct_descendant(parse_and_get_bdd):
    with pytest.raises(NodeAncestorEvidenceError,
                       match=r".*SubAttack1.*ComplexAttack.*"):
        parse_and_get_bdd("ComplexAttack && SubAttack1 [ComplexAttack: 1]")

    with pytest.raises(NodeAncestorEvidenceError,
                       match=r".*SubAttack2.*ComplexAttack.*"):
        parse_and_get_bdd(
            "ComplexAttack || (SubAttack2 && obj_prop1) [ComplexAttack: 0]")


def test_intermediate_evidence_with_nested_descendant(parse_and_get_bdd,
                                                      attack_tree_mixed_gates):
    with pytest.raises(NodeAncestorEvidenceError,
                       match=r".*Attack11.*PathC.*"):
        parse_and_get_bdd("RootA || !Attack11 [PathC: 1]",
                          attack_tree=attack_tree_mixed_gates)
    with pytest.raises(NodeAncestorEvidenceError,
                       match=r".*Attack11.*PathC.*"):
        parse_and_get_bdd("RootA || !Attack11 [PathC: 0]",
                          attack_tree=attack_tree_mixed_gates)


def test_multiple_descendants_in_formula(parse_and_get_bdd,
                                         attack_tree_mixed_gates):
    """
    When evidence is provided for the intermediate node but more than one of its descendant nodes
    occur in the same formula, the parser should raise an error.
    """
    with pytest.raises(NodeAncestorEvidenceError,
                       match=r".*SubAttack1.*ComplexAttack.*"):
        parse_and_get_bdd(
            "ComplexAttack && (SubAttack1 || SubAttack2) [ComplexAttack: 1]")

    with pytest.raises(NodeAncestorEvidenceError,
                       match=r".*Attack7.*SubPathC1.*"):
        parse_and_get_bdd("PathC && (SubPathC1 || Attack7) [SubPathC1: 1]",
                          attack_tree=attack_tree_mixed_gates)

    with pytest.raises(NodeAncestorEvidenceError,
                       match=r".*Attack10.*SubPathC2.*"):
        parse_and_get_bdd("PathC || (SubPathC1 && Attack10) [SubPathC2: 1]",
                          attack_tree=attack_tree_mixed_gates)


def test_evidence_intermediate_child_in_other_part(parse_and_get_bdd):
    transformer, bdd = parse_and_get_bdd(
        "(ComplexAttack [ComplexAttack:1]) && SubAttack1")
    assert bdd == transformer.bdd.var('SubAttack1')
    transformer, bdd = parse_and_get_bdd(
        "(RootA [ComplexAttack:1]) || SubAttack1")
    assert bdd == transformer.bdd.var('SubAttack1') | transformer.bdd.var(
        'BasicAttack')
    transformer, bdd = parse_and_get_bdd("""
        ((ComplexAttack [ComplexAttack:1]) && 
         (SubAttack1 [SubAttack1:1]))
        """)
    assert bdd == transformer.bdd.true


def test_evidence_on_children(parse_and_get_bdd):
    with pytest.raises(EvidenceAncestorEvidenceError,
                       match=r".*SubAttack1.*ComplexAttack.*"):
        parse_and_get_bdd("ComplexAttack [ComplexAttack: 1, SubAttack1: 1]")

    with pytest.raises(EvidenceAncestorEvidenceError,
                       match=r".*SubAttack1.*RootA.*"):
        parse_and_get_bdd("RootA [RootA: 1, SubAttack1: 1]")

    with pytest.raises(EvidenceAncestorEvidenceError,
                       match=r".*SubAttack1.*ComplexAttack.*"):
        parse_and_get_bdd("RootA [ComplexAttack: 1, SubAttack1: 1]")

    transformer, bdd = parse_and_get_bdd(
        "(RootA [ComplexAttack: 1]) [SubAttack1: 1]")
    assert bdd == transformer.bdd.var('BasicAttack')

    with pytest.raises(EvidenceAncestorEvidenceError,
                       match=r".*SubAttack1.*ComplexAttack.*"):
        parse_and_get_bdd("(RootA [SubAttack1: 1]) [ComplexAttack: 1]")

    with pytest.raises(EvidenceAncestorEvidenceError,
                       match=r".*SubFault1.*ComplexFault.*"):
        parse_and_get_bdd("""ComplexFault [
            SubFault1: 1,             // Set basic event true
            obj_prop4: 0,             
            ComplexFault: 1           // Override everything to true
        ]""")


def test_evidence_on_non_module_nodes(parse_and_get_bdd,
                                      transform_disruption_tree_str):
    """Test that setting evidence on non-module nodes raises appropriate errors."""
    # Create a DAG where some nodes are not modules:
    #      Root
    #     /   \
    #    A     B
    #   / \   / \
    #  C   D E   F
    #       \   /
    #        G
    tree_str = """
    toplevel Root;
    Root and A B;
    A and C D;
    B and E F;
    D or G;
    F or G;

    A cond=(obj_prop1) objects=[Object1];
    B cond=(obj_prop2) objects=[Object1];
    C prob=0.1;
    D prob=0.2;
    E prob=0.3;
    F prob=0.4;
    G prob=0.5;
    """
    complex_tree = transform_disruption_tree_str(tree_str)

    # Test valid module nodes (Root, C, E, G)
    transformer, bdd = parse_and_get_bdd("Root [Root: 1]",
                                         attack_tree=complex_tree)
    assert bdd == transformer.bdd.true

    transformer, bdd = parse_and_get_bdd("C [C: 1]", attack_tree=complex_tree)
    assert bdd == transformer.bdd.true

    transformer, bdd = parse_and_get_bdd("E [E: 1]", attack_tree=complex_tree)
    assert bdd == transformer.bdd.true

    transformer, bdd = parse_and_get_bdd("G [G: 1]", attack_tree=complex_tree)
    assert bdd == transformer.bdd.true

    # Test invalid module nodes (A, B, D, F)
    with pytest.raises(NonModuleNodeError,
                       match=r".*A.*not a module.*"):
        parse_and_get_bdd("A || C [A: 1]", attack_tree=complex_tree)

    with pytest.raises(NonModuleNodeError,
                       match=r".*B.*not a module.*"):
        parse_and_get_bdd("B || E [B: 1]", attack_tree=complex_tree)

    with pytest.raises(NonModuleNodeError,
                       match=r".*D.*not a module.*"):
        parse_and_get_bdd("D || G [D: 1]", attack_tree=complex_tree)

    with pytest.raises(NonModuleNodeError,
                       match=r".*F.*not a module.*"):
        parse_and_get_bdd("F || G [F: 1]", attack_tree=complex_tree)

    # Test that the error is raised even when evidence on the non-module node
    # is combined with evidence on other valid nodes
    with pytest.raises(NonModuleNodeError,
                       match=r".*D.*not a module.*"):
        parse_and_get_bdd("Root && D [Root: 1, D: 1]", attack_tree=complex_tree)

    with pytest.raises(NonModuleNodeError,
                       match=r".*F.*not a module.*"):
        parse_and_get_bdd("(Root && F [Root: 1]) [F: 1]",
                          attack_tree=complex_tree)
    with pytest.raises(NonModuleNodeError,
                       match=r".*F.*not a module.*"):
        parse_and_get_bdd("(Root && F [F: 1]) [Root: 1]",
                          attack_tree=complex_tree)


def test_invalid_node_evidence(parse_and_get_bdd):
    """Test that providing evidence for a non-existent node raises an error."""
    with pytest.raises(InvalidNodeEvidenceError, match=r".*NonExistentNode.*"):
        parse_and_get_bdd("ComplexAttack [NonExistentNode: 1]")

    with pytest.raises(InvalidNodeEvidenceError, match=r".*FakeNode.*"):
        parse_and_get_bdd("ComplexAttack && BasicAttack [FakeNode: 0]")

    # Test with nested evidence
    with pytest.raises(InvalidNodeEvidenceError, match=r".*NonExistentNode.*"):
        parse_and_get_bdd("(ComplexAttack [NonExistentNode: 1]) && BasicAttack")

    # Test with multiple pieces of evidence including an invalid one
    with pytest.raises(InvalidNodeEvidenceError, match=r".*InvalidNode.*"):
        parse_and_get_bdd(
            "ComplexAttack [BasicAttack: 1, InvalidNode: 0, SubAttack1: 1]")
