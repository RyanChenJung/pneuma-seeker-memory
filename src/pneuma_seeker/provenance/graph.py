import uuid

from logging import Logger
from typing import Any

from pneuma_seeker.core.ir_system.data_model import RetrieverType


class ProvenanceNode:
    def __init__(
        self,
        data_ref: Any,  # Either path to data or data itself
        source_retriever: RetrieverType,  # Where the data comes from
        description: str | None = None,
    ):
        self.id = str(uuid.uuid4())
        self.data_ref = data_ref
        self.description = description
        self.source_retriever = source_retriever

        self.children: list[ProvenanceNode] = []
        self.parents: list[ProvenanceNode] = []

    def add_child(self, child: "ProvenanceNode"):
        self.children.append(child)
        child.parents.append(self)


class ProvenanceGraph:
    def __init__(self, logger: Logger):
        self.nodes: dict[str, ProvenanceNode] = {}
        self.logger = logger

    def add_node(self, node: ProvenanceNode, overwrite=False):
        if not isinstance(node, ProvenanceNode):
            raise ValueError(f"node must be a ProvenanceNode, got {type(node)}")
        if node.id in self.nodes.keys() and not overwrite:
            raise ValueError(
                f"node {node.id} already exists; set overwrite = True to update"
            )
        self.nodes[node.id] = node
        return node
    
    def get_node_by_id(self, node_id: str):
        return self.nodes.get(node_id)

    def get_node(self, filters: dict[str, Any]) -> ProvenanceNode | None:
        """Returns the first node where all filters match (attr=value)."""
        for node in self.nodes.values():
            if all(getattr(node, k, None) == v for k, v in filters.items()):
                return node
        return None

    def get_nodes(self, filters: dict[str, Any]) -> list[ProvenanceNode]:
        """Returns all nodes where all filters match (attr=value)."""
        return [
            node
            for node in self.nodes.values()
            if all(getattr(node, k, None) == v for k, v in filters.items())
        ]

    def connect(self, parent: ProvenanceNode, child: ProvenanceNode):
        if not isinstance(parent, ProvenanceNode):
            raise ValueError(f"parent must be a ProvenanceNode, got {type(parent)}")
        if not isinstance(child, ProvenanceNode):
            raise ValueError(f"child must be a ProvenanceNode, got {type(child)}")
        parent.add_child(child)
        self.logger.info(
            f"Parent node {parent.id} and child node {child.id} connected successfully."
        )

    def trace_upstream(self, node: ProvenanceNode) -> list[ProvenanceNode]:
        """Return all ancestors of a given node, traversing parents recursively."""
        return self.__trace(node, "parents")

    def trace_downstream(self, node: ProvenanceNode) -> list[ProvenanceNode]:
        """Return all descendants of a given node, traversing children recursively."""
        return self.__trace(node, "children")

    def __trace(self, start: ProvenanceNode, relation: str) -> list[ProvenanceNode]:
        visited, stack, result = set(), [start], []
        while stack:
            current = stack.pop()
            for neighbor in getattr(current, relation):
                if neighbor.id not in visited:
                    visited.add(neighbor.id)
                    result.append(neighbor)
                    stack.append(neighbor)
        return result
