import pytest
from lark.exceptions import VisitError

from odf.transformers.object_graph import ObjectGraphTransformer


def test_basic_object_graph(parse_rule):
    """Test transforming a basic object graph with a single node."""
    transformer = ObjectGraphTransformer()
    tree = parse_rule("""toplevel A;
    A properties = [prop1];""", "object_graph_tree")

    result = transformer.transform(tree)
    node = result.nodes["A"]["data"]
    assert node.name == "A"
    assert node.properties == ["prop1"]


def test_object_graph_with_intermediate_node(parse_rule):
    """Test transforming an object graph with has relationships."""
    transformer = ObjectGraphTransformer()
    tree = parse_rule("""toplevel Root;
    Root has A B;
    A properties = [prop1];
    B;
    """, "object_graph_tree")

    result = transformer.transform(tree)

    # Check nodes exist
    assert "Root" in result.nodes
    assert "A" in result.nodes
    assert "B" in result.nodes

    # Check edges (has relationships)
    assert list(result.edges()) == [("Root", "A"), ("Root", "B")]

    # Check node properties
    assert result.nodes["A"]["data"].properties == ["prop1"]
    assert result.nodes["B"]["data"].properties is None


def test_duplicate_basic_object_definition_raises_error(parse_rule):
    """Test that defining a basic object multiple times raises an error."""
    transformer = ObjectGraphTransformer()
    tree = parse_rule("""toplevel A;
    A;
    A properties = [prop1, prop2];
    """, "object_graph_tree")

    with pytest.raises(VisitError) as excinfo:
        transformer.transform(tree)
    assert "Basic object 'A' is already defined" in str(excinfo.value.orig_exc)


def test_duplicate_intermediate_object_definition_raises_error(parse_rule):
    """Test that defining an intermediate object multiple times raises an error."""
    transformer = ObjectGraphTransformer()
    tree = parse_rule("""toplevel Root;
    A has B C;
    A has D E;
    """, "object_graph_tree")

    with pytest.raises(VisitError) as excinfo:
        transformer.transform(tree)
    assert "Intermediate object 'A' is already defined" in str(
        excinfo.value.orig_exc)


def test_object_can_be_both_basic_and_child(parse_rule):
    """Test that an object can be both a basic object and appear as a child in relationships."""
    transformer = ObjectGraphTransformer()
    tree = parse_rule("""toplevel Root;
    Root has A B;
    A properties = [prop1];
    B properties = [prop2];
    """, "object_graph_tree")

    result = transformer.transform(tree)

    # Check both structure and properties
    assert list(result.edges()) == [("Root", "A"), ("Root", "B")]
    assert result.nodes["A"]["data"].properties == ["prop1"]
    assert result.nodes["B"]["data"].properties == ["prop2"]


def test_object_can_be_both_basic_and_intermediate(parse_rule):
    """Test that an object can be both a basic object and an intermediate object."""
    transformer = ObjectGraphTransformer()
    tree = parse_rule("""toplevel A;
    A has B C;
    A properties = [prop1];
    B properties = [prop2];
    C;
    """, "object_graph_tree")

    result = transformer.transform(tree)

    # Check structure
    assert list(result.edges()) == [("A", "B"), ("A", "C")]

    # Check properties
    assert result.nodes["A"]["data"].properties == ["prop1"]
    assert result.nodes["B"]["data"].properties == ["prop2"]
    assert result.nodes["C"]["data"].properties is None


def test_complex_object_graph(parse_rule):
    """Test transforming a complex object graph with multiple nodes and properties."""
    transformer = ObjectGraphTransformer()
    tree = parse_rule("""toplevel Root;
    Root has A B C;
    B has D E;
    C has F G;
    A properties = [prop1];
    D properties = [prop2, prop3];
    E properties = [prop2];
    F;
    G properties = [prop4];
    """, "object_graph_tree")

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

    # Check node properties
    assert result.nodes["A"]["data"].properties == ["prop1"]
    assert result.nodes["B"]["data"].properties is None
    assert result.nodes["C"]["data"].properties is None
    assert result.nodes["D"]["data"].properties == ["prop2", "prop3"]
    assert result.nodes["E"]["data"].properties == ["prop2"]
    assert result.nodes["F"]["data"].properties is None
    assert result.nodes["G"]["data"].properties == ["prop4"]


def test_complex_object_graph_basic_nodes_first(parse_rule):
    """Test transforming a complex object graph with nodes defined before relationships."""
    transformer = ObjectGraphTransformer()
    tree = parse_rule("""toplevel Root;
    A properties = [prop1];
    D properties = [prop2, prop3];
    E properties = [prop2];
    F;
    G properties = [prop4];
    B has D E;
    C has F G;
    Root has A B C;
    """, "object_graph_tree")

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

    # Check node properties
    assert result.nodes["A"]["data"].properties == ["prop1"]
    assert result.nodes["B"]["data"].properties is None
    assert result.nodes["C"]["data"].properties is None
    assert result.nodes["D"]["data"].properties == ["prop2", "prop3"]
    assert result.nodes["E"]["data"].properties == ["prop2"]
    assert result.nodes["F"]["data"].properties is None
    assert result.nodes["G"]["data"].properties == ["prop4"]


def test_cyclic_graph_raises_error(parse_rule):
    """Test that a cyclic graph raises NotAcyclicError."""
    transformer = ObjectGraphTransformer()
    tree = parse_rule("""toplevel A;
    A has B C;
    B has C D;
    C has A E;
    D;
    E;
    """, "object_graph_tree")

    with pytest.raises(VisitError) as excinfo:
        transformer.transform(tree)
    assert "Graph is not acyclic" in str(excinfo.value.orig_exc)


def test_disconnected_graph_raises_error(parse_rule):
    """Test that a disconnected graph raises NotConnectedError."""
    transformer = ObjectGraphTransformer()
    tree = parse_rule("""toplevel A;
    A has B C;
    D has E F;  // Disconnected subgraph
    """, "object_graph_tree")

    with pytest.raises(VisitError) as excinfo:
        transformer.transform(tree)
    assert "Graph is not connected" in str(excinfo.value.orig_exc)


def test_multiple_roots_raises_error(parse_rule):
    """Test that multiple root nodes raise NotExactlyOneRootError."""
    transformer = ObjectGraphTransformer()
    # Both A and D have no parents
    tree = parse_rule("""toplevel A;
    A has B C;
    D has B C;
    """, "object_graph_tree")

    with pytest.raises(VisitError) as excinfo:
        transformer.transform(tree)
    assert "Graph has more than one root" in str(excinfo.value.orig_exc)
