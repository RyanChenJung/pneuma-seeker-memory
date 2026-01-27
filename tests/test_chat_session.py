import os
import sys
import types
import unittest
from unittest.mock import MagicMock

from pandas import DataFrame

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import pneuma_seeker.chat_session as chat_session_mod
from pneuma_seeker.provenance.graph import ProvenanceGraph, ProvenanceNode
from pneuma_seeker.shared.schemas.core.conductor import InformationNeedState
from pneuma_seeker.shared.schemas.core.ir_system import RetrieverType, Table
from pneuma_seeker.shared.config import Config
from pneuma_seeker.shared.schemas.language_model.message import LLMMessage


class DummyConductor:
    def __init__(self, user_id, chat_id, config, logger, prov_graph_obj, db_api, lm_api):
        self.user_id = user_id
        self.chat_id = chat_id
        self.config = config
        self.logger = logger
        # set placeholders that ChatSession may use
        self.info_need_state = {"state": "ok"}
        self.retrieved_tables = []
        self.enumerated_table_ids = []
        self.prov_graph = types.SimpleNamespace(nodes={})
        self.db_api = db_api
        self.lm_api = lm_api

    def chat(self, last_content, interaction_history, external_data_paths):
        # Echo back a couple items based on last_content
        yield f"resp:{last_content}"
        yield "final"


class ChatSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        # Patch Conductor, load_state and save_state inside the chat_session module
        self._orig_conductor = getattr(chat_session_mod, "Conductor", None)
        self._orig_load = getattr(chat_session_mod, "load_state", None)
        self._orig_save = getattr(chat_session_mod, "save_state", None)
        self._orig_prov = getattr(chat_session_mod, "ProvenanceGraph", None)

        chat_session_mod.Conductor = DummyConductor
        chat_session_mod.load_state = lambda user_id, chat_id, logger, src: (
            {"state": "ok"},
            [],
            [],
            types.SimpleNamespace(nodes={}),
        )
        chat_session_mod.save_state = MagicMock()
        chat_session_mod.ProvenanceGraph = lambda logger: types.SimpleNamespace()

        self.cfg = Config()
        self.logger = MagicMock()
        self.db_api = MagicMock()
        self.lm_api = MagicMock()

    def tearDown(self) -> None:
        # restore
        if self._orig_conductor is not None:
            chat_session_mod.Conductor = self._orig_conductor
        if self._orig_load is not None:
            chat_session_mod.load_state = self._orig_load
        if self._orig_save is not None:
            chat_session_mod.save_state = self._orig_save
        if self._orig_prov is not None:
            chat_session_mod.ProvenanceGraph = self._orig_prov

    def test_chat_yields_conductor_responses_and_done(self):
        cs = chat_session_mod.ChatSession(
            "u1",
            "c1",
            self.cfg,
            self.logger,
            self.db_api,
            self.lm_api,
        )
        messages = [LLMMessage(role="user", content="hello")]
        out = list(cs.chat(messages))
        # Should include two responses from DummyConductor and a final DONE
        self.assertIn("resp:hello", out)
        self.assertIn("final", out)
        self.assertIn("DONE", out)

    def test_persist_session_calls_save_state(self):
        cs = chat_session_mod.ChatSession(
            "u2",
            "c2",
            self.cfg,
            self.logger,
            self.db_api,
            self.lm_api,
        )
        # populate conductor.prov_graph.nodes to simulate content
        cs.conductor.prov_graph.nodes = {
            "n1": ProvenanceNode(
                source_retriever=RetrieverType.USER, python_code="code", description=""
            )
        }
        cs.conductor.info_need_state = InformationNeedState()
        cs.conductor.retrieved_tables = [
            Table(
                doc_id="doc1",
                retriever_type=RetrieverType.PNEUMA_RETRIEVER,
                content=DataFrame(),
                metadata={},
            )
        ]
        cs.conductor.enumerated_table_ids = ["id1"]

        # call persist
        cs.persist_session()

        # ensure save_state was called
        self.assertTrue(chat_session_mod.save_state.called)
        args = chat_session_mod.save_state.call_args[0]
        # expected args: user_id, chat_id, info_need_state, retrieved_tables, enumerated_table_ids, prov_graph
        self.assertEqual(args[0], "u2")
        self.assertEqual(args[1], "c2")


if __name__ == "__main__":
    unittest.main()
