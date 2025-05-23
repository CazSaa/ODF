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
from odf.models.object_graph import ObjectGraph
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
    return Lark(grammar_text, maybe_placeholders=False, strict=True)


@pytest.fixture(scope="session")
def make_parser(grammar_text):
    """Create a parser with a specific start rule."""

    def _make_parser(start):
        return Lark(grammar_text, start=start, maybe_placeholders=False,
                    strict=True)

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
def attack_tree1(attack_tree_str1, parse_rule, object_graph1):
    """Create an attack tree with basic and non-basic nodes."""
    tree = parse_rule(attack_tree_str1, "disruption_tree")
    return DisruptionTreeTransformer(object_graph1).transform(tree)


@pytest.fixture
def fault_tree1(fault_tree_str1, parse_rule, object_graph1):
    """Create a fault tree with a basic node."""
    tree = parse_rule(fault_tree_str1, "disruption_tree")
    return DisruptionTreeTransformer(object_graph1).transform(tree)


@pytest.fixture
def object_graph1(object_graph_str1, parse_rule):
    """Create an object graph with properties."""
    tree = parse_rule(object_graph_str1, "object_graph_tree")
    return ObjectGraphTransformer().transform(tree)


@pytest.fixture
def transform_disruption_tree_str(parse_rule):
    def _transform_disruption_tree_str(tree_str, object_graph=None):
        tree = parse_rule(tree_str, "disruption_tree")
        return DisruptionTreeTransformer(
            object_graph or ObjectGraph()).transform(tree)

    return _transform_disruption_tree_str


@pytest.fixture
def transform_object_graph_str(parse_rule):
    def _transform_object_graph_str(graph_str):
        tree = parse_rule(graph_str, "object_graph_tree")
        return ObjectGraphTransformer().transform(tree)

    return _transform_object_graph_str


