import pytest
from dd import cudd
from lark import Tree, Token

from odf.checker.layer1.layer1_bdd import Layer1BDDTransformer, \
    intermediate_node_to_bdd, ConditionTransformer
from odf.parser.parser import parse
from odf.__main__ import extract_parse_trees
from odf.transformers.disruption_tree import DisruptionTreeTransformer
from odf.transformers.object_graph import ObjectGraphTransformer


def parse_and_transform_to_bdd(formula_str: str, attack_tree_str: str,
                               fault_tree_str: str, object_graph_str: str):
    """Parse input strings and transform the formula to a BDD."""
    full_input = f"""
{attack_tree_str}

{fault_tree_str}

{object_graph_str}

[formulas]
{{}} {formula_str};
"""
    parse_tree = parse(full_input)
    [attack_parse_tree, fault_parse_tree,
     object_parse_tree, formula_parse_tree] = extract_parse_trees(parse_tree)

    attack_tree = DisruptionTreeTransformer().transform(attack_parse_tree)
    fault_tree = DisruptionTreeTransformer().transform(fault_parse_tree)
    object_graph = ObjectGraphTransformer().transform(object_parse_tree)

    query = formula_parse_tree.children[0]
    assert query.data == "layer1_query"
    formula = query.children[0].children[1]

    transformer = Layer1BDDTransformer(attack_tree, fault_tree, object_graph)
    return transformer, transformer.transform(formula)


@pytest.fixture
def attack_tree_str():
    """Create an attack tree with basic and non-basic nodes."""
    return """[odg.attack_tree]
    toplevel Root;
    Root and BasicAttack ComplexAttack;
    BasicAttack prob = 0.5;
    ComplexAttack and SubAttack1 SubAttack2;
    ComplexAttack cond = (obj_prop1 && obj_prop2);
    SubAttack1 prob = 0.3;
    SubAttack2 prob = 0.4;"""


@pytest.fixture
def fault_tree_str():
    """Create a fault tree with basic and complex nodes."""
    return """[odg.fault_tree]
    toplevel Root;
    Root and BasicFault ComplexFault;
    BasicFault prob = 0.3;
    ComplexFault and SubFault1 SubFault2;
    ComplexFault cond = (obj_prop4 && obj_prop5);
    SubFault1 prob = 0.2;
    SubFault2 prob = 0.1 cond = (obj_prop6);"""


@pytest.fixture
def object_graph_str():
    """Create an object graph with properties."""
    return """[odg.object_graph]
    toplevel Root;
    Root has Object1 Object2;
    Object1 properties = [obj_prop1, obj_prop2];
    Object2 properties = [obj_prop3];"""


def test_basic_node_bdd_creation(attack_tree_str, fault_tree_str,
                                 object_graph_str):
    """Test creating BDD for a basic node reference."""
    transformer, bdd = parse_and_transform_to_bdd("BasicAttack",
                                                  attack_tree_str,
                                                  fault_tree_str,
                                                  object_graph_str)

    expected = transformer.bdd.var('BasicAttack')
    assert bdd == expected


def test_basic_node_negation(attack_tree_str, fault_tree_str, object_graph_str):
    """Test creating BDD for a negated basic node."""
    transformer, bdd = parse_and_transform_to_bdd("!BasicAttack",
                                                  attack_tree_str,
                                                  fault_tree_str,
                                                  object_graph_str)

    expected = ~transformer.bdd.var('BasicAttack')
    assert bdd == expected


def test_object_property_bdd(attack_tree_str, fault_tree_str, object_graph_str):
    """Test creating BDD for an object property."""
    transformer, bdd = parse_and_transform_to_bdd("obj_prop1", attack_tree_str,
                                                  fault_tree_str,
                                                  object_graph_str)

    expected = transformer.bdd.var('obj_prop1')
    assert bdd == expected


def test_complex_node_bdd(attack_tree_str, fault_tree_str, object_graph_str):
    """Test creating BDD for a complex node (which uses AND gate and conditions)."""
    transformer, bdd = parse_and_transform_to_bdd("ComplexAttack",
                                                  attack_tree_str,
                                                  fault_tree_str,
                                                  object_graph_str)

    # ComplexAttack is (SubAttack1 AND SubAttack2) AND (obj_prop1 AND obj_prop2)
    expected = (transformer.bdd.var('SubAttack1') & transformer.bdd.var(
        'SubAttack2')) & \
               (transformer.bdd.var('obj_prop1') & transformer.bdd.var(
                   'obj_prop2'))
    assert bdd == expected


def test_combined_formula_bdd(attack_tree_str, fault_tree_str,
                              object_graph_str):
    """Test creating BDD for a formula combining multiple nodes and operators."""
    formula = "(BasicAttack && ComplexFault) || obj_prop3"
    transformer, bdd = parse_and_transform_to_bdd(formula, attack_tree_str,
                                                  fault_tree_str,
                                                  object_graph_str)

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


