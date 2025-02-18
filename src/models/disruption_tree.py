from typing import Optional, Literal

import networkx as nx

GateType = Literal["and", "or"]


class DisruptionTree(nx.DiGraph):
    pass


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
