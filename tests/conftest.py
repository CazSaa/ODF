"""
Pytest fixtures for parser tests.
"""
from pathlib import Path

import pytest
from lark import Lark

from odf.__main__ import validate_models
from odf.checker.layer1.check_layer1 import layer1_check, \
    layer1_compute_all
from odf.checker.layer1.layer1_bdd import Layer1BDDInterpreter
from odf.checker.layer2.check_layer2 import check_layer2_query
from odf.transformers.configuration import parse_configuration
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
def attack_tree_str1():
    """Create an attack tree with basic and non-basic nodes."""
    return """
    toplevel RootA;
    RootA and BasicAttack ComplexAttack;
    BasicAttack prob = 0.5;
    ComplexAttack and SubAttack1 SubAttack2;
    ComplexAttack cond = (obj_prop1 && obj_prop2) objects=[Object1];
    SubAttack1 prob = 0.3;
    SubAttack2 prob = 0.4;"""


@pytest.fixture
def fault_tree_str1():
    """Create a fault tree with basic and complex nodes."""
    return """
    toplevel RootF;
    RootF and BasicFault ComplexFault;
    BasicFault prob = 0.3;
    ComplexFault and SubFault1 SubFault2;
    ComplexFault cond = (obj_prop4 && obj_prop5) objects=[Object2];
    SubFault1 prob = 0.2;
    SubFault2 prob = 0.1 cond = (obj_prop6) objects=[Object2];"""


@pytest.fixture
def object_graph_str1():
    """Create an object graph with properties."""
    return """
    RootO has Object1 Object2;
    Object1 properties = [obj_prop1, obj_prop2];
    Object2 properties = [obj_prop3, obj_prop4, obj_prop5, obj_prop6];"""


@pytest.fixture
def attack_tree1(attack_tree_str1, parse_rule):
    """Create an attack tree with basic and non-basic nodes."""
    tree = parse_rule(attack_tree_str1, "disruption_tree")
    return DisruptionTreeTransformer().transform(tree)


@pytest.fixture
def fault_tree1(fault_tree_str1, parse_rule):
    """Create a fault tree with a basic node."""
    tree = parse_rule(fault_tree_str1, "disruption_tree")
    return DisruptionTreeTransformer().transform(tree)


@pytest.fixture
def object_graph1(object_graph_str1, parse_rule):
    """Create an object graph with properties."""
    tree = parse_rule(object_graph_str1, "object_graph_tree")
    return ObjectGraphTransformer().transform(tree)


@pytest.fixture
def transform_disruption_tree_str(parse_rule):
    def _transform_disruption_tree_str(tree_str):
        tree = parse_rule(tree_str, "disruption_tree")
        return DisruptionTreeTransformer().transform(tree)

    return _transform_disruption_tree_str


@pytest.fixture
def transform_object_graph_str(parse_rule):
    def _transform_object_graph_str(graph_str):
        tree = parse_rule(graph_str, "object_graph_tree")
        return ObjectGraphTransformer().transform(tree)

    return _transform_object_graph_str


@pytest.fixture
def attack_tree_mixed_gates(transform_disruption_tree_str):
    """Create an attack tree with mixed AND/OR gates for interesting MRS patterns."""
    return transform_disruption_tree_str("""
    toplevel RootA;
    RootA or PathA PathB PathC;

    // Path A: Simple AND chain
    PathA and StepA1 StepA2;
    StepA1 and Attack1 Attack2;
    StepA2;
    Attack1;
    Attack2;

    // Path B: OR of ANDs - multiple minimal sets
    PathB or SubPathB1 SubPathB2;
    SubPathB1 and Attack3 Attack4;
    SubPathB2 and Attack5 Attack6;
    Attack3;
    Attack4;
    Attack5;
    Attack6;

    // Path C: Complex mix of gates with conditions
    PathC and SubPathC1 SubPathC2 SubPathC3;
    SubPathC1 or Attack7 Attack8;
    SubPathC2 and Attack9 SubPathC2_1;
    SubPathC2_1 or Attack10 Attack11;
    SubPathC3;
    SubPathC2_1;
    Attack7 cond = (obj_prop1) objects=[Object1];
    Attack8 cond = (obj_prop2) objects=[Object1];
    Attack9;
    Attack10;
    Attack11;
    """)


