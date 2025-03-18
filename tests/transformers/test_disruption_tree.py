from fractions import Fraction

import pytest
from lark.exceptions import VisitError

from odf.transformers.disruption_tree import DisruptionTreeTransformer


def test_basic_disruption_tree(parse_rule):
    """Test transforming a basic disruption tree with a single node."""
    transformer = DisruptionTreeTransformer()
    tree = parse_rule("""toplevel A;
    A prob = 0.5;""", "disruption_tree")

    result = transformer.transform(tree)
    node = result.nodes["A"]["data"]
    assert node.name == "A"
    assert node.probability == Fraction("0.5")
    assert node.objects is None
    assert node.object_properties == set()
    assert node.gate_type is None


def test_disruption_tree_with_all_attributes(parse_rule):
    """Test transforming a disruption tree with node having all attributes."""
    transformer = DisruptionTreeTransformer()
    tree = parse_rule("""toplevel A;
    A prob = 0.5 objects = [obj1, obj2] cond = (x && y);
    """, "disruption_tree")

    result = transformer.transform(tree)
    node = result.nodes["A"]["data"]
    assert node.name == "A"
    assert node.probability == Fraction("0.5")
    assert node.objects == ["obj1", "obj2"]
    assert node.object_properties == {"x", "y"}
    assert node.gate_type is None


def test_disruption_tree_with_intermediate_node(parse_rule):
    """Test transforming a disruption tree with intermediate AND node."""
    transformer = DisruptionTreeTransformer()
    tree = parse_rule("""toplevel Root;
    Root and A B;
    A prob = 0.5;
    B;
    """, "disruption_tree")

    result = transformer.transform(tree)

    # Check nodes exist
    assert "Root" in result.nodes
    assert "A" in result.nodes
    assert "B" in result.nodes

    # Check edges
    assert list(result.edges()) == [("Root", "A"), ("Root", "B")]

    # Check node attributes
    assert result.nodes["Root"]["data"].gate_type == "and"
    assert result.nodes["A"]["data"].probability == Fraction("0.5")
    assert result.nodes["B"]["data"].probability is None
    assert result.nodes["A"]["data"].gate_type is None
    assert result.nodes["B"]["data"].gate_type is None


def test_duplicate_basic_node_definition_raises_error(parse_rule):
    """Test that defining a basic node multiple times raises an error."""
    transformer = DisruptionTreeTransformer()
    tree = parse_rule("""toplevel A;
    A;
    A prob = 0.5 objects = [obj1];
    """, "disruption_tree")

    with pytest.raises(VisitError) as excinfo:
        transformer.transform(tree)
    assert "Basic node 'A' is already defined" in str(excinfo.value.orig_exc)


def test_duplicate_intermediate_node_definition_raises_error(parse_rule):
    """Test that defining an intermediate node multiple times raises an error."""
    transformer = DisruptionTreeTransformer()
    tree = parse_rule("""toplevel Root;
    A and B C;
    A or D E;
    """, "disruption_tree")

    with pytest.raises(VisitError) as excinfo:
        transformer.transform(tree)
    assert "Intermediate node 'A' is already defined" in str(
        excinfo.value.orig_exc)


def test_node_can_be_both_basic_and_child(parse_rule):
    """Test that a node can be both a basic node and appear as a child in a gate."""
    transformer = DisruptionTreeTransformer()
    tree = parse_rule("""toplevel Root;
    Root and A B;
    A prob = 0.5;
    B objects = [obj1];
    """, "disruption_tree")

    result = transformer.transform(tree)

    # Check both structure and properties
    assert list(result.edges()) == [("Root", "A"), ("Root", "B")]
    assert result.nodes["A"]["data"].probability == Fraction("0.5")
    assert result.nodes["B"]["data"].objects == ["obj1"]


def test_node_can_be_both_basic_and_intermediate(parse_rule):
    """Test that a node can be both a basic node and an intermediate node."""
    transformer = DisruptionTreeTransformer()
    tree = parse_rule("""toplevel A;
    A prob = 0.5;
    A and B C;
    B objects = [obj1];
    C;
    """, "disruption_tree")

    result = transformer.transform(tree)

    # Check structure and properties are preserved
    assert list(result.edges()) == [("A", "B"), ("A", "C")]
    assert result.nodes["A"]["data"].probability == Fraction("0.5")
    assert result.nodes["A"]["data"].gate_type == "and"
    assert result.nodes["B"]["data"].objects == ["obj1"]


def test_complex_disruption_tree(parse_rule):
    """Test transforming a complex disruption tree with multiple nodes and attributes."""
    transformer = DisruptionTreeTransformer()
    tree = parse_rule("""toplevel Root;
    Root and A B C;
    B and D E;
    C or F G;
    A prob = 0.5 objects = [obj1];
    D objects = [obj2, obj3];
    E prob = 0.6 cond = (x && y) objects = [obj2];
    F prob = 0.4;
    G objects = [obj4];
    """, "disruption_tree")

    result = transformer.transform(tree)

    # Check structure
    assert list(result.edges()) == [
        ("Root", "A"),
        ("Root", "B"),
        ("Root", "C"),
        ("B", "D"),
        ("B", "E"),
        ("C", "F"),
        ("C", "G")
    ]

    # Check gate types
    assert result.nodes["Root"]["data"].gate_type == "and"
    assert result.nodes["B"]["data"].gate_type == "and"
    assert result.nodes["C"]["data"].gate_type == "or"
    for node in ["A", "D", "E", "F", "G"]:
        assert result.nodes[node]["data"].gate_type is None

    # Check node attributes
    assert result.nodes["A"]["data"].probability == Fraction("0.5")
    assert result.nodes["A"]["data"].objects == ["obj1"]

    assert result.nodes["B"]["data"].probability is None

    assert result.nodes["C"]["data"].probability is None

    assert result.nodes["D"]["data"].objects == ["obj2", "obj3"]
    assert result.nodes["D"]["data"].probability is None

    assert result.nodes["E"]["data"].probability == Fraction("0.6")
    assert result.nodes["E"]["data"].object_properties == {"x", "y"}
    assert result.nodes["E"]["data"].objects == ["obj2"]

    assert result.nodes["F"]["data"].probability == Fraction("0.4")

    assert result.nodes["G"]["data"].objects == ["obj4"]


