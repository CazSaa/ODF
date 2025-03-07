from lark import Tree

from odf.checker.layer1.check_layer1 import check_layer1_query
from odf.models.disruption_tree import DisruptionTree
from odf.models.object_graph import ObjectGraph


def check_formulas(formulas_parse_tree: Tree, attack_tree: DisruptionTree,
                   fault_tree: DisruptionTree, object_graph: ObjectGraph):
    for formula in formulas_parse_tree.children:
        match formula.data:
            case "layer1_query":
                check_layer1_query(formula, attack_tree,
                                   fault_tree, object_graph)
            case "layer2_query":
                raise NotImplementedError()
            case "layer3_query":
                raise NotImplementedError()
            case _:
                raise ValueError(f"Unexpected formula type: {formula.data}")
    pass
