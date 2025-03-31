import re
from fractions import Fraction
from typing import Optional, Literal

from lark import Tree, Visitor
from networkx.algorithms.components import is_weakly_connected
from networkx.algorithms.dag import descendants

from odf.checker.exceptions import InvalidProbabilityError, InvalidImpactError
from odf.models.tree_graph import TreeGraph
from odf.transformers.exceptions import NotConnectedError, \
    NotExactlyOneRootError

GateType = Literal["and", "or"]

NODE_NAME_PATTERN = re.compile(r'[a-zA-Z_][a-zA-Z0-9_]*')


# noinspection PyMethodMayBeStatic
class ConditionVariablesVisitor(Visitor):
    def __init__(self):
        super().__init__()
        self.vars: set[str] = set()

    def node_atom(self, items):
        self.vars.add(items.children[0].value)


class DTNode:
    def __init__(self, name: str,
                 probability: Optional[Fraction] = None,
                 impact: Optional[Fraction] = None,
                 objects: Optional[set[str]] = None,
                 condition_tree: Optional[Tree] = None,
                 gate_type: Optional[GateType] = None):
        self.name = name
        self.validate_probability(probability)
        self.probability = probability
        self.validate_impact(impact)
        self.impact = impact
        self.objects = objects
        self.condition_tree = condition_tree
        if condition_tree is not None:
            visitor = ConditionVariablesVisitor()
            visitor.visit(condition_tree)
            self.object_properties = visitor.vars
        else:
            self.object_properties = set()
        self.gate_type = gate_type

    def update_from_attrs(self, attrs: dict) -> None:
        if "probability" in attrs:
            self.validate_probability(attrs["probability"])
            self.probability = attrs["probability"]
        if "impact" in attrs:
            self.validate_impact(attrs["impact"])
            self.impact = attrs["impact"]
        if "objects" in attrs:
            self.objects = attrs["objects"]
        if "condition_tree" in attrs:
            self.condition_tree = attrs["condition_tree"]
            visitor = ConditionVariablesVisitor()
            visitor.visit(attrs["condition_tree"])
            self.object_properties = visitor.vars
        if "gate_type" in attrs:
            self.gate_type = attrs["gate_type"]

    def validate_probability(self, probability: Optional[Fraction]):
        if probability is None:
            return
        if probability < 0 or probability > 1:
            raise InvalidProbabilityError(self.name, probability)

    def validate_impact(self, impact: Optional[Fraction]):
        if impact is None:
            return
        if impact < 0:
            raise InvalidImpactError(self.name, impact)


class DisruptionTree(TreeGraph[DTNode]):
    def has_basic_node(self, node_name: str) -> bool:
        return node_name in self.nodes and self.out_degree(node_name) == 0

    def has_intermediate_node(self, node_name: str) -> bool:
        return node_name in self.nodes and self.out_degree(node_name) > 0

    def validate_tree(self):
        """Validate the tree structure.

        Ensures the graph is:
        1. Weakly connected (all nodes are connected when edges are treated as undirected)
        2. Has exactly one root node (node with no incoming edges)
        """
        super().validate_tree()
        if not is_weakly_connected(self):
            raise NotConnectedError()
        if sum(1 for (node, in_deg) in self.in_degree if in_deg == 0) != 1:
            raise NotExactlyOneRootError()

    def get_basic_descendants(self, node_name: str) -> set[str]:
        """Get all descendants of the given node (including itself) that are basic nodes (leaf nodes). """
        return {node for node in (descendants(self, node_name) | {node_name})
                if self.out_degree(node) == 0}

    def get_descendants(self, node_name: str) -> set[str]:
        """Get all descendants of the given node (including itself). """
        return {node for node in (descendants(self, node_name) | {node_name})}

    def get_strict_descendants(self, node_name: str) -> set[str]:
        """Get all descendants of the given node (excluding itself). """
        return {node for node in descendants(self, node_name)}

    def participant_nodes(self, object_name: str) -> set[DTNode]:
        """Get all nodes in which the object participates."""
        return {node for node in self.nodes_obj() if
                object_name in (node.objects or set())}

    def is_module(self, node_name: str) -> bool:
        r"""Check if a node is a module.
        
        A node is a module if all paths from its descendants to the rest of the
        tree must pass through this node. In other words, no descendant can have
        a parent that is not also a descendant of this node (except for the node
        itself).
        
        Example non-module:
             Root
             /  \
            B    D
           / \  /
          C   A

        Here B is not a module because while it has descendants A and C,
        its descendant A has a parent D that is not a descendant of B.

        Args:
            node_name: The name of the node to check.

        Returns:
            True if the node is a module, False otherwise.
        """
        descendants_ = self.get_strict_descendants(node_name)
        for descendant in descendants_:
            for predecessor in self.predecessors(descendant):
                if predecessor != node_name and predecessor not in descendants_:
                    return False
        return True
