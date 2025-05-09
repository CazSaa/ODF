from fractions import Fraction

from dd import cudd
from dd.cudd import Function
from lark import Tree
from lark.visitors import Interpreter, visit_children_decor

from odf.checker.exceptions import MissingNodeProbabilityError, \
    MissingConfigurationError
from odf.checker.layer1.layer1_bdd import Layer1BDDInterpreter
from odf.core.constants import COLOR_GRAY, COLOR_RESET
from odf.core.types import Configuration
from odf.models.disruption_tree import DisruptionTree
from odf.models.object_graph import ObjectGraph
from odf.transformers.configuration import parse_configuration
from odf.transformers.prob_evidence_prepass import PrePassEvidenceInterpreter
from odf.utils.dfs import dfs_nodes_with_complement
from odf.utils.formatting import format_boolean, format_risk
from odf.utils.logger import logger
from odf.utils.reconstructor import reconstruct


def l2_prob(attack_tree: DisruptionTree,
            fault_tree: DisruptionTree,
            bdd: cudd.Function,
            configuration: Configuration,
            prob_evidence: dict) -> Fraction:
    root = bdd
    complemented = root.negated
    while root.var in configuration:
        if configuration[root.var]:
            root = root.high
        else:
            root = root.low
            complemented ^= root.negated

    return calc_node_prob(attack_tree, fault_tree, root, complemented,
                          prob_evidence)


def calc_node_prob(attack_tree: DisruptionTree,
                   fault_tree: DisruptionTree,
                   root: cudd.Function,
                   is_complement: bool,
                   prob_evidence: dict) -> Fraction:
    manager = root.bdd

    probs = {
        manager.true: Fraction(1),
        manager.false: Fraction(0),
    }

    def to_key(node_: Function, complemented_: bool) -> Function:
        return node_ if not complemented_ else manager.apply("not", node_)

    for node, complemented in dfs_nodes_with_complement(root.regular,
                                                        is_complement):
        if to_key(node, complemented) in probs:
            continue

        # If we have evidence for this node, use it instead of the node's probability
        if node.var in fault_tree:
            if node.var in prob_evidence:
                node_prob = prob_evidence[node.var]
            else:
                node_prob = fault_tree.nodes[node.var]["data"].probability
                if node_prob is None:
                    raise MissingNodeProbabilityError(node.var, "fault tree")
            p_low = probs[to_key(node.low, complemented)] * (
                    Fraction(1) - node_prob)
            p_high = probs[to_key(node.high, complemented)] * node_prob
            probs[to_key(node, complemented)] = p_low + p_high
        elif node.var in attack_tree:
            if node.var in prob_evidence:
                node_prob = prob_evidence[node.var]
            else:
                node_prob = attack_tree.nodes[node.var]["data"].probability
                if node_prob is None:
                    raise MissingNodeProbabilityError(node.var, "attack tree")
            p_low = probs[to_key(node.low, complemented)]
            p_high = probs[to_key(node.high, complemented)] * node_prob
            probs[to_key(node, complemented)] = max(p_low, p_high)
        else:
            raise AssertionError(
                "We should only encounter nodes from the attack or fault tree")
    return probs[to_key(root.regular, is_complement)]


def calc_prob(configuration, evidence, formula_tree, attack_tree, fault_tree,
              object_graph) -> tuple[set[str], Fraction]:
    l1_transformer = Layer1BDDInterpreter(
        attack_tree, fault_tree, object_graph,
        reordering=False)
    bdd = l1_transformer.interpret(formula_tree)
    needed_vars = l1_transformer.object_properties.intersection(bdd.support)
    given_vars = set(configuration.keys())
    missing_vars = needed_vars - given_vars
    if len(missing_vars) > 0:
        raise MissingConfigurationError(missing_vars,
                                        type_name="object properties")
    prob = l2_prob(attack_tree, fault_tree, bdd,
                   configuration, evidence)
    return needed_vars, prob


