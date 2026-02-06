import os
import sys
import types
import unittest
from unittest.mock import MagicMock


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import pneuma_seeker.chat_session as chat_session_mod
from pneuma_seeker.shared.config import Config
from pneuma_seeker.shared.schemas.language_model.message import LLMMessage


class DummyConductor:
    def __init__(
        self, user_id, chat_id, config, logger, prov_graph_obj, db_api, lm_api
    ):
        self.user_id = user_id
        self.chat_id = chat_id
        self.config = config
        self.logger = logger
        # set placeholders that ChatSession may use
        self.info_need_state = {"state": "ok"}
        self.retrieved_tables = []
        self.enumerated_tables = []
        self.prov_graph = types.SimpleNamespace(nodes={})
        self.db_api = db_api
        self.lm_api = lm_api

    def chat(self, last_content, interaction_history, external_data_paths):
        # Echo back a couple items based on last_content
        yield f"resp:{last_content}"
        yield "final"


class ChatSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        # Patch Conductor, load_state and persist_session inside the chat_session module
        self._orig_conductor = getattr(chat_session_mod, "Conductor", None)
        self._orig_prov = getattr(chat_session_mod, "ProvenanceGraph", None)

        chat_session_mod.Conductor = DummyConductor
        chat_session_mod.ProvenanceGraph = lambda logger: types.SimpleNamespace()

        self.cfg = Config()
        self.cfg.PERSIST_CHAT_SESSION = False
        self.logger = MagicMock()
        self.db_api = MagicMock()
        self.lm_api = MagicMock()
        self.db_api.load_state = MagicMock(
            return_value=(
                {"state": "ok"},
                [],
                [],
                types.SimpleNamespace(nodes={}),
            )
        )
        self.db_api.persist_session = MagicMock()

    def tearDown(self) -> None:
        # restore
        if self._orig_conductor is not None:
            chat_session_mod.Conductor = self._orig_conductor
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


if __name__ == "__main__":
    unittest.main()
