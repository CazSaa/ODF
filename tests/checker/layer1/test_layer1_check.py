import pytest

from odf.__main__ import extract_parse_trees
from odf.checker.layer1.check_layer1 import layer1_check, parse_configuration
from odf.parser.parser import parse
from odf.transformers.disruption_tree import DisruptionTreeTransformer
from odf.transformers.object_graph import ObjectGraphTransformer


def check_formula_with_config(formula_str: str, config_str: str,
                              attack_tree_str: str, fault_tree_str: str,
                              object_graph_str: str) -> bool:
    """Helper function to check a layer1 formula with a configuration."""
    full_input = f"""
{attack_tree_str}

{fault_tree_str}

{object_graph_str}

[formulas]
{config_str} {formula_str};
"""
    parse_tree = parse(full_input)
    [attack_parse_tree, fault_tree_parse_tree,
     object_parse_tree, formulas_parse_tree] = extract_parse_trees(parse_tree)

    attack_tree = DisruptionTreeTransformer().transform(attack_parse_tree)
    fault_tree = DisruptionTreeTransformer().transform(fault_tree_parse_tree)
    object_graph = ObjectGraphTransformer().transform(object_parse_tree)

    formula = formulas_parse_tree.children[0]
    assert formula.data == "layer1_query"
    assert formula.children[0].data == "check"
    config = parse_configuration(formula.children[0].children[0])
    formula_tree = formula.children[0].children[1]

    return layer1_check(formula_tree, config, attack_tree, fault_tree,
                        object_graph)


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


def test_basic_check(attack_tree_str, fault_tree_str, object_graph_str):
    """Test checking a basic formula with complete configuration."""
    # Test single node satisfaction
    assert check_formula_with_config(
        "BasicAttack",
        "{BasicAttack:1}",
        attack_tree_str, fault_tree_str, object_graph_str
    )

    assert not check_formula_with_config(
        "BasicAttack",
        "{BasicAttack:0}",
        attack_tree_str, fault_tree_str, object_graph_str
    )

    # Test negation
    assert check_formula_with_config(
        "!BasicAttack",
        "{BasicAttack:0}",
        attack_tree_str, fault_tree_str, object_graph_str
    )


def test_complex_formula_check(attack_tree_str, fault_tree_str,
                               object_graph_str):
    """Test checking complex formulas with gates and conditions."""
    # Test ComplexAttack which requires its basic events and conditions
    assert check_formula_with_config(
        "ComplexAttack",
        "{SubAttack1:1, SubAttack2:1, obj_prop1:1, obj_prop2:1}",
        attack_tree_str, fault_tree_str, object_graph_str
    )

    # Test complex formula with multiple operators
    assert check_formula_with_config(
        "(BasicAttack || BasicFault) && ComplexAttack",
        "{BasicAttack:1, BasicFault:0, SubAttack1:1, SubAttack2:1, obj_prop1:1, obj_prop2:1}",
        attack_tree_str, fault_tree_str, object_graph_str
    )


def test_missing_variables(attack_tree_str, fault_tree_str, object_graph_str):
    """Test error handling when configuration is missing required variables."""
    with pytest.raises(ValueError, match="Missing variables:"):
        check_formula_with_config(
            "ComplexAttack",
            "{SubAttack1:1}",  # Missing SubAttack2 and object properties
            attack_tree_str, fault_tree_str, object_graph_str
        )


def test_extra_variables(attack_tree_str, fault_tree_str, object_graph_str,
                         capsys):
    """Test handling of extra variables in configuration."""
    result = check_formula_with_config(
        "BasicAttack",
        "{BasicAttack:1, NonexistentVar:1}",
        attack_tree_str, fault_tree_str, object_graph_str
    )

    # Check that warning was printed
    captured = capsys.readouterr()
    assert "You specified variables that do not exist" in captured.out
    assert "NonexistentVar" in captured.out
    # Check that the formula was still evaluated correctly
    assert result == True


def test_complex_conditions_check(attack_tree_str, fault_tree_str,
                                  object_graph_str):
    """Test checking formulas with complex conditions."""
    # Test ComplexFault which has nested conditions
    assert check_formula_with_config(
        "ComplexFault",
        "{SubFault1:1, SubFault2:1, obj_prop4:1, obj_prop5:1, obj_prop6:1}",
        attack_tree_str, fault_tree_str, object_graph_str
    )

    # Test when one condition is false
    assert not check_formula_with_config(
        "ComplexFault",
        "{SubFault1:1, SubFault2:1, obj_prop4:0, obj_prop5:1, obj_prop6:1}",
        attack_tree_str, fault_tree_str, object_graph_str
    )
    assert not check_formula_with_config(
        "ComplexFault",
        "{SubFault1:1, SubFault2:1, obj_prop4:1, obj_prop5:0, obj_prop6:1}",
        attack_tree_str, fault_tree_str, object_graph_str
    )
    assert not check_formula_with_config(
        "ComplexFault",
        "{SubFault1:1, SubFault2:1, obj_prop4:1, obj_prop5:1, obj_prop6:0}",
        attack_tree_str, fault_tree_str, object_graph_str
    )


def test_boolean_operators(attack_tree_str, fault_tree_str, object_graph_str):
    """Test various boolean operators in formulas."""
    # Test AND
    assert check_formula_with_config(
        "BasicAttack && BasicFault",
        "{BasicAttack:1, BasicFault:1}",
        attack_tree_str, fault_tree_str, object_graph_str
    )

    # Test OR
    assert check_formula_with_config(
        "BasicAttack || BasicFault",
        "{BasicAttack:1, BasicFault:0}",
        attack_tree_str, fault_tree_str, object_graph_str
    )

    # Test IMPLIES
    assert check_formula_with_config(
        "BasicAttack => BasicFault",
        "{BasicAttack:0, BasicFault:1}",
        attack_tree_str, fault_tree_str, object_graph_str
    )
    assert not check_formula_with_config(
        "BasicAttack => BasicFault",
        "{BasicAttack:1, BasicFault:0}",
        attack_tree_str, fault_tree_str, object_graph_str
    )

    # Test EQUIV
    assert check_formula_with_config(
        "BasicAttack == BasicFault",
        "{BasicAttack:1, BasicFault:1}",
        attack_tree_str, fault_tree_str, object_graph_str
    )

    # Test NOT EQUIV
    assert check_formula_with_config(
        "BasicAttack != BasicFault",
        "{BasicAttack:1, BasicFault:0}",
        attack_tree_str, fault_tree_str, object_graph_str
    )


def test_object_property_check(attack_tree_str, fault_tree_str,
                               object_graph_str):
    """Test checking formulas with object properties."""
    # Test direct object property
    assert check_formula_with_config(
        "obj_prop1",
        "{obj_prop1:1}",
        attack_tree_str, fault_tree_str, object_graph_str
    )

    # Test object property in condition
    assert not check_formula_with_config(
        "SubFault2",
        "{SubFault2:1, obj_prop6:0}",
        attack_tree_str, fault_tree_str, object_graph_str
    )
    assert not check_formula_with_config(
        "SubFault2",
        "{SubFault2:0, obj_prop6:1}",
        attack_tree_str, fault_tree_str, object_graph_str
    )
    assert check_formula_with_config(
        "SubFault2",
        "{SubFault2:1, obj_prop6:1}",
        attack_tree_str, fault_tree_str, object_graph_str
    )
