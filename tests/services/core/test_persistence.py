# tests/unit/core/test_persistence.py
import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../src"))
)

import duckdb
import pandas as pd

from pneuma_seeker.services.core.conductor.state import InformationNeedState
from pneuma_seeker.services.core.ir_system.data_model import AbstractDocument, RetrieverType
from pneuma_seeker.services.core.persistence import (
    _deserialize_provenance_graph,
    _serialize_provenance_graph,
    init_db,
    load_state,
    save_state,
)
from pneuma_seeker.provenance.graph import ProvenanceGraph, ProvenanceNode


class PersistenceTests(unittest.TestCase):
    """Tests for persistence of InformationNeedState, retrieval results, and provenance graph."""

    def setUp(self):
        self.db_path = "pneuma_seeker_test.duckdb"
        self.logger = MagicMock()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_init_db_creates_table(self):
        """Tests that init_db creates the chat_state table."""
        init_db(self.db_path)
        con = duckdb.connect(self.db_path)
        # Table should exist
        tables = con.execute("SHOW TABLES").fetchdf()
        con.close()
        self.assertIn("chat_state", tables["name"].tolist())

    def test_save_and_load_provenance_graph_roundtrip(self):
        """Tests saving and loading a provenance graph."""
        init_db(self.db_path)

        info_state = InformationNeedState()
        retrieved_tables = []
        enumerated_table_ids = ["tbl_1"]

        # Build a simple provenance graph
        graph = ProvenanceGraph(logger=self.logger, create_default_root=False)
        parent = ProvenanceNode(RetrieverType.USER, "print('parent')", "Parent node")
        child = ProvenanceNode(RetrieverType.USER, "print('child')", "Child node")
        parent.add_child(child)
        graph.add_node(parent)
        graph.add_node(child)

        # Save state
        save_state(
            user_id="u1",
            chat_id="c1",
            info_need_state=info_state,
            retrieved_tables=retrieved_tables,
            enumerated_table_ids=enumerated_table_ids,
            provenance_graph=graph,
            db_path=self.db_path,
        )

        # Load state
        loaded_info_state, loaded_retrievals, loaded_enumerated, loaded_graph = (
            load_state("u1", "c1", self.logger, db_path=self.db_path)
        )

        # Enumerated table IDs round-trip
        self.assertEqual(loaded_enumerated, enumerated_table_ids)

        # Graph node structure preserved
        self.assertEqual(set(loaded_graph.nodes.keys()), set(graph.nodes.keys()))

        loaded_parent = loaded_graph.get_node_by_id(parent.id)
        self.assertIsNotNone(loaded_parent)
        if loaded_parent is not None:
            self.assertIn(child.id, [c.id for c in loaded_parent.children])

    def test_save_and_load_retrieved_tables_roundtrip(self):
        """Tests saving and loading retrieved tables with inline AbstractDocuments."""
        init_db(self.db_path)

        info_state = InformationNeedState()

        # Create inline AbstractDocument (no file path)
        doc = AbstractDocument(
            doc_id="doc_inline",
            retriever_type=RetrieverType.USER,
            content=pd.DataFrame({"a": [1, 2], "b": [3, 4]}),
            metadata={"source": "unit-test"},
            path=None,
            last_node_id=None,
        )

        retrieved_tables = [doc]
        graph = ProvenanceGraph(logger=self.logger, create_default_root=False)

        save_state(
            user_id="u2",
            chat_id="c2",
            info_need_state=info_state,
            retrieved_tables=retrieved_tables,
            enumerated_table_ids=[],
            provenance_graph=graph,
            db_path=self.db_path,
        )

        _, loaded_retrievals, _, _ = load_state(
            "u2", "c2", self.logger, db_path=self.db_path
        )

        # There should be one retrieved AbstractDocument
        self.assertEqual(len(loaded_retrievals), 1)
        loaded_doc = loaded_retrievals[0]
        self.assertEqual(loaded_doc.doc_id, "doc_inline")
        self.assertEqual(loaded_doc.retriever_type, RetrieverType.USER)
        self.assertEqual(loaded_doc.metadata, {"source": "unit-test"})

        # Ensure DataFrame content preserved
        self.assertIsInstance(loaded_doc.content, pd.DataFrame)
        self.assertListEqual(list(loaded_doc.content.columns), ["a", "b"])
        self.assertEqual(len(loaded_doc.content), 2)

    def test_serialize_deserialize_provenance_graph_helpers(self):
        """Tests provenance graph (de)serialization helpers directly."""
        graph = ProvenanceGraph(logger=self.logger, create_default_root=False)
        n1 = ProvenanceNode(RetrieverType.USER, "x=1", "desc1")
        n2 = ProvenanceNode(RetrieverType.WEB_SEARCH, "y=2", "desc2")
        n1.add_child(n2)
        graph.add_node(n1)
        graph.add_node(n2)

        serialized = _serialize_provenance_graph(graph)
        self.assertIn("nodes", serialized)

        deserialized = _deserialize_provenance_graph(serialized, self.logger)
        self.assertEqual(set(deserialized.nodes.keys()), set(graph.nodes.keys()))

        d_n1 = deserialized.get_node_by_id(n1.id)
        self.assertIsNotNone(d_n1)
        if d_n1 is not None:
            self.assertIn(n2.id, [c.id for c in d_n1.children])