def test_complex_disruption_tree_basic_nodes_first(parse_rule):
    """Test transforming a complex disruption tree with nodes defined before relationships."""
    transformer = DisruptionTreeTransformer()
    tree = parse_rule("""toplevel Root;
    A prob = 0.5 objects = [obj1];
    D objects = [obj2, obj3];
    E prob = 0.6 cond = (x && y) objects = [obj2];
    F prob = 0.4;
    G objects = [obj4];
    B and D E;
    C or F G;
    Root and A B C;
    """, "disruption_tree")

    result = transformer.transform(tree)

    # Check structure
    assert list(result.edges()) == [
        ("Root", "A"),
        ("Root", "B"),
        ("Root", "C"),
        ("B", "D"),
        ("B", "E"),
        ("C", "F"),
        ("C", "G")
    ]

    # Check gate types
    assert result.nodes["Root"]["data"].gate_type == "and"
    assert result.nodes["B"]["data"].gate_type == "and"
    assert result.nodes["C"]["data"].gate_type == "or"
    for node in ["A", "D", "E", "F", "G"]:
        assert result.nodes[node]["data"].gate_type is None

    # Check node attributes
    assert result.nodes["A"]["data"].probability == Fraction("0.5")
    assert result.nodes["A"]["data"].objects == ["obj1"]

    assert result.nodes["B"]["data"].probability is None

    assert result.nodes["C"]["data"].probability is None

    assert result.nodes["D"]["data"].objects == ["obj2", "obj3"]
    assert result.nodes["D"]["data"].probability is None

    assert result.nodes["E"]["data"].probability == Fraction("0.6")
    assert result.nodes["E"]["data"].object_properties == {"x", "y"}
    assert result.nodes["E"]["data"].objects == ["obj2"]

    assert result.nodes["F"]["data"].probability == Fraction("0.4")

    assert result.nodes["G"]["data"].objects == ["obj4"]


def test_attribute_combinations(parse_rule):
    """Test all valid attribute combinations and orderings."""
    test_cases = [
        # prob + objects
        """toplevel Root;
        Root prob = 0.5 objects = [obj1];""",
        """toplevel Root;
        Root objects = [obj1] prob = 0.5;""",

        # prob + condition
        """toplevel Root;
        Root prob = 0.5 cond = (x);""",
        """toplevel Root;
        Root cond = (x) prob = 0.5;""",

        # objects + condition
        """toplevel Root;
        Root objects = [obj1] cond = (x);""",
        """toplevel Root;
        Root cond = (x) objects = [obj1];"""
    ]

    for case in test_cases:
        tree = parse_rule(case, "disruption_tree")
        result = DisruptionTreeTransformer().transform(tree)
        node = result.nodes["Root"]["data"]

        if "prob = 0.5" in case:
            assert node.probability == Fraction("0.5")
        else:
            assert node.probability is None

        if "objects = [obj1]" in case:
            assert node.objects == ["obj1"]
        else:
            assert node.objects is None

        if "cond = (x)" in case:
            assert node.object_properties == {"x"}
        else:
            assert node.object_properties == set()
        assert node.gate_type is None


def test_complex_boolean_formula(parse_rule):
    """Test transforming a disruption tree node with a complex boolean formula."""
    transformer = DisruptionTreeTransformer()
    tree = parse_rule("""toplevel Root;
    Root cond = ((!a && b) || (c => d) || (x == y) || (p != q));
    """, "disruption_tree")

    result = transformer.transform(tree)
    node = result.nodes["Root"]["data"]
    assert node.object_properties == {"a", "b", "c", "d", "x", "y", "p", "q"}
    assert node.probability is None
    assert node.objects is None
    assert node.gate_type is None


def test_cyclic_graph_raises_error(parse_rule):
    """Test that a cyclic graph raises NotAcyclicError."""
    transformer = DisruptionTreeTransformer()
    tree = parse_rule("""toplevel A;
    A and B C;
    B and C D;
    C and A E;
    D;
    E;
    """, "disruption_tree")

    with pytest.raises(VisitError) as excinfo:
        transformer.transform(tree)
    assert "Graph is not acyclic" in str(excinfo.value.orig_exc)


def test_disconnected_graph_raises_error(parse_rule):
    """Test that a disconnected graph raises NotConnectedError."""
    transformer = DisruptionTreeTransformer()
    tree = parse_rule("""toplevel A;
    A and B C;
    D and E F;  // Disconnected subgraph
    B;
    C;
    E;
    F;
    """, "disruption_tree")

    with pytest.raises(VisitError) as excinfo:
        transformer.transform(tree)
    assert "Graph is not connected" in str(excinfo.value.orig_exc)


def test_multiple_roots_raises_error(parse_rule):
    """Test that multiple root nodes raise NotExactlyOneRootError."""
    transformer = DisruptionTreeTransformer()
    # Both A and D have no parents
    tree = parse_rule("""toplevel A;
    A and B C;
    D and B C;
    """, "disruption_tree")

    with pytest.raises(VisitError) as excinfo:
        transformer.transform(tree)
    assert "Graph has more than one root" in str(excinfo.value.orig_exc)
