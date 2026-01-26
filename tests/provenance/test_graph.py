# tests/pneuma_seeker/provenance/test_graph.py
import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src"))
)

from pneuma_seeker.shared.schemas.core.ir_system import RetrieverType
from pneuma_seeker.provenance.graph import ProvenanceGraph, ProvenanceNode


class ProvenanceGraphTests(unittest.TestCase):
    def setUp(self):
        self.logger = MagicMock()
        self.graph = ProvenanceGraph(logger=self.logger)

    def test_node_creation_and_add_child(self):
        """Tests ProvenanceNode creation and adding child nodes."""
        parent = ProvenanceNode(RetrieverType.USER, "x=1", "")
        child = ProvenanceNode(RetrieverType.USER, "y=2", "")
        parent.add_child(child)
        self.assertIn(child, parent.children)
        self.assertIn(parent, child.parents)

    def test_add_node_and_overwrite(self):
        """Tests adding nodes to the ProvenanceGraph and overwriting existing nodes."""
        node = ProvenanceNode(RetrieverType.USER, "code", "")
        added = self.graph.add_node(node)
        self.assertEqual(added, node)
        self.assertIn(node.id, self.graph.nodes)

        with self.assertRaises(ValueError):
            self.graph.add_node(node)

        node.python_code = "new code"
        overwritten = self.graph.add_node(node, overwrite=True)
        self.assertEqual(overwritten.python_code, "new code")

    def test_connect_nodes(self):
        """Tests connecting two nodes in the ProvenanceGraph."""
        parent = ProvenanceNode(RetrieverType.USER, "p", "")
        child = ProvenanceNode(RetrieverType.USER, "c", "")
        self.graph.add_node(parent)
        self.graph.add_node(child)
        self.graph.connect(parent, child)
        self.assertIn(child, parent.children)
        self.assertIn(parent, child.parents)
        self.logger.info.assert_called()

    def test_reset_for_materialization(self):
        """Tests resetting the graph for materialization."""
        node_user = ProvenanceNode(RetrieverType.USER, "u", "")
        node_web = ProvenanceNode(RetrieverType.WEB_SEARCH, "w", "")
        self.graph.add_node(node_user)
        self.graph.add_node(node_web)
        self.graph.reset_for_materialization()
        self.assertIn(node_user.id, self.graph.nodes)
        self.assertNotIn(node_web.id, self.graph.nodes)
        self.logger.info.assert_called()

    def test_get_node_by_id_and_filters(self):
        """Tests retrieving nodes by ID and filters."""
        node = ProvenanceNode(RetrieverType.USER, "x", "")
        self.graph.add_node(node)
        self.assertEqual(self.graph.get_node_by_id(node.id), node)
        self.assertEqual(self.graph.get_node({"python_code": "x"}), node)
        self.assertIsNone(self.graph.get_node({"python_code": "y"}))
        user_nodes = self.graph.get_nodes({"source_retriever": RetrieverType.USER})
        self.assertIn(node, user_nodes)

    def test_trace_upstream_downstream(self):
        """Tests tracing upstream and downstream nodes."""
        n1 = ProvenanceNode(RetrieverType.USER, "a", "")
        n2 = ProvenanceNode(RetrieverType.USER, "b", "")
        n3 = ProvenanceNode(RetrieverType.USER, "c", "")
        n1.add_child(n2)
        n2.add_child(n3)
        self.graph.add_node(n1)
        self.graph.add_node(n2)
        self.graph.add_node(n3)
        upstream = self.graph.trace_upstream(n3)
        downstream = self.graph.trace_downstream(n1)
        self.assertEqual(set(upstream), {n1, n2})
        self.assertEqual(set(downstream), {n2, n3})

    def test_to_text_output(self):
        """Tests the textual representation of the ProvenanceGraph."""
        n1 = ProvenanceNode(RetrieverType.USER, "a", "")
        n2 = ProvenanceNode(RetrieverType.USER, "b", "")
        n1.add_child(n2)
        self.graph.add_node(n1)
        self.graph.add_node(n2)
        text = self.graph.to_text()
        self.assertIn(n1.id, text)
        self.assertIn(n2.id, text)
        self.assertIn("Python Code: a", text)
        self.assertIn("Python Code: b", text)

    def test_get_graph_visualization_returns_html(self):
        """Tests that get_graph_visualization returns valid HTML output."""
        node = ProvenanceNode(RetrieverType.USER, "x=1", "")
        self.graph.add_node(node)
        html_output = self.graph.get_graph_visualization()
        self.assertTrue(html_output.strip().startswith("<!DOCTYPE html>") or "<html" in html_output)

    def test_get_graph_explanation(self):
        """Tests the textual explanation returned by get_graph_explanation."""
        # Create a used data node and a processing (materializer) node
        used_node = ProvenanceNode(RetrieverType.WEB_SEARCH, "df = load_data()", "")
        materializer_node = ProvenanceNode(RetrieverType.MATERIALIZER, "result = process(df)", "")

        # Add nodes and connect them so the used node has downstream usage
        self.graph.add_node(used_node)
        self.graph.add_node(materializer_node)
        self.graph.connect(used_node, materializer_node)

        link = "http://example.com/script.py"
        explanation = self.graph.get_graph_explanation(link)

        # The script download link should be present
        self.assertIn(link, explanation)

        # The used data python code should appear in a code block
        self.assertIn(f"```python\n{used_node.python_code}\n```", explanation)

        # The materializer node should be listed as a processing step
        self.assertIn("Step 1", explanation)
        self.assertIn(materializer_node.python_code, explanation)

        # The default root node code should not be listed under used data
        self.assertNotIn(self.graph.ROOT_NODE_CODE, explanation)

    def test_get_graph_code_concatenation_simple(self):
        """Tests simple linear graph code concatenation."""
        # Simple linear DAG: n1 -> n2 -> n3
        n1 = ProvenanceNode(RetrieverType.USER, "code_a", "")
        n2 = ProvenanceNode(RetrieverType.USER, "code_b", "")
        n3 = ProvenanceNode(RetrieverType.USER, "code_c", "")
        n1.add_child(n2)
        n2.add_child(n3)
        self.graph.add_node(n1)
        self.graph.add_node(n2)
        self.graph.add_node(n3)

        concat = self.graph.get_graph_code()
        expected = "code_a\n\ncode_b\n\ncode_c"
        self.assertTrue(concat.endswith(expected))

    def test_get_graph_code_concatenation_skips_empty_and_preserves_order(self):
        """Tests that empty python_code nodes are skipped and order is preserved."""
        # n1 -> n2(empty) and n1 -> n3 ; empty python_code should be skipped
        n1 = ProvenanceNode(RetrieverType.USER, "first", "")
        n2 = ProvenanceNode(RetrieverType.USER, "", "")
        n3 = ProvenanceNode(RetrieverType.USER, "third", "")
        n1.add_child(n2)
        n1.add_child(n3)
        self.graph.add_node(n1)
        self.graph.add_node(n2)
        self.graph.add_node(n3)

        concat = self.graph.get_graph_code()
        # n1 should appear before n3 since it's the parent; n2 is skipped
        self.assertIn("first", concat)
        self.assertIn("third", concat)
        self.assertTrue(concat.index("first") < concat.index("third"))

    def test_get_graph_code_concatenation_detects_cycle_and_logs(self):
        """Tests that cycles in the graph are detected and logged."""
        # Create a cycle n1 -> n2 -> n3 -> n1. In this case there will be no
        # node with indegree 0 so Kahn's algorithm will detect a cycle and
        # return an empty concatenation while issuing a warning.
        n1 = ProvenanceNode(RetrieverType.USER, "a", "")
        n2 = ProvenanceNode(RetrieverType.USER, "b", "")
        n3 = ProvenanceNode(RetrieverType.USER, "c", "")
        n1.add_child(n2)
        n2.add_child(n3)
        n3.add_child(n1)
        self.graph.add_node(n1)
        self.graph.add_node(n2)
        self.graph.add_node(n3)

        concat = self.graph.get_graph_code()
        # The default root node is still present and will be included even
        # when the rest of the graph forms a cycle. Kahn's algorithm will
        # process the root then detect the cycle among the remaining nodes.
        self.assertTrue(concat.endswith("tables: dict[str, pd.DataFrame] = {}"))
        self.logger.warning.assert_called()

    def test_add_node_invalid_type_raises(self):
        """Adding a non-ProvenanceNode should raise ValueError."""
        with self.assertRaises(ValueError):
            self.graph.add_node("not a node") # type: ignore

    def test_connect_invalid_types_raise(self):
        """Connecting non-ProvenanceNode objects should raise ValueError."""
        n = ProvenanceNode(RetrieverType.USER, "a", "")
        with self.assertRaises(ValueError):
            self.graph.connect("not a node", n) # type: ignore
        with self.assertRaises(ValueError):
            self.graph.connect(n, "not a node") # type: ignore

    def test_topological_sort_branching_order(self):
        """Branching DAG should preserve parent-before-child ordering."""
        parent = ProvenanceNode(RetrieverType.USER, "p", "")
        child1 = ProvenanceNode(RetrieverType.USER, "c1", "")
        child2 = ProvenanceNode(RetrieverType.USER, "c2", "")
        parent.add_child(child1)
        parent.add_child(child2)
        self.graph.add_node(parent)
        self.graph.add_node(child1)
        self.graph.add_node(child2)

        ordered = self.graph.topological_sort()
        ids = [n.id for n in ordered]
        self.assertTrue(ids.index(parent.id) < ids.index(child1.id))
        self.assertTrue(ids.index(parent.id) < ids.index(child2.id))

    def test_trace_include_self(self):
        """trace_upstream/downstream should include the node when requested."""
        a = ProvenanceNode(RetrieverType.USER, "a", "")
        b = ProvenanceNode(RetrieverType.USER, "b", "")
        a.add_child(b)
        self.graph.add_node(a)
        self.graph.add_node(b)

        up_with_self = set(self.graph.trace_upstream(b, include_self=True))
        self.assertIn(a, up_with_self)
        self.assertIn(b, up_with_self)

    def test_get_nodes_multi_filter(self):
        """get_nodes should support filtering by multiple attributes."""
        node = ProvenanceNode(RetrieverType.USER, "unique_code", "desc")
        self.graph.add_node(node)
        result = self.graph.get_nodes({"python_code": "unique_code", "source_retriever": RetrieverType.USER})
        self.assertIn(node, result)

    def test_reset_for_materialization_cleans_edges(self):
        """reset_for_materialization should remove non-USER nodes and strip edges to them."""
        user_node = ProvenanceNode(RetrieverType.USER, "u", "")
        non_user = ProvenanceNode(RetrieverType.WEB_SEARCH, "w", "")
        non_user.add_child(user_node)
        self.graph.add_node(user_node)
        self.graph.add_node(non_user)

        # Ensure the parent relationship exists before reset
        self.assertIn(non_user, user_node.parents)

        self.graph.reset_for_materialization()

        # non_user should be removed
        self.assertNotIn(non_user.id, self.graph.nodes)

        # user_node should remain, but should no longer have the non-user parent
        kept = self.graph.get_node_by_id(user_node.id)
        self.assertIsNotNone(kept)
        self.assertEqual(kept.parents, []) # type: ignore

if __name__ == "__main__":
    unittest.main()
