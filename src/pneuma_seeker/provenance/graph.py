# src/pneuma_seeker/provenance/graph.py
import html
from pyvis.network import Network
from pneuma_seeker.core.ir_system.data_model import RetrieverType


class ProvenanceNode:
    _id_counter = 1

    def __init__(self, source_retriever: RetrieverType, python_code: str):
        self.id = f"Node {ProvenanceNode._id_counter}"
        ProvenanceNode._id_counter += 1

        self.source_retriever = source_retriever
        self.python_code = python_code
        self.parents = []
        self.children = []

    def add_child(self, child: "ProvenanceNode"):
        if child not in self.children:
            self.children.append(child)
        if self not in child.parents:
            child.parents.append(self)

    def __repr__(self):
        return f"<ProvenanceNode {self.id} ({self.source_retriever.name})>"


class ProvenanceGraph:
    def __init__(self, logger=None):
        ProvenanceNode._id_counter = 1

        self.nodes: dict[str, ProvenanceNode] = {}
        self.logger = logger or self._noop_logger()

    # ----------------------------------------------------------------------
    # internal utilities
    # ----------------------------------------------------------------------
    def _noop_logger(self):
        class _Noop:
            def info(self, *_a, **_kw): ...
            def debug(self, *_a, **_kw): ...
        return _Noop()

    # ----------------------------------------------------------------------
    # core node ops
    # ----------------------------------------------------------------------
    def add_node(self, node: ProvenanceNode, overwrite: bool = False):
        if not isinstance(node, ProvenanceNode):
            raise ValueError(f"node must be a ProvenanceNode, got {type(node)}")

        existing = self.nodes.get(node.id)
        if existing and not overwrite:
            raise ValueError(f"node {node.id} already exists; set overwrite=True to update")

        if existing and overwrite:
            # update in place — preserve identity, parent/child relationships
            existing.source_retriever = node.source_retriever
            existing.python_code = node.python_code
            self.logger.info(f"[PROV GRAPH] Node {node.id} updated (overwrite=True).")
            return existing

        self.nodes[node.id] = node
        self.logger.info(f"[PROV GRAPH] Node {node.id} added.")
        return node

    def connect(self, parent: ProvenanceNode, child: ProvenanceNode):
        if not isinstance(parent, ProvenanceNode):
            raise ValueError(f"parent must be a ProvenanceNode, got {type(parent)}")
        if not isinstance(child, ProvenanceNode):
            raise ValueError(f"child must be a ProvenanceNode, got {type(child)}")

        # always resolve canonical instances from self.nodes if present
        parent_canon = self.nodes.get(parent.id, parent)
        child_canon = self.nodes.get(child.id, child)

        parent_canon.add_child(child_canon)
        self.logger.info(
            f"[PROV GRAPH] Parent node {parent_canon.id} and child node {child_canon.id} connected successfully."
        )

    # ----------------------------------------------------------------------
    # node retrieval
    # ----------------------------------------------------------------------
    def get_node_by_id(self, node_id: str):
        return self.nodes.get(node_id)

    def get_node(self, filters: dict):
        for node in self.nodes.values():
            if all(getattr(node, k, None) == v for k, v in filters.items()):
                return node
        return None

    def get_nodes(self, filters: dict):
        return [
            n for n in self.nodes.values()
            if all(getattr(n, k, None) == v for k, v in filters.items())
        ]

    # ----------------------------------------------------------------------
    # tracing
    # ----------------------------------------------------------------------
    def trace_upstream(self, node: ProvenanceNode):
        visited = []
        def dfs(n):
            for p in n.parents:
                if p not in visited:
                    visited.append(p)
                    dfs(p)
        dfs(node)
        return visited

    def trace_downstream(self, node: ProvenanceNode):
        visited = []
        def dfs(n):
            for c in n.children:
                if c not in visited:
                    visited.append(c)
                    dfs(c)
        dfs(node)
        return visited

    # ----------------------------------------------------------------------
    # text output
    # ----------------------------------------------------------------------
    def to_text(self) -> str:
        lines = []
        # deterministic ordering: sort by numeric part of "Node <n>"
        def _node_sort_key(item):
            node_id = item[0]  # dict key is something like "Node 1"
            try:
                return int(node_id.split()[-1])
            except Exception:
                return node_id

        for node_id, node in sorted(self.nodes.items(), key=_node_sort_key):
            lines.append(f"{node.id}:")
            lines.append(f"  Source Retriever: {node.source_retriever.value}")
            lines.append(f"  Python Code: {node.python_code}")
            lines.append(f"  Parents: {[p.id for p in node.parents]}")
            lines.append(f"  Children: {[c.id for c in node.children]}")
            lines.append("")
        return "\n".join(lines)

    # ----------------------------------------------------------------------
    # visualization
    # ----------------------------------------------------------------------
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

    # ----------------------------------------------------------------------
    # materialization reset
    # ----------------------------------------------------------------------
    def reset_for_materialization(self):
        # keep USER nodes and their immediate parents/children to avoid orphaning
        keep = {
            node_id: node
            for node_id, node in self.nodes.items()
            if node.source_retriever == RetrieverType.USER
        }
        for n in list(keep.values()):
            for p in n.parents:
                keep[p.id] = p
            for c in n.children:
                keep[c.id] = c
        self.nodes = keep
        self.logger.info("[PROV GRAPH] The graph has been reset successfully.")