@pytest.fixture
def attack_tree_paper_example(transform_disruption_tree_str):
    """Create the attack tree from the paper example."""
    return transform_disruption_tree_str("""
    toplevel Attacker_breaks_in_house;
    Attacker_breaks_in_house or EDLU FD;
    FD or PL DD;
    
    Attacker_breaks_in_house objects=[House,Inhabitant];
    EDLU objects=[Door] prob=0.17;
    FD objects=[Door];
    PL objects=[Lock] cond=(LP) prob=0.10;
    DD objects=[Door] cond=(DF) prob=0.13;
    """)


@pytest.fixture
def fault_tree_paper_example(transform_disruption_tree_str):
    """Create the fault tree from the paper example."""
    return transform_disruption_tree_str("""
    toplevel Fire_and_impossible_escape;
    Fire_and_impossible_escape and FBO DGB;
    DGB and DSL LGJ;
    
    Fire_and_impossible_escape objects=[House,Inhabitant] cond=(Inhab_in_House);
    FBO objects=[House,Inhabitant] cond=(!HS && IU) prob=0.21;
    DGB objects=[Door];
    DSL objects=[Door] prob=0.20;
    LGJ objects=[Lock] cond=(LJ) prob=0.70;
    """)


@pytest.fixture
def object_graph_paper_example(transform_object_graph_str):
    """Create the object graph from the paper example."""
    return transform_object_graph_str("""
    House has Door;
    Door has Lock;
    Inhabitant properties=[Inhab_in_House,IU];
    
    House properties=[HS];
    Door properties=[DF];
    Lock properties=[LP,LJ];
    """)


@pytest.fixture
def paper_example_models(attack_tree_paper_example, fault_tree_paper_example,
                         object_graph_paper_example):
    """Returns the paper example models as a list for unpacking with *."""
    return [attack_tree_paper_example, fault_tree_paper_example,
            object_graph_paper_example]


@pytest.fixture
def parse_and_get_bdd(attack_tree1, fault_tree1, object_graph1, parse_rule):
    def _parse_and_get_bdd(formula, attack_tree=attack_tree1,
                           fault_tree=fault_tree1, object_graph=object_graph1):
        tree = parse_rule(formula, "layer1_formula")
        validate_models(attack_tree, fault_tree, object_graph)
        transformer = Layer1BDDInterpreter(attack_tree, fault_tree,
                                           object_graph)
        bdd = transformer.interpret(tree)
        return transformer, bdd

    return _parse_and_get_bdd


@pytest.fixture
def do_layer1_check(attack_tree1, fault_tree1, object_graph1, parse_rule):
    def _do_layer1_check(formula, configuration, attack_tree=attack_tree1,
                         fault_tree=fault_tree1, object_graph=object_graph1):
        formula_tree = parse_rule(formula, "layer1_formula")
        config_tree = parse_rule(configuration, "configuration")
        config = parse_configuration(config_tree)
        return layer1_check(formula_tree, config, attack_tree, fault_tree,
                            object_graph)

    return _do_layer1_check


@pytest.fixture
def do_layer1_compute_all(attack_tree1, fault_tree1, object_graph1, parse_rule):
    def _do_layer1_compute_all(formula, configuration, attack_tree=attack_tree1,
                               fault_tree=fault_tree1,
                               object_graph=object_graph1):
        formula_tree = parse_rule(formula, "layer1_formula")
        config_tree = parse_rule(configuration, "configuration")
        config = parse_configuration(config_tree)
        return layer1_compute_all(formula_tree, config, attack_tree, fault_tree,
                                  object_graph)

    return _do_layer1_compute_all


@pytest.fixture
def do_check_layer2(parse_rule):
    def _do_check_layer2(formula, attack_tree, fault_tree, object_graph):
        validate_models(attack_tree, fault_tree, object_graph)
        formula_tree = parse_rule(formula, "layer2_query")
        return check_layer2_query(formula_tree, attack_tree, fault_tree,
                                  object_graph)

    return _do_check_layer2
