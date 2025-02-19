from networkx import DiGraph
from networkx.algorithms.dag import is_directed_acyclic_graph

from odf.transformers.exceptions import NotAcyclicError


class TreeGraph(DiGraph):
    """Base class for tree graph structures in the application."""

    def validate_tree(self):
        """Validate the tree structure.
        
        Ensures the graph is directed and acyclic
        """
        if not is_directed_acyclic_graph(self):
            raise NotAcyclicError()
