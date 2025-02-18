from typing import Optional

import networkx as nx


class ObjectGraph(nx.DiGraph):
    pass


class ObjectNode:
    def __init__(self, name: str, properties: Optional[list[str]] = None):
        self.name = name
        self.properties = properties

    def update_from_attrs(self, attrs: dict) -> None:
        if "properties" in attrs:
            self.properties = attrs["properties"]
