import pytest

from odf.models.exceptions import CrossReferenceError
from odf.models.validation import validate_disruption_tree_references, \
    validate_unique_node_names
from odf.parser.parser import parse
from odf.transformers.disruption_tree import DisruptionTreeTransformer
from odf.transformers.object_graph import ObjectGraphTransformer


def test_valid_references():
    odl_text = """
    [odg.attack_tree]
    toplevel Root;
    Root or Node1 Node2;

    Root objects=[House,Door] cond=(HS && DF);
    Node1 prob=0.17 objects=[Lock] cond=(LP);
    Node2 prob=0.13 objects=[Lock] cond=(LJ);

    [odg.fault_tree]
    toplevel FRoot;
    
    [odg.object_graph]
    toplevel House;
    House has Door;
    Door has Lock;

    House properties=[HS];
    Door properties=[DF];
    Lock properties=[LP,LJ];
    
    [formulas]
    Root;
    """

    parse_tree = parse(odl_text)
    trees = parse_tree.children
    attack_tree = DisruptionTreeTransformer().transform(trees[0])
    object_graph = ObjectGraphTransformer().transform(trees[2])

    # Should not raise any exceptions
    validate_disruption_tree_references(attack_tree, object_graph)


def test_duplicate_node_names():
    odl_text = """
    [odg.attack_tree]
    toplevel Root;
    Root or DuplicateName Node2;
    
    Root objects=[House];
    DuplicateName objects=[Door];
    Node2 objects=[Lock];

    [odg.fault_tree]
    toplevel DuplicateName;  // Same name used in attack tree
    DuplicateName;

    [odg.object_graph]
    toplevel House;
    House has Door;
    Door has Lock;
    
    [formulas]
    Root;
    """

    parse_tree = parse(odl_text)
    trees = parse_tree.children
    attack_tree = DisruptionTreeTransformer().transform(trees[0])
    fault_tree = DisruptionTreeTransformer().transform(trees[1])
    object_graph = ObjectGraphTransformer().transform(trees[2])

    with pytest.raises(CrossReferenceError) as exc_info:
        validate_unique_node_names(attack_tree, fault_tree, object_graph)
    assert "Node name 'DuplicateName' is used in multiple trees" in str(
        exc_info.value)


def test_invalid_object_reference():
    odl_text = """
    [odg.attack_tree]
    toplevel Root;
    Root objects=[NonExistentObject];

    [odg.fault_tree]
    toplevel FRoot;

    [odg.object_graph]
    toplevel House;
    House properties=[HS];
    
    [formulas]
    Root;
    """

    parse_tree = parse(odl_text)
    trees = parse_tree.children
    attack_tree = DisruptionTreeTransformer().transform(trees[0])
    object_graph = ObjectGraphTransformer().transform(trees[2])

    with pytest.raises(CrossReferenceError) as exc_info:
        validate_disruption_tree_references(attack_tree, object_graph)
    assert "Root" in str(exc_info.value)
    assert "NonExistentObject" in str(exc_info.value)


def test_property_without_object():
    odl_text = """
    [odg.attack_tree]
    toplevel Root;
    Root cond=(HS);  // No objects specified

    [odg.fault_tree]
    toplevel FRoot;

    [odg.object_graph]
    toplevel House;
    House properties=[HS];
    
    [formulas]
    Root;
    """

    parse_tree = parse(odl_text)
    trees = parse_tree.children
    attack_tree = DisruptionTreeTransformer().transform(trees[0])
    object_graph = ObjectGraphTransformer().transform(trees[2])

    with pytest.raises(CrossReferenceError) as exc_info:
        validate_disruption_tree_references(attack_tree, object_graph)
    assert "Root" in str(exc_info.value)


def test_invalid_property_reference():
    odl_text = """
    [odg.attack_tree]
    toplevel Root;
    Root objects=[House] cond=(InvalidProp);

    [odg.fault_tree]
    toplevel FRoot;

    [odg.object_graph]
    toplevel House;
    House properties=[HS];
    
    [formulas]
    Root;
    """

    parse_tree = parse(odl_text)
    trees = parse_tree.children
    attack_tree = DisruptionTreeTransformer().transform(trees[0])
    object_graph = ObjectGraphTransformer().transform(trees[2])

    with pytest.raises(CrossReferenceError) as exc_info:
        validate_disruption_tree_references(attack_tree, object_graph)
    assert "Root" in str(exc_info.value)
    assert "InvalidProp" in str(exc_info.value)


def test_property_from_wrong_object():
    odl_text = """
    [odg.attack_tree]
    toplevel Root;
    Root objects=[House] cond=(LP);  // LP is Lock's property

    [odg.fault_tree]
    toplevel FRoot;

    [odg.object_graph]
    toplevel House;
    House properties=[HS];
    Lock properties=[LP];
    
    [formulas]
    Root;
    """

    parse_tree = parse(odl_text)
    trees = parse_tree.children
    attack_tree = DisruptionTreeTransformer().transform(trees[0])
    object_graph = ObjectGraphTransformer().transform(trees[2])

    with pytest.raises(CrossReferenceError) as exc_info:
        validate_disruption_tree_references(attack_tree, object_graph)
    assert "Root" in str(exc_info.value)
    assert "LP" in str(exc_info.value)
    assert "House" in str(exc_info.value)


def test_complex_conditions():
    odl_text = """
    [odg.attack_tree]
    toplevel Root;
    Root objects=[Lock,Door] cond=((LP && !LJ) || DF);

    [odg.fault_tree]
    toplevel FRoot;

    [odg.object_graph]
    toplevel House;
    House has Door;
    Door has Lock;

    Door properties=[DF];
    Lock properties=[LP,LJ];
    
    [formulas]
    Root;
    """

    parse_tree = parse(odl_text)
    trees = parse_tree.children
    attack_tree = DisruptionTreeTransformer().transform(trees[0])
    object_graph = ObjectGraphTransformer().transform(trees[2])

    # Should not raise any exceptions
    validate_disruption_tree_references(attack_tree, object_graph)
