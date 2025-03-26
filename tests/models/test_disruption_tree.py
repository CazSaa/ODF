import pytest

from odf.models.disruption_tree import DisruptionTree, DTNode


@pytest.fixture
def basic_tree():
    """Create a basic tree where all nodes should be modules."""
    tree = DisruptionTree()

    # Create a simple tree structure:
    #     Root
    #     /  \
    #    A    B
    #   /    / \
    #  C    D   E
    nodes = {name: DTNode(name=name) for name in
             ['Root', 'A', 'B', 'C', 'D', 'E']}
    for node in nodes.values():
        tree.add_node(node.name, data=node)

    tree.add_edge('Root', 'A')
    tree.add_edge('Root', 'B')
    tree.add_edge('A', 'C')
    tree.add_edge('B', 'D')
    tree.add_edge('B', 'E')

    return tree


@pytest.fixture
def dag_with_shared_child():
    """Create a DAG where nodes have multiple parents, making some non-modules."""
    tree = DisruptionTree()

    # Create the structure from the example:
    #     Root
    #     /  \
    #    B    D
    #   / \  /
    #  C   A
    nodes = {name: DTNode(name=name) for name in ['Root', 'B', 'D', 'C', 'A']}
    for node in nodes.values():
        tree.add_node(node.name, data=node)

    tree.add_edge('Root', 'B')
    tree.add_edge('Root', 'D')
    tree.add_edge('B', 'C')
    tree.add_edge('B', 'A')
    tree.add_edge('D', 'A')

    return tree


def test_basic_tree_modules(basic_tree):
    """Test that in a basic tree, all intermediate nodes are modules."""
    assert basic_tree.is_module('Root')
    assert basic_tree.is_module('A')
    assert basic_tree.is_module('B')
    # Leaf nodes are technically modules but not interesting for our use case
    assert basic_tree.is_module('C')
    assert basic_tree.is_module('D')
    assert basic_tree.is_module('E')


def test_dag_non_modules(dag_with_shared_child):
    """Test that nodes are not modules when their descendants have other parents."""
    assert not dag_with_shared_child.is_module('D')
    assert not dag_with_shared_child.is_module('B')

    assert dag_with_shared_child.is_module('Root')

    assert dag_with_shared_child.is_module('C')
    assert dag_with_shared_child.is_module('A')


@pytest.fixture
def complex_dag():
    """Create a complex DAG with multiple shared children and cross-connections.
    
    Structure:
         Root
        /    \\
       A       B
      / \\    / \\
     C   D   E   F
          \\   /
             G
           
    Notable cases:
    - G has multiple paths to reach it (through D and F)
    - A and B are not modules because G can be reached through multiple paths
    - D and F are not modules for the same reason
    - Root, C, E, and G are modules
    """
    tree = DisruptionTree()

    nodes = {name: DTNode(name=name) for name in
             ['Root', 'A', 'B', 'C', 'D', 'E', 'F', 'G']}
    for node in nodes.values():
        tree.add_node(node.name, data=node)

    edges = [
        ('Root', 'A'), ('Root', 'B'),
        ('A', 'C'), ('A', 'D'),
        ('B', 'E'), ('B', 'F'),
        ('D', 'G'), ('F', 'G')
    ]
    for src, dst in edges:
        tree.add_edge(src, dst)

    return tree


def test_complex_dag_modules(complex_dag):
    """Test module detection in a complex DAG with multiple paths to shared nodes."""
    # Test each node's module status
    modules = {'Root', 'C', 'E', 'G'}
    non_modules = {'A', 'B', 'D', 'F'}

    for node in modules:
        assert complex_dag.is_module(node)

    for node in non_modules:
        assert not complex_dag.is_module(node)
