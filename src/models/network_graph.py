from networkx import DiGraph
from networkx.algorithms.components import is_weakly_connected
from networkx.algorithms.dag import is_directed_acyclic_graph

from src.transformers.exceptions import NotAcyclicError, NotConnectedError, \
    NotExactlyOneRootError


class TreeGraph(DiGraph):
    """Base class for tree graph structures in the application."""

    def validate_tree(self):
        """Validate the tree structure.
        
        Ensures the graph is:
        1. Directed and acyclic
        2. Weakly connected (all nodes are connected when edges are treated as undirected)
        3. Has exactly one root node (node with no incoming edges)
        """
        if not is_directed_acyclic_graph(self):
            raise NotAcyclicError()
        if not is_weakly_connected(self):
            raise NotConnectedError()
        if sum(1 for (node, in_deg) in self.in_degree if in_deg == 0) != 1:
            raise NotExactlyOneRootError()
