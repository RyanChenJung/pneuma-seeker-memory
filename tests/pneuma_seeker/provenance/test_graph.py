# tests/pneuma_seeker/provenance/test_graph.py
import os
import sys
import unittest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../src"))
)
from unittest.mock import MagicMock

from pneuma_seeker.core.ir_system.data_model import RetrieverType
from pneuma_seeker.provenance.graph import ProvenanceGraph, ProvenanceNode


class ProvenanceGraphTests(unittest.TestCase):
    def setUp(self):
        self.logger = MagicMock()
        self.graph = ProvenanceGraph(logger=self.logger)

    def test_node_creation_and_add_child(self):
        parent = ProvenanceNode(RetrieverType.USER, "x=1")
        child = ProvenanceNode(RetrieverType.USER, "y=2")
        parent.add_child(child)

        self.assertIn(child, parent.children)
        self.assertIn(parent, child.parents)

    def test_add_node_and_overwrite(self):
        node = ProvenanceNode(RetrieverType.USER, "code")
        added = self.graph.add_node(node)
        self.assertEqual(added, node)
        self.assertIn(node.id, self.graph.nodes)

        # Adding same node without overwrite should raise
        with self.assertRaises(ValueError):
            self.graph.add_node(node)

        # With overwrite=True, should succeed
        node.python_code = "new code"
        overwritten = self.graph.add_node(node, overwrite=True)
        self.assertEqual(overwritten.python_code, "new code")

    def test_connect_nodes(self):
        parent = ProvenanceNode(RetrieverType.USER, "p")
        child = ProvenanceNode(RetrieverType.USER, "c")
        self.graph.add_node(parent)
        self.graph.add_node(child)
        self.graph.connect(parent, child)

        self.assertIn(child, parent.children)
        self.logger.info.assert_called()

    def test_reset_for_materialization(self):
        node_user = ProvenanceNode(RetrieverType.USER, "u")
        node_web = ProvenanceNode(RetrieverType.WEB_SEARCH, "w")
        self.graph.add_node(node_user)
        self.graph.add_node(node_web)

        self.graph.reset_for_materialization()
        self.assertIn(node_user.id, self.graph.nodes)
        self.assertNotIn(node_web.id, self.graph.nodes)
        self.logger.info.assert_called()

    def test_get_node_by_id_and_filters(self):
        node = ProvenanceNode(RetrieverType.USER, "x")
        self.graph.add_node(node)

        self.assertEqual(self.graph.get_node_by_id(node.id), node)
        self.assertEqual(self.graph.get_node({"python_code": "x"}), node)
        self.assertEqual(self.graph.get_node({"python_code": "y"}), None)
        self.assertEqual(
            self.graph.get_nodes({"source_retriever": RetrieverType.USER}), [node]
        )

    def test_trace_upstream_downstream(self):
        n1 = ProvenanceNode(RetrieverType.USER, "a")
        n2 = ProvenanceNode(RetrieverType.USER, "b")
        n3 = ProvenanceNode(RetrieverType.USER, "c")
        n1.add_child(n2)
        n2.add_child(n3)

        self.graph.add_node(n1)
        self.graph.add_node(n2)
        self.graph.add_node(n3)

        upstream = self.graph.trace_upstream(n3)
        downstream = self.graph.trace_downstream(n1)

        self.assertEqual(upstream, [n2, n1])
        self.assertEqual(downstream, [n2, n3])

    def test_to_text_output(self):
        n1 = ProvenanceNode(RetrieverType.USER, "a")
        n2 = ProvenanceNode(RetrieverType.USER, "b")
        n1.add_child(n2)
        self.graph.add_node(n1)
        self.graph.add_node(n2)

        text = self.graph.to_text()
        self.assertIn("Node 1", text)
        self.assertIn("Node 2", text)
        self.assertIn("Python Code: a", text)
        self.assertIn("Python Code: b", text)

    def test_get_graph_visualization_returns_html(self):
        node = ProvenanceNode(RetrieverType.USER, "x=1")
        self.graph.add_node(node)
        html_output = self.graph.get_graph_visualization()
        self.assertTrue(
            html_output.startswith("<!DOCTYPE html>") or "<html" in html_output
        )


if __name__ == "__main__":
    unittest.main()
