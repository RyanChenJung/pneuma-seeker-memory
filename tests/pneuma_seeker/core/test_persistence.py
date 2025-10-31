import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../src"))
)

import duckdb

from pneuma_seeker.core.conductor.main import (
    AbstractDocument,
    InformationNeedState,
    RetrieverType,
)
from pneuma_seeker.core.persistence import (
    _deserialize_provenance_graph,
    _serialize_provenance_graph,
    init_db,
    load_state,
    save_state,
)
from pneuma_seeker.provenance.graph import ProvenanceGraph, ProvenanceNode


class PersistenceTests(unittest.TestCase):
    """Tests for persistence of info need state, retrieval results, and provenance graph."""

    def setUp(self):
        self.db_path = "pneuma_seeker_test.duckdb"
        self.logger = MagicMock()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_init_db_creates_table(self):
        """Tests that init_db creates the chat_state table."""

        # Should not raise and the table should exist (querying it should work)
        init_db(self.db_path)
        con = duckdb.connect(self.db_path)
        # Table exists, selecting should return zero rows
        rows = con.execute("SELECT count(*) FROM chat_state").fetchone()
        con.close()
        self.assertIsNotNone(rows)

    def test_save_and_load_provenance_graph_roundtrip(self):
        """Tests saving and loading a provenance graph."""
        init_db(self.db_path)

        info_state = InformationNeedState()
        retrieval_results = {}
        enumerated_table_ids = ["tbl_1"]

        # build a small provenance graph with parent->child
        graph = ProvenanceGraph(logger=self.logger)
        p = ProvenanceNode(RetrieverType.USER, "pcode", "")
        c = ProvenanceNode(RetrieverType.USER, "ccode", "")
        p.add_child(c)
        graph.add_node(p)
        graph.add_node(c)

        save_state(
            user_id="u1",
            chat_id="c1",
            info_need_state=info_state,
            retrieval_results=retrieval_results,
            enumerated_table_ids=enumerated_table_ids,
            provenance_graph=graph,
        )

        loaded_info_state, loaded_retrievals, loaded_enumerated, loaded_graph = (
            load_state("u1", "c1", self.logger)
        )

        # enumerated_table_ids round-trip
        self.assertEqual(loaded_enumerated, enumerated_table_ids)

        # provenance graph nodes preserved
        self.assertEqual(set(loaded_graph.nodes.keys()), set(graph.nodes.keys()))
        # edges preserved: child of p should be c
        loaded_p = loaded_graph.get_node_by_id(p.id)
        self.assertIsNotNone(loaded_p)
        if loaded_p is not None:
            self.assertIn(c.id, [ch.id for ch in loaded_p.children])

    def test_save_and_load_retrieval_results_roundtrip(self):
        """Tests saving and loading retrieval results with AbstractDocuments."""
        init_db(self.db_path)

        info_state = InformationNeedState()

        # Create a simple AbstractDocument with inline content (no path)
        doc = AbstractDocument(
            doc_id="doc1",
            retriever_type=RetrieverType.USER,
            content="inline content",
            metadata={"k": "v"},
            path=None,
            last_node_id=None,
        )

        retrieval_results = {RetrieverType.USER: [doc]}

        graph = ProvenanceGraph(logger=self.logger)

        save_state(
            user_id="u2",
            chat_id="c2",
            info_need_state=info_state,
            retrieval_results=retrieval_results,
            enumerated_table_ids=[],
            provenance_graph=graph,
        )

        _, loaded_retrievals, _, _ = load_state("u2", "c2", self.logger)

        self.assertIn(RetrieverType.USER, loaded_retrievals)
        loaded_docs = loaded_retrievals[RetrieverType.USER]
        self.assertEqual(len(loaded_docs), 1)
        self.assertEqual(loaded_docs[0].doc_id, "doc1")
        self.assertEqual(loaded_docs[0].metadata, {"k": "v"})

    def test_serialize_deserialize_provenance_graph_helpers(self):
        """Tests the provenance graph serialization and deserialization helpers."""
        graph = ProvenanceGraph(logger=self.logger)
        n1 = ProvenanceNode(RetrieverType.USER, "x=1", "")
        n2 = ProvenanceNode(RetrieverType.WEB_SEARCH, "y=2", "")
        n1.add_child(n2)
        graph.add_node(n1)
        graph.add_node(n2)

        obj = _serialize_provenance_graph(graph)
        self.assertIn("nodes", obj)
        des = _deserialize_provenance_graph(obj, self.logger)
        self.assertEqual(set(des.nodes.keys()), set(graph.nodes.keys()))
        dn1 = des.get_node_by_id(n1.id)
        self.assertIsNotNone(dn1)
        if dn1 is not None:
            self.assertIn(n2.id, [c.id for c in dn1.children])


if __name__ == "__main__":
    unittest.main()