@pytest.fixture
def attack_tree_mixed_gates(transform_disruption_tree_str, object_graph1):
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
    """, object_graph1)


@pytest.fixture
def attack_tree_paper_example(transform_disruption_tree_str,
                              object_graph_paper_example):
    """Create the attack tree from the paper example with impact values."""
    return transform_disruption_tree_str("""
    toplevel Attacker_breaks_in_house;
    Attacker_breaks_in_house or EDLU FD;
    FD or PL DD;
    
    Attacker_breaks_in_house objects=[House,Inhabitant] impact=3.47;
    EDLU objects=[Door] prob=0.17 impact=1.27;
    FD objects=[Door] impact=2.57;
    PL objects=[Lock] cond=(LP) prob=0.10 impact=2.51;
    DD objects=[Door] cond=(DF) prob=0.13 impact=1.81;
    """, object_graph_paper_example)


@pytest.fixture
def fault_tree_paper_example(transform_disruption_tree_str,
                             object_graph_paper_example):
    """Create the fault tree from the paper example with impact values."""
    return transform_disruption_tree_str("""
    toplevel Fire_and_impossible_escape;
    Fire_and_impossible_escape and FBO DGB;
    DGB and DSL LGJ;
    
    Fire_and_impossible_escape objects=[House,Inhabitant] cond=(Inhab_in_House) impact=3.53;
    FBO objects=[House,Inhabitant] cond=(!HS && IU) prob=0.21 impact=1.09;
    DGB objects=[Door] impact=1.67;
    DSL objects=[Door] prob=0.20 impact=1.31;
    LGJ objects=[Lock] cond=(LJ) prob=0.70 impact=0.83;
    """, object_graph_paper_example)


@pytest.fixture
def fault_tree_paper_example_with_unsat_node(transform_disruption_tree_str,
                                             object_graph_paper_example):
    return transform_disruption_tree_str("""
    toplevel Fire_and_impossible_escape;
    Fire_and_impossible_escape and FBO DGB;
    DGB and DSL LGJ;
    
    Fire_and_impossible_escape objects=[House,Inhabitant] cond=(Inhab_in_House) impact=3.31;
    FBO objects=[House,Inhabitant] cond=(!HS && IU) prob=0.21 impact=1.09;
    DGB objects=[Door] impact=1.67;
    DSL objects=[Door,House] prob=0.20 impact=1.31 cond=(HS);
    LGJ objects=[Lock] cond=(LJ) prob=0.70 impact=0.83;
    """, object_graph_paper_example)


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
def object_graph_paper_example_with_extra(transform_object_graph_str):
    """Create the object graph from the paper example."""
    return transform_object_graph_str("""
    House has Door;
    Door has Lock;
    Inhabitant properties=[Inhab_in_House,IU];

    House properties=[HS];
    Door properties=[DF];
    Lock properties=[LP,LJ];
    ExtraObject properties=[ExtraProp];
    """)


@pytest.fixture
def paper_example_models(attack_tree_paper_example, fault_tree_paper_example,
                         object_graph_paper_example):
    """Returns the paper example models as a list for unpacking with *."""
    return [attack_tree_paper_example, fault_tree_paper_example,
            object_graph_paper_example]


@pytest.fixture
def attack_tree_paper_example_disconnected(transform_disruption_tree_str,
                                           object_graph_paper_example_disconnected):
    return transform_disruption_tree_str("""
    toplevel Attacker_breaks_in_house;
    Attacker_breaks_in_house or EDLU FD;
    FD or PL DD;

    Attacker_breaks_in_house objects=[House,Inhabitant] impact=3.47;
    EDLU objects=[Door] prob=0.17 impact=1.27;
    FD objects=[Door] impact=2.57;
    PL objects=[Lock] cond=(LP) prob=0.10 impact=2.51;
    DD objects=[Door] cond=(DF) prob=0.13 impact=1.81;
    """, object_graph_paper_example_disconnected)


@pytest.fixture
def fault_tree_paper_example_disconnected(transform_disruption_tree_str,
                                          object_graph_paper_example_disconnected):
    return transform_disruption_tree_str("""
    toplevel Fire_and_impossible_escape;
    Fire_and_impossible_escape and FBO DGB;
    DGB and DSL LGJ;

    Fire_and_impossible_escape objects=[House,Inhabitant] cond=(Inhab_in_House) impact=3.53;
    FBO objects=[House,Inhabitant] cond=(!HS && IU) prob=0.21 impact=1.09;
    DGB objects=[Door] impact=1.67;
    DSL objects=[Door] prob=0.20 impact=1.31;
    LGJ objects=[Lock] cond=(LJ) prob=0.70 impact=0.83;
    """, object_graph_paper_example_disconnected)


@pytest.fixture
def object_graph_paper_example_disconnected(transform_object_graph_str):
    """Create the object graph from the paper example but disconnected."""
    return transform_object_graph_str("""
    Inhabitant properties=[Inhab_in_House,IU];
    House properties=[HS];
    Door properties=[DF];
    Lock properties=[LP,LJ];
    """)


@pytest.fixture
def paper_example_disconnected(attack_tree_paper_example_disconnected,
                               fault_tree_paper_example_disconnected,
                               object_graph_paper_example_disconnected):
    return [attack_tree_paper_example_disconnected,
            fault_tree_paper_example_disconnected,
            object_graph_paper_example_disconnected]


@pytest.fixture
def attack_tree_complex_str():
    """Attack tree (can be minimal if not directly used by non-ops)."""
    return """
    toplevel ComplexRootA;
    ComplexRootA prob=0.23 impact=1.27 objects=[Obj6]; // Dummy fault
    """


@pytest.fixture
def fault_tree_complex_str():
    """Fault tree containing variables for the complex MTBDD test."""
    return """
    toplevel ComplexRootA;
    ComplexRootA or NON_OP1 NON_OP2 NON_OP3 NON_OP4 NON_OP5; // Include all non-ops
    NON_OP1 prob=0.07 impact=1.31 objects=[Obj1];
    NON_OP2 prob=0.11 impact=1.37 objects=[Obj2];
    NON_OP3 prob=0.13 impact=1.39 objects=[Obj3];
    NON_OP4 prob=0.17 impact=1.49 objects=[Obj4];
    NON_OP5 prob=0.19 impact=1.51 objects=[Obj5];
    """


@pytest.fixture
def object_graph_complex_str():
    """Object graph containing objects and OP variables for the complex MTBDD test."""
    # Define objects and properties OP1..OP8
    return """
    Obj1 properties=[OP1, OP2];
    Obj2 properties=[OP3, OP4];
    Obj3 properties=[OP5, OP6];
    Obj4 properties=[OP7, OP8];
    Obj5; // Object for NON_OP5 if needed
    Obj6; // Object for ComplexRootF if needed
    """


@pytest.fixture
def attack_tree_complex(attack_tree_complex_str, transform_disruption_tree_str,
                        object_graph_complex):
    """Parsed attack tree for the complex MTBDD test."""
    return transform_disruption_tree_str(attack_tree_complex_str,
                                         object_graph_complex)


@pytest.fixture
def fault_tree_complex(fault_tree_complex_str, transform_disruption_tree_str,
                       object_graph_complex):
    """Parsed fault tree for the complex MTBDD test."""
    return transform_disruption_tree_str(fault_tree_complex_str,
                                         object_graph_complex)


@pytest.fixture
def object_graph_complex(object_graph_complex_str, transform_object_graph_str):
    """Parsed object graph for the complex MTBDD test."""
    return transform_object_graph_str(object_graph_complex_str)


@pytest.fixture
def complex_test_models(attack_tree_complex, fault_tree_complex,
                        object_graph_complex):
    """Returns the complex test models as a list for unpacking."""
    return [attack_tree_complex, fault_tree_complex, object_graph_complex]


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


import re


def _extract_section(file_content: str, section_name: str) -> str:
    """Extract a section from the case study file content."""
    # Find start of section using regex to match section header at start of line
    pattern = f"^\\[{re.escape(section_name)}\\]"
    match = re.search(pattern, file_content, re.MULTILINE)
    if not match:
        raise ValueError(f"Section {section_name} not found")

    start_idx = match.start()

    # Find start of next section using regex
    next_section = re.search(r"^\[", file_content[start_idx + 1:], re.MULTILINE)

    if next_section:
        # Found another section, extract up to it
        section_content = file_content[start_idx + len(
            match.group()):start_idx + 1 + next_section.start()]
    else:
        # No next section, use rest of file
        section_content = file_content[start_idx + len(match.group()):]

    return section_content.strip()


@pytest.fixture(scope="session")
def case_study_content():
    """Read the case study file content."""
    case_study_path = Path(__file__).parent.parent / "docs" / "case-study.odf"
    return case_study_path.read_text()


@pytest.fixture(scope="session")
def alternative_case_study_content():
    """Read the alternative case study file content."""
    case_study_path = Path(
        __file__).parent.parent / "docs" / "case-study-adapt.odf"
    return case_study_path.read_text()


@pytest.fixture
def case_study_attack_tree_str(case_study_content):
    """Attack tree from the case study."""
    return _extract_section(case_study_content, "dog.attack_tree")


@pytest.fixture
def alternative_case_study_attack_tree_str(alternative_case_study_content):
    """Alternative attack tree from the case study with adapted Waterhammer attack."""
    return _extract_section(alternative_case_study_content, "dog.attack_tree")


@pytest.fixture
def case_study_fault_tree_str(case_study_content):
    """Fault tree from the case study."""
    return _extract_section(case_study_content, "dog.fault_tree")


@pytest.fixture
def alternative_case_study_fault_tree_str(alternative_case_study_content):
    """Alternative fault tree from the case study with adapted Waterhammer attack."""
    return _extract_section(alternative_case_study_content, "dog.fault_tree")


@pytest.fixture
def case_study_object_graph_str(case_study_content):
    """Object graph from the case study."""
    return _extract_section(case_study_content, "dog.object_graph")


@pytest.fixture
def alternative_case_study_object_graph_str(alternative_case_study_content):
    """Object graph from the case study with adapted Waterhammer attack."""
    return _extract_section(alternative_case_study_content, "dog.object_graph")


@pytest.fixture
def case_study_models(case_study_attack_tree_str, case_study_fault_tree_str,
                      case_study_object_graph_str,
                      transform_disruption_tree_str,
                      transform_object_graph_str):
    """Returns the case study models as a list for unpacking."""
    object_graph = transform_object_graph_str(case_study_object_graph_str)
    attack_tree = transform_disruption_tree_str(case_study_attack_tree_str,
                                                object_graph)
    fault_tree = transform_disruption_tree_str(case_study_fault_tree_str,
                                               object_graph)
    return [attack_tree, fault_tree, object_graph]


@pytest.fixture
def alternative_case_study_models(
        alternative_case_study_attack_tree_str,
        alternative_case_study_fault_tree_str,
        alternative_case_study_object_graph_str,
        transform_disruption_tree_str,
        transform_object_graph_str):
    """Returns the alternative case study models as a list for unpacking."""
    object_graph = transform_object_graph_str(
        alternative_case_study_object_graph_str)
    attack_tree = transform_disruption_tree_str(
        alternative_case_study_attack_tree_str, object_graph)
    fault_tree = transform_disruption_tree_str(
        alternative_case_study_fault_tree_str, object_graph)
    return [attack_tree, fault_tree, object_graph]
