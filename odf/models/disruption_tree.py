import re
from typing import Optional, Literal

from networkx.algorithms.components import is_weakly_connected
from networkx.algorithms.dag import descendants

from odf.models.tree_graph import TreeGraph
from odf.transformers.exceptions import NotConnectedError, \
    NotExactlyOneRootError

GateType = Literal["and", "or"]

NODE_NAME_PATTERN = re.compile(r'[a-zA-Z_][a-zA-Z0-9_]*')


class DTNode:
    def __init__(self, name: str,
                 probability: Optional[float] = None,
                 objects: Optional[list[str]] = None,
                 condition: Optional[str] = None,
                 gate_type: Optional[GateType] = None):
        self.name = name
        self.probability = probability
        self.objects = objects
        self.condition = condition
        self.gate_type = gate_type

    def update_from_attrs(self, attrs: dict) -> None:
        if "probability" in attrs:
            self.probability = attrs["probability"]
        if "objects" in attrs:
            self.objects = attrs["objects"]
        if "condition" in attrs:
            self.condition = attrs["condition"]
        if "gate_type" in attrs:
            self.gate_type = attrs["gate_type"]

    @property
    def object_properties(self) -> set[str]:
        if self.condition is None:
            return set()
        return set(re.findall(NODE_NAME_PATTERN, self.condition))


class DisruptionTree(TreeGraph[DTNode]):
    def has_basic_node(self, node_name: str) -> bool:
        return node_name in self.nodes and self.out_degree(node_name) == 0

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
