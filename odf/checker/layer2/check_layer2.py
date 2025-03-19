import pathlib
from collections import deque
from fractions import Fraction
from typing import Iterator

from dd import cudd
from dd.cudd import Function
from lark import Transformer, Tree

from odf.checker.layer1.layer1_bdd import Layer1BDDTransformer
from odf.core.types import Configuration
from odf.models.disruption_tree import DisruptionTree
from odf.models.object_graph import ObjectGraph
from odf.transformers.configuration import parse_configuration
from odf.transformers.mixins.boolean_eval import BooleanEvalMixin


def dfs_nodes_with_complement(
        root: cudd.Function, is_complement: bool
) -> Iterator[tuple[Function, bool]]:
    """
    Generator that traverses the BDD in reverse-topological order in a
    non-recursive manner. For each node it yields a tuple: (node, complemented)
    where 'complemented' is True if an odd number of complemented edges were taken
    on the path from the original root to 'node'.

    Note:
      - Each node supports a "negated" attribute (True if the pointer is complemented).
      - Each node supports a "regular" property that returns the underlying (uncomplemented) node.
    """
    # Each stack element is a tuple: (node, complement_flag, visited_flag)
    stack = deque([(root, is_complement, False)])
    yielded = set()  # To avoid yielding the same (node, complement) pair more than once.
    iters = 0
    max_len = 0

    while stack:
        iters += 1
        max_len = max(max_len, len(stack))
        node, comp, visited = stack.pop()
        if (node, comp) in yielded:
            continue
        if visited:
            yielded.add((node, comp))
            yield node, comp
            continue

        # Mark the current node as visited
        stack.append((node, comp, True))

        # Terminal node?
        if node.var is None:
            continue

        # Process children (both low and high children)
        for child in (node.low, node.high):
            new_comp = comp ^ child.negated  # toggle complement flag if edge is complemented

            child_regular = child.regular
            stack.append((child_regular, new_comp, False))


def l2_prob(attack_tree: DisruptionTree,
            fault_tree: DisruptionTree,
            bdd: cudd.Function,
            configuration: Configuration) -> float:
    root = bdd
    complemented = root.negated
    while root.var in configuration:
        if configuration[root.var]:
            root = root.high
        else:
            root = root.low
            complemented ^= root.negated

    return calc_node_prob(attack_tree, fault_tree, root, complemented)


def calc_node_prob(attack_tree: DisruptionTree,
                   fault_tree: DisruptionTree,
                   root: cudd.Function,
                   is_complement: bool) -> float:
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

        if node.var in fault_tree:
            node_prob = fault_tree.nodes[node.var]["data"].probability
            if node_prob is None:
                # todo caz
                raise ValueError(
                    f"Node {node.var} has no probability in the fault tree")
            p_low = probs[to_key(node.low, complemented)] * (
                    Fraction(1) - node_prob)
            p_high = probs[to_key(node.high, complemented)] * node_prob
            probs[to_key(node, complemented)] = p_low + p_high
        elif node.var in attack_tree:
            node_prob = attack_tree.nodes[node.var]["data"].probability
            if node_prob is None:
                # todo caz
                raise ValueError(
                    f"Node {node.var} has no probability in the attack tree")
            p_low = probs[to_key(node.low, complemented)]
            p_high = probs[to_key(node.high, complemented)] * node_prob
            probs[to_key(node, complemented)] = max(p_low, p_high)
        else:
            raise AssertionError(
                "We should only encounter nodes from the attack or fault tree")
    return probs[to_key(root.regular, is_complement)]


