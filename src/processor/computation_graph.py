from datetime import datetime
from inspect import currentframe
from typing import Any, Optional
from uuid import uuid4


class Node:
    def __init__(
        self,
        computation_description: str,
        computation_output: Any,
        function_name: str,
        class_name: Optional[str],
        input_nodes: Optional[list["Node"]] = None,
    ):
        self.id = str(uuid4())
        self.timestamp = str(datetime.now())
        self.input_nodes = input_nodes or []
        self.computation_description = computation_description
        self.computation_output = computation_output
        self.function_name = function_name
        self.class_name = class_name

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "input_nodes": [input_node.id for input_node in self.input_nodes],
            "computation_description": self.computation_description,
            "computation_output": self.computation_output,
            "function_name": self.function_name,
            "class_name": self.class_name,
        }


class ComputationGraph:
    def __init__(self):
        self.nodes: list[Node] = []

    def create_node(
        self,
        computation_description: str,
        computation_output: Any,
        input_nodes: Optional[list["Node"]] = None,
    ) -> Node:
        # Grab the caller info using inspect
        frame = currentframe()
        caller_frame = frame.f_back
        function_name = caller_frame.f_code.co_name
        class_name = None
        if "self" in caller_frame.f_locals:
            class_name = type(caller_frame.f_locals["self"]).__name__

        new_node = Node(
            computation_description,
            computation_output,
            function_name,
            class_name,
            input_nodes,
        )

        self.nodes.append(new_node)
        return new_node

    def to_json(self):
        return {"nodes": [node.to_dict() for node in self.nodes]}
