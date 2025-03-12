"""
Pytest fixtures for parser tests.
"""
from pathlib import Path

import pytest
from lark import Lark

from odf.checker.layer1.check_layer1 import parse_configuration, layer1_check
from odf.checker.layer1.layer1_bdd import Layer1BDDTransformer
from odf.transformers.disruption_tree import DisruptionTreeTransformer
from odf.transformers.object_graph import ObjectGraphTransformer


@pytest.fixture(scope="session")
def grammar_path():
    """Path to the grammar file."""
    return Path(__file__).parent.parent / "odf" / "parser" / "grammar.lark"


@pytest.fixture(scope="session")
def grammar_text(grammar_path):
    """Raw grammar text."""
    return grammar_path.read_text()


@pytest.fixture(scope="session")
def parser(grammar_text):
    """Lark parser instance."""
    return Lark(grammar_text, parser="earley", propagate_positions=True,
                strict=True)


@pytest.fixture(scope="session")
def make_parser(grammar_text):
    """Create a parser with a specific start rule."""

    def _make_parser(start):
        return Lark(grammar_text, parser="earley", propagate_positions=True,
                    start=start, strict=True)

    return _make_parser


@pytest.fixture
def parse(parser):
    """Helper fixture to parse input text using the default start rule."""

    def _parse(text):
        return parser.parse(text)

    return _parse


@pytest.fixture
def parse_rule(make_parser):
    """Helper fixture to parse input text using a specific start rule."""

    def _parse_rule(text, start):
        parser = make_parser(start)
        return parser.parse(text)

    return _parse_rule


@pytest.fixture
def attack_tree_str():
    """Create an attack tree with basic and non-basic nodes."""
    return """
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
    return """
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
    return """
    toplevel Root;
    Root has Object1 Object2;
    Object1 properties = [obj_prop1, obj_prop2];
    Object2 properties = [obj_prop3];"""


@pytest.fixture
def transform_disruption_tree_str(parse_rule):
    def _transform_disruption_tree_str(tree_str):
        tree = parse_rule(tree_str, "disruption_tree")
        return DisruptionTreeTransformer().transform(tree)

    return _transform_disruption_tree_str


@pytest.fixture
def attack_tree(attack_tree_str, parse_rule):
    """Create an attack tree with basic and non-basic nodes."""
    tree = parse_rule(attack_tree_str, "disruption_tree")
    return DisruptionTreeTransformer().transform(tree)


@pytest.fixture
def fault_tree(fault_tree_str, parse_rule):
    """Create a fault tree with a basic node."""
    tree = parse_rule(fault_tree_str, "disruption_tree")
    return DisruptionTreeTransformer().transform(tree)


@pytest.fixture
def object_graph(object_graph_str, parse_rule):
    """Create an object graph with properties."""
    tree = parse_rule(object_graph_str, "object_graph_tree")
    return ObjectGraphTransformer().transform(tree)


@pytest.fixture
def parse_and_get_bdd(attack_tree, fault_tree, object_graph, parse_rule):
    def _parse_and_get_bdd(formula, attack_tree_=attack_tree,
                           fault_tree_=fault_tree, object_graph_=object_graph):
        tree = parse_rule(formula, "layer1_formula")
        transformer = Layer1BDDTransformer(attack_tree_, fault_tree_,
                                           object_graph_)
        bdd = transformer.transform(tree)
        return transformer, bdd

    return _parse_and_get_bdd


@pytest.fixture
def do_layer1_check(attack_tree, fault_tree, object_graph, parse_rule):
    def _do_layer1_check(formula, configuration, attack_tree_=attack_tree,
                         fault_tree_=fault_tree, object_graph_=object_graph):
        formula_tree = parse_rule(formula, "layer1_formula")
        config_tree = parse_rule(configuration, "configuration")
        config = parse_configuration(config_tree)
        return layer1_check(formula_tree, config, attack_tree_, fault_tree_,
                            object_graph_)

    return _do_layer1_check
