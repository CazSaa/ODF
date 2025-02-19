from typing import TypeVar, Iterator, Generic

from networkx import DiGraph
from networkx.algorithms.dag import is_directed_acyclic_graph

from odf.transformers.exceptions import NotAcyclicError

NodeT = TypeVar('NodeT')


class TreeGraph(DiGraph, Generic[NodeT]):
    """Base class for tree graph structures in the application."""

    def validate_tree(self):
        """Validate the tree structure.
        
        Ensures the graph is directed and acyclic
        """
        if not is_directed_acyclic_graph(self):
            raise NotAcyclicError()

    def nodes_obj(self) -> Iterator[NodeT]:
        """Returns an iterator over the node objects in the graph.
        
        Returns objects stored in the nodes rather than just the node IDs.
        """
        for node_id in self.nodes:
            yield self.nodes[node_id]["data"]
