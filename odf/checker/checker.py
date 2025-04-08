from lark import Tree

from odf.checker.layer1.check_layer1 import check_layer1_query
from odf.checker.layer2.check_layer2 import check_layer2_query
from odf.checker.layer3.check_layer3 import check_layer3_query
from odf.core.constants import SEPARATOR_LENGTH, COLOR_GRAY, COLOR_RESET
from odf.models.disruption_tree import DisruptionTree
from odf.models.object_graph import ObjectGraph
from odf.utils.reconstructor import reconstruct

SEPARATOR = "-" * SEPARATOR_LENGTH


def check_formulas(formulas_parse_tree: Tree, attack_tree: DisruptionTree,
                   fault_tree: DisruptionTree, object_graph: ObjectGraph):
    for i, formula in enumerate(formulas_parse_tree.children):
        formula_string = reconstruct(formula, multiline=True)

        print("\n\n" + SEPARATOR)
        print(f"{COLOR_GRAY}Processing Formula {i + 1}:{COLOR_RESET}")
        print(f"  {formula_string}")
        print(SEPARATOR)

        match formula.data:
            case "layer1_query":
                check_layer1_query(formula, attack_tree,
                                   fault_tree, object_graph)
            case "layer2_query":
                check_layer2_query(formula.children[0], attack_tree,
                                   fault_tree, object_graph)
            case "layer3_query":
                check_layer3_query(formula.children[0], attack_tree,
                                   fault_tree, object_graph)
            case _:
                raise AssertionError(f"Unexpected formula type: {formula.data}")
