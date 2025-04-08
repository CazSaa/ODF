from collections import deque
from fractions import Fraction
from typing import Literal, Optional, Callable, Iterable

from dd import cudd, cudd_add
from lark import Tree, Token
from lark.visitors import Interpreter

from odf.checker.exceptions import MissingNodeImpactError
from odf.checker.layer1.layer1_bdd import Layer1BDDInterpreter
from odf.checker.layer2.check_layer2 import calc_node_prob
from odf.core.constants import COLOR_GRAY
from odf.models.disruption_tree import DisruptionTree
from odf.models.object_graph import ObjectGraph
from odf.transformers.mixins.mappings import BooleanMappingMixin
from odf.utils.dfs import find_config_reflection_nodes, dfs_mtbdd_terminals, \
    find_paths_to_min_terminal
from odf.utils.formatting import format_config, format_node_name, format_risk
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
            logger.warning(
                f"Node '{participant_node.name}' is not satisfiable.")
            continue

        bdd_support = bdd.support
        needed_evidence = {k: v for k, v in evidence.items() if
                           k in bdd_support}
        if needed_evidence:
            bdd = manager.let(needed_evidence, bdd)
            used_evidence.update(needed_evidence.keys())

        if bdd == manager.false:
            logger.warning(
                f"Evidence {needed_evidence} made node '{participant_node.name}' unsatisfiable.")
            continue

        risk = -1
        for cr_node, is_compl in find_config_reflection_nodes(bdd,
                                                              lambda node: node.var in object_properties):
            p = calc_node_prob(attack_tree, fault_tree, cr_node, is_compl, {})
            risk = max(risk, p * participant_node.impact)
        logger.info(
            f"Risk for node {participant_node.name}: {risk} (~{format_risk(float(risk))}{COLOR_GRAY})")

        if risk > max_risk:
            max_risk = risk
            max_element = participant_node

    unused_evidence = set(evidence.keys()) - used_evidence
    if unused_evidence:
        logger.warning(
            f"Evidence {unused_evidence} is not used by the formula and will be ignored.")
    return max_element


def create_mtbdd(mtbdd_manager: cudd_add.ADD,
                 attack_tree: DisruptionTree,
                 fault_tree: DisruptionTree,
                 object_properties: set[str],
                 bdd: cudd.Function,
                 impact: Fraction) -> cudd_add.Function:
    """
    Creates an MTBDD (ADD) representing risk based on a BDD.

    Iteratively traverses the BDD. When transitioning from an object property (OP)
    node to a non-OP node (event/attack), calculates the probability of the
    non-OP subtree and multiplies by impact to get risk, creating a terminal ADD node.
    Within OP nodes, constructs ITE ADD nodes.

    Args:
        mtbdd_manager: The ADD manager.
        attack_tree: The attack tree model.
        fault_tree: The fault tree model.
        object_properties: Set of variable names that are object properties.
        bdd: The input BDD.
        impact: The impact value associated with the BDD.

    Returns:
        The resulting ADD representing a mapping from configurations of object
        properties to risk values.
    """
    # (node, is_complement, parent_is_op)
    stack = deque([(bdd, bdd.negated, True)])
    # Memoization for computed ADDs
    results: dict[tuple[cudd.Function, bool], cudd_add.Function] = {}
    # Stores intermediate state for nodes being processed:
    # key: (node, is_complement), value: {'stage': 'start'/'waiting_high'/'waiting_low', 'high_result': ADD}
    processing_state: dict[tuple[cudd.Function, bool], dict] = {}

    while stack:
        current_bdd, current_complement, current_parent_is_op = stack[-1]
        current_key = (current_bdd, current_complement)

        if current_key in results:
            stack.pop()
            continue

        is_op = current_bdd.var in object_properties

        # Base Case: Transition from OP node to non-OP node
        if current_parent_is_op and not is_op:
            p = calc_node_prob(attack_tree, fault_tree, current_bdd,
                               current_complement, {})
            risk = p * impact
            result_add = mtbdd_manager.constant(float(risk))
            results[current_key] = result_add
            stack.pop()
            continue

        # Recursive Step: Still within OP nodes
        # This assertion holds because the base case handles parent_is_op=True, is_op=False
        # and the initial call starts with parent_is_op=True.
        # If parent_is_op=False, we wouldn't enter this part due to the base case logic.
        assert current_parent_is_op and is_op, \
            f"Unexpected state: parent_is_op={current_parent_is_op}, is_op={is_op} for var {current_bdd.var}"

        state = processing_state.get(current_key, {'stage': 'start'})

        high_child_bdd = current_bdd.high
        high_child_complement = current_complement
        high_child_key = (high_child_bdd, high_child_complement)

        low_child_bdd = current_bdd.low.regular
        low_child_complement = current_complement ^ current_bdd.low.negated
        low_child_key = (low_child_bdd, low_child_complement)

        if state['stage'] == 'start':
            # Process high child first
            processing_state[current_key] = {'stage': 'waiting_high'}
            if high_child_key not in results:
                stack.append((high_child_bdd, high_child_complement, is_op))
                continue  # Process high child
            # High child already processed (e.g., shared node), fall through

        if state['stage'] == 'waiting_high':
            if high_child_key not in results:
                raise RuntimeError(
                    f"High child {high_child_key} result not found for parent {current_key}")

            high_add = results[high_child_key]
            processing_state[current_key] = {'stage': 'waiting_low',
                                             'high_result': high_add}
            if low_child_key not in results:
                stack.append((low_child_bdd, low_child_complement, is_op))
                continue  # Process low child
            # Low child already processed, fall through

        if state['stage'] == 'waiting_low':
            if low_child_key not in results:
                raise RuntimeError(
                    f"Low child {low_child_key} result not found for parent {current_key}")

            low_add = results[low_child_key]
            high_add = state['high_result']

            # Combine results using ITE
            var_add = mtbdd_manager.var(current_bdd.var)
            result_add = mtbdd_manager.apply('ite', var_add, high_add, low_add)
            results[current_key] = result_add
            stack.pop()
            continue

    final_key = (bdd, bdd.negated)
    if final_key not in results:
        raise RuntimeError("Failed to compute final result for the MTBDD.")

    return results[final_key]


