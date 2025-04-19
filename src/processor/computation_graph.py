from datetime import datetime
from typing import Any
from uuid import uuid4


class Node:
    def __init__(
        self,
        computation_description: str,
        computation_output: Any,
        input_nodes: list["Node"] = None,
    ):
        self.id = str(uuid4())
        self.timestamp = str(datetime.now())
        self.input_nodes = input_nodes or []
        self.computation_description = computation_description
        self.computation_output = computation_output

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "input_nodes": [input_node.id for input_node in self.input_nodes],
            "computation_description": self.computation_description,
            "computation_output": self.computation_output,
        }


class ComputationGraph:
    def __init__(self):
        self.nodes: list[Node] = []

    def add_node(self, node: Node):
        self.nodes.append(node)

    def to_json(self):
        return {"nodes": [node.to_dict() for node in self.nodes]}
