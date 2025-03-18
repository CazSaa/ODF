from typing import Optional, Iterator

from odf.models.tree_graph import TreeGraph


class ObjectNode:
    def __init__(self, name: str, properties: Optional[list[str]] = None):
        self.name = name
        self.properties = properties

    def update_from_attrs(self, attrs: dict) -> None:
        if "properties" in attrs:
            self.properties = attrs["properties"]


class ObjectGraph(TreeGraph[ObjectNode]):
    def has_object_property(self, object_property: str) -> bool:
        # TODO caz very inefficient
        return any(object_property == prop for prop in self.object_properties)

    @property
    def object_properties(self) -> Iterator[str]:
        return (prop for node in self.nodes_obj() for prop in
                (node.properties or []))
