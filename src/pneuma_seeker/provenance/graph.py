# src/pneuma_seeker/provenance/graph.py
import html
from logging import Logger
import uuid

from pyvis.network import Network

from pneuma_seeker.core.ir_system.data_model import RetrieverType


class ProvenanceNode:
    """Represents a node in the provenance graph."""

    def __init__(self, source_retriever: RetrieverType, python_code: str):
        self.id = str(uuid.uuid4())
        self.source_retriever = source_retriever
        self.python_code = python_code
        self.parents = []
        self.children = []

    def add_child(self, child: "ProvenanceNode"):
        """Adds a child node to this node."""
        if child not in self.children:
            self.children.append(child)
        if self not in child.parents:
            child.parents.append(self)

    def __repr__(self):
        """String representation of the ProvenanceNode."""
        return f"<ProvenanceNode {self.id} ({self.source_retriever.name})>"


class ProvenanceGraph:
    """Manages a graph of ProvenanceNodes representing data provenance."""

    def __init__(self, logger: Logger, create_default_root: bool = True):
        """Create a provenance graph.

        Args:
            logger: Logger instance for messages.
            create_default_root: When True (default) create a default root node
                with python_code "tables = {}". When False, no default root is
                created. This is useful for deserialization where the serialized
                graph will supply its own nodes.
        """
        self.nodes: dict[str, ProvenanceNode] = {}
        self.logger = logger
        self.ROOT_NODE_CODE = "import pandas as pd\ntables: dict[str, pd.DataFrame] = {}"

        if create_default_root:
            # Initialize a default root node so the graph always starts with a
            # base context. This root holds the initial tables mapping used by
            # downstream steps.
            root_node = ProvenanceNode(
                RetrieverType.USER,
                self.ROOT_NODE_CODE,
            )
            self.nodes[root_node.id] = root_node
            self.logger.info(f"[PROV GRAPH] Root node {root_node.id} initialized.")

    def add_node(self, node: ProvenanceNode, overwrite: bool = False):
        """Adds a node to the graph."""
        if not isinstance(node, ProvenanceNode):
            raise ValueError(f"node must be a ProvenanceNode, got {type(node)}")

        existing = self.nodes.get(node.id)
        if existing and not overwrite:
            raise ValueError(
                f"node {node.id} already exists; set overwrite=True to update"
            )

        if existing and overwrite:
            existing.source_retriever = node.source_retriever
            existing.python_code = node.python_code
            self.logger.info(f"[PROV GRAPH] Node {node.id} updated (overwrite=True).")
            return existing

        self.nodes[node.id] = node
        self.logger.info(f"[PROV GRAPH] Node {node.id} added.")
        return node

    def connect(self, parent: ProvenanceNode, child: ProvenanceNode):
        """Connects parent and child nodes in the graph."""
        if not isinstance(parent, ProvenanceNode):
            raise ValueError(f"parent must be a ProvenanceNode, got {type(parent)}")
        if not isinstance(child, ProvenanceNode):
            raise ValueError(f"child must be a ProvenanceNode, got {type(child)}")

        parent_canon = self.nodes.get(parent.id, parent)
        child_canon = self.nodes.get(child.id, child)

        parent_canon.add_child(child_canon)
        self.logger.info(
            f"[PROV GRAPH] Parent node {parent_canon.id} and child node {child_canon.id} connected successfully."
        )

    def get_nodes(
        self, filters: dict[str, object] | None = None
    ) -> list[ProvenanceNode]:
        """Retrieves all nodes matching given filters (or all if no filters)."""
        if not filters:
            return list(self.nodes.values())
        return [
            node
            for node in self.nodes.values()
            if all(getattr(node, k, None) == v for k, v in filters.items())
        ]

    def get_node(self, filters: dict[str, object]) -> ProvenanceNode | None:
        """Retrieves a single node matching given filters."""
        nodes = self.get_nodes(filters)
        return nodes[0] if len(nodes) > 0 else None

    def get_node_by_id(self, node_id: str) -> ProvenanceNode | None:
        """Retrieves a node by ID (shortcut for get_node({'id': node_id}))."""
        return self.nodes.get(node_id)

    def trace_upstream(self, node: ProvenanceNode, include_self: bool = False):
        """Return all upstream (ancestor) nodes of the given node."""
        visited = set()
        stack = [node]

        while stack:
            n = stack.pop()
            for parent in n.parents:
                if parent not in visited:
                    visited.add(parent)
                    stack.append(parent)

        if include_self:
            visited.add(node)

        return list(visited)

    def trace_downstream(self, node: ProvenanceNode, include_self: bool = False):
        """Return all downstream (descendant) nodes of the given node."""
        visited = set()
        stack = [node]

        while stack:
            n = stack.pop()
            for child in n.children:
                if child not in visited:
                    visited.add(child)
                    stack.append(child)

        if include_self:
            visited.add(node)

        return list(visited)

    def to_text(self) -> str:
        """Returns a textual representation of the graph."""
        lines = []

        for _, node in sorted(self.nodes.items(), key=lambda x: x[0]):
            retriever_name = (
                getattr(node.source_retriever, "value", None)
                or getattr(node.source_retriever, "name", None)
                or str(node.source_retriever)
            )

            lines.append(f"{node.id}:")
            lines.append(f"  Source Retriever: {retriever_name}")
            lines.append(f"  Python Code: {node.python_code or '<empty>'}")
            lines.append(
                f"  Parents: {', '.join(p.id for p in node.parents) or '<none>'}"
            )
            lines.append(
                f"  Children: {', '.join(c.id for c in node.children) or '<none>'}"
            )
            lines.append("")

        return "\n".join(lines)

    def get_graph_code_concatenation(self) -> str:
        """
        Return a single Python code string that is the concatenation of all
        node.python_code values in topologically sorted order (parents before children).
        """
        # Compute in-degree of each node
        indegree = {node.id: 0 for node in self.nodes.values()}
        for node in self.nodes.values():
            for child in node.children:
                indegree[child.id] = indegree.get(child.id, 0) + 1

        # Kahn's algorithm (iterative topological sort)
        queue = [n for n in self.nodes.values() if indegree.get(n.id, 0) == 0]
        ordered_nodes = []
        visited_count = 0

        while queue:
            node = queue.pop(0)
            ordered_nodes.append(node)
            visited_count += 1

            for child in node.children:
                indegree[child.id] -= 1
                if indegree[child.id] == 0:
                    queue.append(child)

        # Detect cycles (non-DAG)
        if visited_count != len(self.nodes):
            self.logger.warning(
                "[PROV GRAPH] Cycle detected during topological ordering!"
            )

        code_sections = [node.python_code for node in ordered_nodes if node.python_code]
        return "\n\n".join(code_sections)

    def get_graph_visualization(self) -> str:
        net = Network(notebook=True, directed=True, cdn_resources="in_line")
        seen = set()

        for node in self.nodes.values():
            if node.id not in seen:
                tooltip = (
                    f"Source Retriever: {html.escape(str(node.source_retriever.value))}\n"
                    f"Python Code: {html.escape(node.python_code)}\n"
                    f"# Children: {len(node.children)}\n"
                    f"# Parents: {len(node.parents)}"
                )
                net.add_node(node.id, label=node.id, title=tooltip)
                seen.add(node.id)

            for child in node.children:
                if child.id not in seen:
                    tooltip = (
                        f"Source Retriever: {html.escape(str(child.source_retriever.value))}\n"
                        f"Python Code: {html.escape(child.python_code)}\n"
                        f"# Children: {len(child.children)}\n"
                        f"# Parents: {len(child.parents)}"
                    )
                    net.add_node(child.id, label=child.id, title=tooltip)
                    seen.add(child.id)

                net.add_edge(node.id, child.id)

        return net.generate_html()

    def reset_for_materialization(self):
        """Resets the graph to include only USER retriever nodes and USER-USER connections."""
        keep = {
            node_id: node
            for node_id, node in self.nodes.items()
            if node.source_retriever == RetrieverType.USER
        }

        for node in keep.values():
            node.parents = [p for p in node.parents if p.id in keep]
            node.children = [c for c in node.children if c.id in keep]

        self.nodes = keep
        self.logger.info("[PROV GRAPH] The graph has been reset successfully.")
