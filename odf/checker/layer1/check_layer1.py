from lark import Tree

from odf.checker.layer1.layer1_bdd import Layer1BDDInterpreter
from odf.core.types import Configuration
from odf.models.disruption_tree import DisruptionTree
from odf.models.object_graph import ObjectGraph
from odf.transformers.configuration import parse_configuration


def check_layer1_query(formula: Tree,
                       attack_tree: DisruptionTree,
                       fault_tree: DisruptionTree,
                       object_graph: ObjectGraph):
    assert formula.data == "layer1_query"

    configuration = parse_configuration(formula.children[0].children[0])

    query_type = formula.children[0].data
    match query_type:
        case "check":
            formula = formula.children[0].children[1]
            res = layer1_check(formula, configuration, attack_tree, fault_tree,
                               object_graph)
            print(f"Result: {res}")
        case "compute_all":
            formula = formula.children[0].children[1]
            res = layer1_compute_all(formula, configuration, attack_tree,
                                     fault_tree, object_graph)
            print(f"Result: {res}")
        case _:
            # Should be unreachable
            raise ValueError(f"Unexpected query type: {query_type}")


def layer1_check(formula: Tree,
                 configuration: Configuration,
                 attack_tree: DisruptionTree,
                 fault_tree: DisruptionTree,
                 object_graph: ObjectGraph) -> bool:
    transformer = Layer1BDDInterpreter(attack_tree, fault_tree, object_graph)
    bdd = transformer.interpret(formula)

    needed_vars = bdd.support
    given_vars = set(configuration.keys())
    missing_vars = needed_vars - given_vars
    if len(missing_vars) > 0:
        # todo caz
        raise ValueError(f"Missing variables: {missing_vars}")

    non_existing_vars = given_vars - needed_vars
    if len(non_existing_vars) > 0:
        # todo caz
        print(
            f"WARNING: You specified variables that either do not exist"
            f" (perhaps you made a typo?), or do not influence the outcome of"
            f" the formula. These variables will be ignored, and are not"
            f" necessary to satisfy the given formula: {non_existing_vars}")
        for var in non_existing_vars:
            del configuration[var]

    res = bdd.eval(configuration)

    return res


def layer1_compute_all(formula: Tree,
                       configuration: Configuration,
                       attack_tree: DisruptionTree,
                       fault_tree: DisruptionTree,
                       object_graph: ObjectGraph) -> set[frozenset[str]]:
    if formula.data != "mrs":
        formula = Tree("mrs", [formula])

    transformer = Layer1BDDInterpreter(attack_tree, fault_tree, object_graph)
    bdd = transformer.interpret(formula)
    manager = transformer.bdd

    needed_vars = transformer.object_properties.intersection(bdd.support)
    given_vars = set(configuration.keys())
    missing_vars = needed_vars - given_vars
    if len(missing_vars) > 0:
        # todo caz
        raise ValueError(
            f"Missing object properties in configuration: {missing_vars}")

    non_existing_vars = given_vars - needed_vars
    if len(non_existing_vars) > 0:
        # todo caz
        print(
            f"WARNING: You specified object properties that either do not exist"
            f" (perhaps you made a typo?), or do not influence the outcome of"
            f" the formula. These object properties will be ignored, and are"
            f" not necessary to satisfy the given formula: {non_existing_vars}")
        for var in non_existing_vars:
            del configuration[var]

    bdd = manager.let(configuration, bdd)

    res = set()
    for assignment in manager._pick_iter(bdd):
        res.add(
            frozenset(var for var, val in assignment.items() if val == True))
    return res