# noinspection PyMethodMayBeStatic
class Layer2Interpreter(Interpreter):
    def __init__(self,
                 configuration: Configuration,
                 attack_tree: DisruptionTree,
                 fault_tree: DisruptionTree,
                 object_graph: ObjectGraph,
                 prob_evidence: dict[int, dict[str, Fraction]]):
        super().__init__()
        self.configuration = configuration
        self.attack_tree = attack_tree
        self.fault_tree = fault_tree
        self.object_graph = object_graph
        self.used_object_properties = set()
        # Map formula node IDs to their evidence
        self.prob_evidence_per_formula = prob_evidence

    def layer2_formula(self, tree):
        self.visit_children(tree)

    @visit_children_decor
    def with_probability_evidence(self, items):
        return items[0]

    def probability_formula(self, tree: Tree):
        formula_tree = tree.children[0]
        relation = tree.children[1]
        threshold = Fraction(tree.children[2])

        formula_id = id(formula_tree)

        # Get evidence for this formula, if any
        evidence = self.prob_evidence_per_formula.get(formula_id, {})

        needed_vars, prob = calc_prob(
            self.configuration, evidence, formula_tree, self.attack_tree,
            self.fault_tree, self.object_graph)
        self.used_object_properties.update(needed_vars)

        if evidence:
            evidence_str = ", ".join(f"{k}={v}" for k, v in evidence.items())
            logger.info(
                f"P({reconstruct(formula_tree)}) with evidence [{evidence_str}] = {prob} (~{format_risk(float(prob))}{COLOR_GRAY}){COLOR_RESET}")
        else:
            logger.info(
                f"P({reconstruct(formula_tree)}) = {prob} (~{format_risk(float(prob))}{COLOR_GRAY}){COLOR_RESET}")

        match relation:
            case "<":
                return prob < threshold
            case "<=":
                return prob <= threshold
            case "==":
                return prob == threshold
            case ">=":
                return prob >= threshold
            case ">":
                return prob > threshold
            case _:
                raise AssertionError("Invalid relation")

    def impl_formula(self, tree):
        a, b = self.visit_children(tree)
        return (not a) or b

    def or_formula(self, tree):
        a, b = self.visit_children(tree)
        return a or b

    def and_formula(self, tree):
        a, b = self.visit_children(tree)
        return a and b

    def equiv_formula(self, tree):
        a, b = self.visit_children(tree)
        return a == b

    def nequiv_formula(self, tree):
        a, b = self.visit_children(tree)
        return a != b

    def neg_formula(self, tree):
        a, = self.visit_children(tree)
        return not a


def check_layer2_query(formula: Tree,
                       attack_tree: DisruptionTree,
                       fault_tree: DisruptionTree,
                       object_graph: ObjectGraph):
    assert formula.data == "layer2_query"
    assert formula.children[0].data == "configuration"

    configuration = parse_configuration(formula.children[0])
    non_object_properties = set(configuration.keys()) - set(
        object_graph.object_properties)
    if len(non_object_properties) > 0:
        logger.warning(
            f"Configuration variables {non_object_properties} are not object properties and will be ignored.")
        for var in non_object_properties:
            del configuration[var]

    # First run a pre-pass to collect all probabilistic evidence from the parse tree
    evidence_interpreter = PrePassEvidenceInterpreter()
    evidence_interpreter.visit(formula.children[1])

    # Create the transformer and pass the collected evidence
    transformer = Layer2Interpreter(configuration, attack_tree, fault_tree,
                                    object_graph,
                                    evidence_interpreter.evidence_per_formula)

    res = transformer.visit(formula.children[1])

    surplus_vars = set(
        configuration.keys()) - transformer.used_object_properties
    if len(surplus_vars) > 0:
        logger.warning(
            f"Object properties {surplus_vars} in configuration are not used by the formula and will be ignored.")

    print(f"  Result: {format_boolean(res)}")
    return res
