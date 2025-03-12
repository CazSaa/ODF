from lark import Tree

from odf.checker.layer1.layer1_bdd import Layer1BDDTransformer
from odf.models.disruption_tree import DisruptionTree
from odf.models.object_graph import ObjectGraph
from odf.transformers.configuration import ConfigurationTransformer

Configuration = dict[str, bool]


def parse_configuration(configuration_tree: Tree) -> Configuration:
    assert configuration_tree.data == "configuration"
    transformer = ConfigurationTransformer()
    return transformer.transform(configuration_tree)


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
            raise NotImplementedError()
        case _:
            raise ValueError(f"Unexpected query type: {query_type}")


def layer1_check(formula: Tree,
                 configuration: Configuration,
                 attack_tree: DisruptionTree,
                 fault_tree: DisruptionTree,
                 object_graph: ObjectGraph) -> bool:
    transformer = Layer1BDDTransformer(attack_tree, fault_tree, object_graph)
    bdd = transformer.transform(formula)
    manager = transformer.bdd

    needed_vars = bdd.support
    given_vars = set(configuration.keys())
    missing_vars = needed_vars - given_vars
    if len(missing_vars) > 0:
        # todo caz
        raise ValueError(f"Missing variables: {missing_vars}")

    non_existing_vars = given_vars - manager.vars
    if len(non_existing_vars) > 0:
        # todo caz
        print(
            f"WARNING: You specified variables that do not exist in the model, these will be ignored: {non_existing_vars}")
        for var in non_existing_vars:
            del configuration[var]

    res = bdd.eval(configuration)

    return res
