import pytest
from lark import Tree, Token

from odf.transformers.disruption_tree import DisruptionTreeTransformer
from odf.transformers.object_graph import ObjectGraphTransformer
from odf.checker.layer1.layer1_bdd import Layer1FormulaVisitor


@pytest.fixture
def attack_tree(parse_rule):
    """Create an attack tree with basic and non-basic nodes."""
    tree_str = """toplevel Root;
    Root and BasicAttack ComplexAttack;
    BasicAttack prob = 0.5;
    ComplexAttack and SubAttack1 SubAttack2;
    ComplexAttack cond = (obj_prop1 && obj_prop2);
    SubAttack1 prob = 0.3;
    SubAttack2 prob = 0.4;
    """
    tree = parse_rule(tree_str, "disruption_tree")
    return DisruptionTreeTransformer().transform(tree)


@pytest.fixture
def fault_tree(parse_rule):
    """Create a fault tree with a basic node."""
    tree_str = """toplevel Root;
    Root and BasicFault ComplexFault;
    BasicFault prob = 0.3;
    ComplexFault and SubFault1 SubFault2;
    ComplexFault cond = (obj_prop4 && obj_prop5);
    SubFault1 prob = 0.2;
    SubFault2 prob = 0.1 cond = (obj_prop6);
    """
    tree = parse_rule(tree_str, "disruption_tree")
    return DisruptionTreeTransformer().transform(tree)


@pytest.fixture
def object_graph(parse_rule):
    """Create an object graph with properties."""
    graph_str = """toplevel Root;
    Root has Object1 Object2;
    Object1 properties = [obj_prop1, obj_prop2];
    Object2 properties = [obj_prop3];
    """
    tree = parse_rule(graph_str, "object_graph_tree")
    return ObjectGraphTransformer().transform(tree)


@pytest.fixture
def visitor(attack_tree, fault_tree, object_graph):
    return Layer1FormulaVisitor(attack_tree, fault_tree, object_graph)


def create_node_atom(name: str) -> Tree:
    """Helper to create a node_atom tree with the given name."""
    return Tree("node_atom", [Token("NODE_NAME", name)])


def test_visit_basic_attack_node(visitor):
    """Test visiting a basic attack node."""
    visitor.node_atom(create_node_atom("BasicAttack"))
    assert "BasicAttack" in visitor.attack_nodes
    assert len(visitor.fault_nodes) == 0
    assert len(visitor.object_properties) == 0


def test_visit_basic_fault_node(visitor):
    """Test visiting a basic fault node."""
    visitor.node_atom(create_node_atom("BasicFault"))
    assert "BasicFault" in visitor.fault_nodes
    assert len(visitor.attack_nodes) == 0
    assert len(visitor.object_properties) == 0


def test_visit_complex_attack_node_with_descendants(visitor):
    """Test visiting a non-basic attack node with basic descendants."""
    visitor.node_atom(create_node_atom("ComplexAttack"))

    # Should collect all basic descendants
    assert "SubAttack1" in visitor.attack_nodes
    assert "SubAttack2" in visitor.attack_nodes

    # Should collect object properties from condition
    assert "obj_prop1" in visitor.object_properties
    assert "obj_prop2" in visitor.object_properties


def test_visit_complex_fault_node_with_descendants(visitor):
    """Test visiting a non-basic fault node with basic descendants."""
    visitor.node_atom(create_node_atom("ComplexFault"))

    # Should collect all basic descendants
    assert "SubFault1" in visitor.fault_nodes
    assert "SubFault2" in visitor.fault_nodes

    # Should collect object properties from conditions of node and descendants
    assert "obj_prop4" in visitor.object_properties
    assert "obj_prop5" in visitor.object_properties
    assert "obj_prop6" in visitor.object_properties


def test_visit_object_property(visitor):
    """Test visiting an object property."""
    visitor.node_atom(create_node_atom("obj_prop1"))
    assert len(visitor.attack_nodes) == 0
    assert len(visitor.fault_nodes) == 0
    assert "obj_prop1" in visitor.object_properties


def test_visit_unknown_node(visitor):
    """Test visiting an unknown node raises ValueError."""
    with pytest.raises(ValueError, match="Unknown node: UnknownNode"):
        visitor.node_atom(create_node_atom("UnknownNode"))


def test_object_properties_collection_from_condition(visitor):
    """Test that object properties are collected from node conditions."""
    visitor.node_atom(create_node_atom("ComplexAttack"))
    assert "obj_prop1" in visitor.object_properties
    assert "obj_prop2" in visitor.object_properties
    assert len(visitor.object_properties) == 2


def test_multiple_visits_accumulate_nodes(visitor):
    """Test that multiple node visits accumulate nodes and properties."""
    visitor.node_atom(create_node_atom("BasicAttack"))
    visitor.node_atom(create_node_atom("ComplexAttack"))
    visitor.node_atom(create_node_atom("obj_prop3"))

    # Should contain both basic and descendant nodes
    assert "BasicAttack" in visitor.attack_nodes
    assert "SubAttack1" in visitor.attack_nodes
    assert "SubAttack2" in visitor.attack_nodes
    assert len(visitor.attack_nodes) == 3
    assert len(visitor.fault_nodes) == 0

    # Should contain properties from both node conditions and object graph
    assert "obj_prop1" in visitor.object_properties
    assert "obj_prop2" in visitor.object_properties
    assert "obj_prop3" in visitor.object_properties
    assert len(visitor.object_properties) == 3
