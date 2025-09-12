import html
import uuid

from logging import Logger
from typing import Any

from pneuma_seeker.core.ir_system.data_model import RetrieverType

from pyvis.network import Network


class ProvenanceNode:
    def __init__(
        self,
        output_data_id: str,
        output_data_ref: Any,  # Either path to data or data itself
        source_retriever: RetrieverType,  # Where the data comes from
        op_description: str,
    ):
        self.id = str(uuid.uuid4())
        self.output_data_id = output_data_id
        self.output_data_ref = output_data_ref
        self.op_description = op_description
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
            f"[PROV GRAPH] Parent node {parent.id} and child node {child.id} connected successfully."
        )

    def trace_upstream(self, node: ProvenanceNode) -> list[ProvenanceNode]:
        """Return all ancestors of a given node, traversing parents recursively."""
        return self.__trace(node, "parents")

    def trace_downstream(self, node: ProvenanceNode) -> list[ProvenanceNode]:
        """Return all descendants of a given node, traversing children recursively."""
        return self.__trace(node, "children")

    def get_graph_visualization(self):
        net = Network(notebook=True, directed=True, cdn_resources="in_line")

        for node in self.nodes.values():
            if node.id not in net.get_nodes():
                tooltip = f"""
                Output Data ID: {html.escape(node.output_data_id)}
                Source: {html.escape(str(node.source_retriever.value))}
                Description: {html.escape(node.op_description)}
                # Children: {len(node.children)}
                # Parents: {len(node.parents)}
                """

                net.add_node(
                    node.id,
                    label=node.output_data_id,
                    title=tooltip,
                )

            for child in node.children:
                if child.id not in net.get_nodes():
                    tooltip = f"""
                    Output Data ID: {html.escape(child.output_data_id)}
                    Source: {html.escape(str(child.source_retriever.value))}
                    Description: {html.escape(child.op_description)}
                    # Children: {len(child.children)}
                    # Parents: {len(child.parents)}
                    """
                    net.add_node(
                        child.id,
                        label=child.output_data_id,
                        title=tooltip,
                    )
                net.add_edge(node.id, child.id)

        return net.generate_html()

    def to_text(self, node: ProvenanceNode | None = None, max_depth: int = 5) -> str:
        """
        Returns a textual representation of the graph with integer IDs instead of UUIDs.
        """
        # Mapping from original UUIDs to integer IDs for readability + token saving
        id_map: dict[str, int] = {}
        next_id = 1

        def _get_int_id(node_id: str) -> int:
            nonlocal next_id
            if node_id not in id_map:
                id_map[node_id] = next_id
                next_id += 1
            return id_map[node_id]

        def _node_text(n: ProvenanceNode, depth: int, visited: set[str]) -> str:
            if depth > max_depth or n.id in visited:
                return ""
            visited.add(n.id)
            int_id = _get_int_id(n.id)
            lines = [
                f"{'  ' * depth}- Node {int_id}",
                f"{'  ' * depth}  Output Data ID: {n.output_data_id}",
                f"{'  ' * depth}  Source: {n.source_retriever.value}",
                f"{'  ' * depth}  Description: {n.op_description}",
                f"{'  ' * depth}  Children: {[ _get_int_id(c.id) for c in n.children ]}",
                f"{'  ' * depth}  Parents: {[ _get_int_id(p.id) for p in n.parents ]}",
            ]
            for child in n.children:
                lines.append(_node_text(child, depth + 1, visited))
            return "\n".join([line for line in lines if line])

        visited_nodes = set()
        if node is not None:
            return _node_text(node, 0, visited_nodes)
        else:
            roots = [n for n in self.nodes.values() if not n.parents]
            all_texts = [_node_text(root, 0, visited_nodes) for root in roots]
            return "\n\n".join(all_texts)

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