def test_intermediate_node_bdd(attack_tree_str, fault_tree_str,
                               object_graph_str, parse_rule):
    """Test intermediate_node_to_bdd function directly."""
    # Parse and transform the attack tree
    attack_tree = DisruptionTreeTransformer().transform(
        parse_rule(attack_tree_str, "attack_tree"))

    # Create BDD manager and test intermediate node conversion
    bdd_manager = cudd.BDD()
    bdd_manager.declare('SubAttack1', 'SubAttack2', 'obj_prop1', 'obj_prop2')

    # Test ComplexAttack node which has an AND gate and conditions
    bdd = intermediate_node_to_bdd(bdd_manager, attack_tree, 'ComplexAttack')
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

    attack_tree = DisruptionTreeTransformer().transform(parse_rule(attack_tree_str, "attack_tree"))

    # Initialize transformer with empty trees/graph since we only need the BDD manager
    transformer = Layer1BDDTransformer(None, None, None)
    bdd_manager = transformer.bdd

    # Declare all variables
    basic_nodes = [f"Basic{i}" for i in range(1, 16)]
    props = [f"prop{i}" for i in range(1, 48)]
    bdd_manager.declare(*basic_nodes, *props)

    # Test the root node which should combine everything
    bdd = intermediate_node_to_bdd(bdd_manager, attack_tree, 'Root')

    # Build expected BDD bottom-up following the tree structure
    def v(name): return bdd_manager.var(name)

    # Helper for implies
    def implies(a, b): return ~a | b

    # Level 4
    basic13_cond = bdd_manager.apply('equiv', v('prop45'),
                                     bdd_manager.apply('xor', v('prop46'), v('prop47')))
    l4a = (v('Basic12') | (v('Basic13') & basic13_cond)) & (~v('prop25') & v('prop26'))
    l4b = (v('Basic14') & v('Basic15')) & (v('prop27') | ~v('prop28'))

    # Level 3
    l3a = (l4a & l4b) & (v('prop15') | ~v('prop16'))

    basic5_cond = bdd_manager.apply('xor', v('prop33'), v('prop34'))
    l3b = (v('Basic4') | (v('Basic5') & basic5_cond)) & (v('prop17') & v('prop18'))

    basic7_cond = (implies(v('prop35'), v('prop36')) & ~v('prop37'))
    l3c = (v('Basic6') & (v('Basic7') & basic7_cond)) & (~v('prop19') | v('prop20'))

    basic9_cond = (bdd_manager.apply('equiv', v('prop38'), v('prop39')) | v('prop40'))
    basic11_cond = (bdd_manager.apply('xor', v('prop41'), v('prop42')) & implies(v('prop43'), v('prop44')))
    l3d = (v('Basic8') | (v('Basic9') & basic9_cond)) & (v('prop21') & ~v('prop22'))
    l3e = (v('Basic10') & (v('Basic11') & basic11_cond)) & (v('prop23') | v('prop24'))

    # Level 2
    l2a = (l3a & l3b) & (v('prop7') & ~v('prop8'))

    basic1_cond = implies(v('prop29'), v('prop30'))
    l2b = ((v('Basic1') & basic1_cond) | l3c) & (v('prop9') | v('prop10'))

    l2c = (l3d & l3e) & (~v('prop11') | v('prop12'))

    basic3_cond = bdd_manager.apply('equiv', v('prop31'), v('prop32'))
    l2d = (v('Basic2') | (v('Basic3') & basic3_cond)) & (v('prop13') & v('prop14'))

    # Level 1 and Root
    l1a = (l2a | l2b) & (v('prop3') | v('prop4'))
    l1b = (l2c & l2d) & (~v('prop5') & v('prop6'))
    expected = (l1a & l1b) & (v('prop1') & v('prop2'))

    assert bdd == expected

# Test cases for formulas with boolean evidence
def test_basic_evidence_substitution(attack_tree_str, fault_tree_str, object_graph_str):
    """Test basic substitution of nodes with boolean evidence."""
    # Set BasicAttack to true
    transformer, bdd = parse_and_transform_to_bdd(
        "BasicAttack [BasicAttack:1]", 
        attack_tree_str, fault_tree_str, object_graph_str
    )
    assert bdd == transformer.bdd.true

    # Set BasicAttack to false
    transformer, bdd = parse_and_transform_to_bdd(
        "BasicAttack [BasicAttack:0]", 
        attack_tree_str, fault_tree_str, object_graph_str
    )
    assert bdd == transformer.bdd.false