def write_bdd_to_dot_file(root: Function, path: str | pathlib.Path) -> None:
    """Write a BDD to a DOT file using integer node labels.

    Args:
        root: The root node of the BDD
        path: Path where to write the DOT file
    """
    manager = root.bdd
    with open(path, 'w') as f:
        f.write('digraph "BDD" {\n')
        f.write('    rankdir=TB;\n')
        f.write('    ordering=out;\n')

        # First pass: collect nodes by level
        nodes_by_var = {}
        for node, _ in dfs_nodes_with_complement(root, root.negated):
            if node.var is None:  # Terminal node
                continue
            nodes_by_var.setdefault(node.var, []).append(node)

        # Write nodes by level to ensure same-level nodes are aligned
        for var, nodes in sorted(nodes_by_var.items()):
            f.write(f'    {{ rank=same; ')
            for node in nodes:
                f.write(f'{int(node)} ')
            f.write('}\n')
            for node in nodes:
                f.write(
                    f'    {int(node)} [shape=circle, label="{int(node)}"];\n')

        # Write terminal nodes
        f.write('    { rank=sink; ')
        for node, _ in dfs_nodes_with_complement(root, root.negated):
            if node.var is not None:  # Skip non-terminal nodes
                continue
            f.write(f'{int(node)} ')
        f.write('}\n')
        for node, _ in dfs_nodes_with_complement(root, root.negated):
            if node.var is not None:
                continue
            if node == manager.true:
                f.write(f'    {int(node)} [shape=box, label="1"];\n')
            else:
                f.write(f'    {int(node)} [shape=box, label="0"];\n')

        # Write edges after all nodes are defined
        for node, _ in dfs_nodes_with_complement(root, root.negated):
            if node.var is None:  # Skip terminal nodes
                continue

            # Write low edge (dashed if complemented)
            low_style = 'dotted' if node.low.negated else 'dashed'
            f.write(
                f'    {int(node)} -> {int(node.low.regular)} [style={low_style}];\n')

            # Write high edge (dashed if complemented)
            high_style = 'dotted' if node.high.negated else 'solid'
            f.write(
                f'    {int(node)} -> {int(node.high.regular)} [style={high_style}];\n')

        f.write('}\n')
        f.close()


# todo caz prob evidence

# noinspection PyMethodMayBeStatic
class Layer2Transformer(Transformer, BooleanEvalMixin):
    def __init__(self,
                 configuration: Configuration,
                 attack_tree: DisruptionTree,
                 fault_tree: DisruptionTree,
                 object_graph: ObjectGraph):
        super().__init__()
        self.configuration = configuration
        self.attack_tree = attack_tree
        self.fault_tree = fault_tree
        self.object_graph = object_graph
        self.used_object_properties = set()

    def probability_formula(self, items):
        formula_tree, relation, threshold = items

        l1_transformer = Layer1BDDTransformer(
            self.attack_tree, self.fault_tree, self.object_graph,
            reordering=False)
        bdd = l1_transformer.transform(formula_tree)

        needed_vars = l1_transformer.object_properties.intersection(bdd.support)
        given_vars = set(self.configuration.keys())
        missing_vars = needed_vars - given_vars
        if len(missing_vars) > 0:
            # todo caz
            raise ValueError(
                f"Missing object properties in configuration: {missing_vars}")
        self.used_object_properties.update(needed_vars)

        prob = l2_prob(self.attack_tree, self.fault_tree, bdd,
                       self.configuration)

        print(f"INFO: Probability: {prob}")  # todo caz reconstruct the formula

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
                raise ValueError("Invalid relation")

    def PROB_VALUE(self, items):
        return Fraction(items.value)


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
        # todo caz
        print(
            f"WARNING: The following variables of the configuration are not"
            f" object properties and will be ignored: {non_object_properties}")
        for var in non_object_properties:
            del configuration[var]

    transformer = Layer2Transformer(configuration, attack_tree, fault_tree,
                                    object_graph)
    res = transformer.transform(formula.children[1])

    surplus_vars = set(
        configuration.keys()) - transformer.used_object_properties
    if len(surplus_vars) > 0:
        # todo caz
        print(
            f"WARNING: You provided object properties in the configuration that"
            f" are not used in the formula, these can be removed: {surplus_vars}")

    return res