def configs_to_risk_mtbdd(
        object_name: str,
        evidence: dict[str, bool],
        attack_tree: DisruptionTree,
        fault_tree: DisruptionTree,
        object_graph: ObjectGraph
) -> Optional[cudd_add.Function]:
    mtbdd_manager = cudd_add.ADD()
    mt_sum = mtbdd_manager.zero

    participant_nodes = attack_tree.participant_nodes(object_name).union(
        fault_tree.participant_nodes(object_name))

    if not participant_nodes:
        logger.info(
            f"There are no nodes in the attack or fault tree that participate in the {object_name} object.")
        return None

    object_properties = set(object_graph.object_properties)
    used_evidence = set()
    mtbdd_manager.declare(*object_properties)

    for participant_node in participant_nodes:
        if participant_node.impact is None:
            raise MissingNodeImpactError(participant_node.name,
                                         "attack or fault")

        interpreter = Layer1BDDInterpreter(attack_tree, fault_tree,
                                           object_graph, reordering=False)
        manager = interpreter.bdd

        formula_tree = Tree("node_atom",
                            [Token("NODE_NAME", participant_node.name)])
        bdd = interpreter.interpret(formula_tree)

        if bdd == manager.false:
            logger.warning(
                f"Node '{participant_node.name}' is not satisfiable.")
            continue

        bdd_support = bdd.support
        needed_evidence = {k: v for k, v in evidence.items() if
                           k in bdd_support}
        if needed_evidence:
            bdd = manager.let(needed_evidence, bdd)
            used_evidence.update(needed_evidence.keys())

        if bdd == manager.false:
            logger.warning(
                f"Evidence {needed_evidence} made node '{participant_node.name}' unsatisfiable.")
            continue

        mtbdd = create_mtbdd(mtbdd_manager,
                             attack_tree,
                             fault_tree,
                             object_properties,
                             bdd,
                             participant_node.impact)
        mt_sum = mtbdd_manager.apply('+', mt_sum, mtbdd)

    unused_evidence = set(evidence.keys()) - used_evidence
    if unused_evidence:
        logger.warning(
            f"Evidence {unused_evidence} is not used by the formula and will be ignored.")

    return mt_sum


def total_risk(object_name: str,
               func_type: Callable[[Iterable[float]], float],
               evidence: dict[str, bool],
               attack_tree: DisruptionTree,
               fault_tree: DisruptionTree,
               object_graph: ObjectGraph) -> Optional[float]:
    mt_sum = configs_to_risk_mtbdd(object_name, evidence, attack_tree,
                                   fault_tree, object_graph)
    if mt_sum is None:
        return None

    return func_type(dfs_mtbdd_terminals(mt_sum))


def optimal_conf(object_name: str,
                 evidence: dict[str, bool],
                 attack_tree: DisruptionTree,
                 fault_tree: DisruptionTree,
                 object_graph: ObjectGraph) -> Optional[list[dict[str, bool]]]:
    mt_sum = configs_to_risk_mtbdd(object_name, evidence, attack_tree,
                                   fault_tree, object_graph)
    if mt_sum is None:
        return None

    paths, min_term = find_paths_to_min_terminal(mt_sum)
    assert min_term is not None
    assert len(paths) > 0

    logger.info(
        f"There {'are multiple' if len(paths) > 1 else 'is one'} optimal configuration"
        f"{'s' if len(paths) > 1 else ''} with "
        f"{'the same ' if len(paths) > 1 else 'a '}risk value of {format_risk(min_term)}")

    return paths


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
            print(f"  Most Risky Attack Node: {format_node_name(result.name)}")
        case "most_risky_f":
            result = most_risky(object_name, "fault", evidence, attack_tree,
                                fault_tree, object_graph)
            print(f"  Most Risky Fault Node: {format_node_name(result.name)}")
        case "max_total_risk":
            result = total_risk(object_name, max, evidence, attack_tree,
                                fault_tree, object_graph)
            print(f"  Maximum Total Risk: {format_risk(result)}")
        case "min_total_risk":
            result = total_risk(object_name, min, evidence, attack_tree,
                                fault_tree, object_graph)
            print(f"  Minimum Total Risk: {format_risk(result)}")
        case "optimal_conf":
            result = optimal_conf(object_name, evidence, attack_tree,
                                  fault_tree, object_graph)
            print("  Optimal Configurations:")
            for config in result:
                print(f"    - {format_config(config)}")
