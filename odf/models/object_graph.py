from typing import Optional

from odf.models.tree_graph import TreeGraph


class ObjectNode:
    def __init__(self, name: str, properties: Optional[list[str]] = None):
        self.name = name
        self.properties = properties

    def update_from_attrs(self, attrs: dict) -> None:
        if "properties" in attrs:
            self.properties = attrs["properties"]


class ObjectGraph(TreeGraph[ObjectNode]):
    pass
