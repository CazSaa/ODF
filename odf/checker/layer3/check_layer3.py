from typing import Literal, Optional

from lark import Tree, Token
from lark.visitors import Interpreter

from odf.checker.exceptions import MissingNodeImpactError
from odf.checker.layer1.layer1_bdd import Layer1BDDInterpreter
from odf.checker.layer2.check_layer2 import calc_node_prob
from odf.models.disruption_tree import DisruptionTree
from odf.models.object_graph import ObjectGraph
from odf.transformers.mixins.mappings import BooleanMappingMixin
from odf.utils.dfs import find_config_reflection_nodes
from odf.utils.logger import logger


class CollectEvidenceInterpreter(Interpreter, BooleanMappingMixin):
    def __init__(self):
        super().__init__()
        self.evidence: dict[str, bool] = {}
        self.formula_type: Optional[str] = None
        self.object_name: Optional[str] = None

    def layer3_query(self, tree: Tree):
        self.visit_children(tree)
        return self.evidence, self.formula_type, self.object_name

    def boolean_evidence(self, tree: Tree):
        return self.mappings_to_dict(self.visit_children(tree))

    def with_boolean_evidence(self, tree: Tree):
        child_evidence = self.visit(tree.children[1])
        self.evidence.update(child_evidence)

        self.visit(tree.children[0])

    # Stop visiting children when we reach a formula
    def __default__(self, tree: Tree):
        self.formula_type = tree.data
        self.object_name = tree.children[0].value


def most_risky(object_name: str,
               tree_type: Literal["attack", "fault"],
               evidence: dict[str, bool],
               attack_tree: DisruptionTree,
               fault_tree: DisruptionTree,
               object_graph: ObjectGraph):
    the_tree = attack_tree if tree_type == "attack" else fault_tree

    participant_nodes = the_tree.participant_nodes(object_name)
    if not participant_nodes:
        logger.info(
            f"There are no nodes in the {tree_type} tree that participate in the {object_name} object.")
        return None

    object_properties = set(object_graph.object_properties)
    used_evidence = set()
    max_risk = -1
    max_element = None
    for participant_node in participant_nodes:
        if participant_node.impact is None:
            raise MissingNodeImpactError(participant_node.name, tree_type)

        interpreter = Layer1BDDInterpreter(attack_tree, fault_tree,
                                           object_graph, reordering=False)
        manager = interpreter.bdd

        formula_tree = Tree("node_atom",
                            [Token("NODE_NAME", participant_node.name)])
        bdd = interpreter.interpret(formula_tree)

        if bdd == manager.false:
            logger.warning(f"Node {participant_node.name} is not satisfiable.")
            continue

        bdd_support = bdd.support
        needed_evidence = {k: v for k, v in evidence.items() if
                           k in bdd_support}
        if needed_evidence:
            bdd = manager.let(needed_evidence, bdd)
            used_evidence.update(needed_evidence.keys())

        if bdd == manager.false:
            logger.warning(
                f"The provided evidence made the node {participant_node.name} unsatisfiable. Evidence: {needed_evidence}")
            continue

        risk = -1
        for cr_node, is_compl in find_config_reflection_nodes(bdd,
                                                              lambda node: node.var in object_properties):
            p = calc_node_prob(attack_tree, fault_tree, cr_node, is_compl, {})
            risk = max(risk, p * participant_node.impact)
        logger.info("Risk for node %s: %f", participant_node.name, risk)

        if risk > max_risk:
            max_risk = risk
            max_element = participant_node

    unused_evidence = set(evidence.keys()) - used_evidence
    if unused_evidence:
        logger.warning(
            f"You specified evidence that is not used in this formula, these elements can be removed: {unused_evidence}")
    return max_element


def check_layer3_query(formula: Tree,
                       attack_tree: DisruptionTree,
                       fault_tree: DisruptionTree,
                       object_graph: ObjectGraph):
    assert formula.data == "layer3_query"
    evidence_interpreter = CollectEvidenceInterpreter()
    evidence, formula_type, object_name = evidence_interpreter.visit(formula)
    assert formula_type is not None

    match formula_type:
        case "most_risky_a":
            result = most_risky(object_name, "attack", evidence, attack_tree,
                                fault_tree, object_graph)
            print(f"The most risky attack node is: {result.name}")
        case "most_risky_f":
            result = most_risky(object_name, "fault", evidence, attack_tree,
                                fault_tree, object_graph)
            print(f"The most risky fault node is: {result.name}")