def test_complex_formula_with_evidence(attack_tree_str, fault_tree_str, object_graph_str):
    """Test evidence in a complex formula affecting multiple nodes."""
    formula = "(BasicAttack || BasicFault) && ComplexAttack [BasicAttack:1, BasicFault:0]"
    transformer, bdd = parse_and_transform_to_bdd(
        formula, attack_tree_str, fault_tree_str, object_graph_str
    )
    
    # With BasicAttack=true and BasicFault=false, the formula reduces to just ComplexAttack
    expected = (transformer.bdd.var('SubAttack1') & transformer.bdd.var('SubAttack2')) & \
               (transformer.bdd.var('obj_prop1') & transformer.bdd.var('obj_prop2'))
    assert bdd == expected

@pytest.mark.xfail(reason="Currently failing due to incorrect handling of intermediate nodes")
def test_intermediate_node_evidence(attack_tree_str, fault_tree_str, object_graph_str):
    """Test evidence on intermediate nodes affecting their basic events."""
    transformer, bdd = parse_and_transform_to_bdd(
        "ComplexAttack || BasicAttack [ComplexAttack:1]",
        attack_tree_str, fault_tree_str, object_graph_str
    )
    expected = transformer.bdd.true  # Formula is true regardless of BasicAttack
    assert bdd == expected

    # Setting ComplexAttack to false
    transformer, bdd = parse_and_transform_to_bdd(
        "ComplexAttack || BasicAttack [ComplexAttack:0]",
        attack_tree_str, fault_tree_str, object_graph_str
    )
    expected = transformer.bdd.var('BasicAttack')  # Formula reduces to just BasicAttack
    assert bdd == expected

def test_object_property_evidence(attack_tree_str, fault_tree_str, object_graph_str):
    """Test evidence on object properties."""
    # Test with ComplexAttack which has object property conditions
    transformer, bdd = parse_and_transform_to_bdd(
        "ComplexAttack [obj_prop1:1, obj_prop2:1]",
        attack_tree_str, fault_tree_str, object_graph_str
    )
    # Only the gates and basic events remain, conditions are satisfied
    expected = transformer.bdd.var('SubAttack1') & transformer.bdd.var('SubAttack2')
    assert bdd == expected

@pytest.mark.xfail(reason="Currently failing due to incorrect handling of intermediate nodes")
def test_multiple_evidence_combined(attack_tree_str, fault_tree_str, object_graph_str):
    """Test multiple pieces of evidence affecting different parts of the formula."""
    formula = "(ComplexAttack || BasicFault) && (BasicAttack || ComplexFault)"
    evidence = "[ComplexAttack:1, BasicFault:0, obj_prop4:1, obj_prop5:1]"
    
    transformer, bdd = parse_and_transform_to_bdd(
        f"{formula} {evidence}",
        attack_tree_str, fault_tree_str, object_graph_str
    )
    
    # First part reduces to true (ComplexAttack:1), second part becomes (BasicAttack || (SubFault1 && SubFault2))
    expected = transformer.bdd.var('BasicAttack') | \
               (transformer.bdd.var('SubFault1') & 
                (transformer.bdd.var('SubFault2') & transformer.bdd.var('obj_prop6')))
    assert bdd == expected

def test_evidence_with_node_conditions(attack_tree_str, fault_tree_str, object_graph_str):
    """Test evidence affecting nodes that have conditions."""
    # ComplexFault has condition (obj_prop4 && obj_prop5)
    # SubFault2 has condition (obj_prop6)
    transformer, bdd = parse_and_transform_to_bdd(
        "ComplexFault [SubFault1:1, obj_prop4:1]",
        attack_tree_str, fault_tree_str, object_graph_str
    )
    
    # Still need SubFault2 and obj_prop5 to be true
    expected = transformer.bdd.var('SubFault2') & \
               transformer.bdd.var('obj_prop5') & \
               transformer.bdd.var('obj_prop6')
    assert bdd == expected

@pytest.mark.xfail(reason="Currently failing due to maybe incorrect handling of evidence")
def test_evidence_overrides_conditions(attack_tree_str, fault_tree_str, object_graph_str):
    """Test that evidence on a node overrides its conditions."""
    # ComplexFault has conditions but we set it directly to true
    transformer, bdd = parse_and_transform_to_bdd(
        "(SubFault2 && BasicAttack) || BasicFault [SubFault2:1]",
        attack_tree_str, fault_tree_str, object_graph_str
    )
    
    # Formula reduces to (true && BasicAttack) || BasicFault
    expected = transformer.bdd.var('BasicAttack') | transformer.bdd.var('BasicFault')
    # Currently, below is happening:
    # expected = (transformer.bdd.var('obj_prop6') & transformer.bdd.var('BasicAttack')) | transformer.bdd.var('BasicFault')

    assert bdd == expected
