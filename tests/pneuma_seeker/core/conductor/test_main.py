# tests/pneuma_seeker/core/conductor/test_main.py
import logging
import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../src"))
)

import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from pneuma_seeker.core.ir_system.data_model import (
    AbstractDocument,
    RetrieverType,
    Table,
    Text,
)
from pneuma_seeker.model.interface.impl.mock_embed_model import MockEmbedModel
from pneuma_seeker.model.interface.impl.mock_llm import MockLLM
from pneuma_seeker.utils.config import Config


class ConductorTests(unittest.TestCase):
    def setUp(self):
        import pneuma_seeker.core.conductor.main as conductor_mod

        self.mock_llm = MockLLM()
        self.mock_embed_model = MockEmbedModel()
        self.patcher_get_llm = patch.object(
            conductor_mod, "get_llm", lambda *a, **k: (lambda p, c, l: self.mock_llm)
        )
        self.patcher_get_embed = patch.object(
            conductor_mod,
            "get_embed_model",
            lambda *a, **k: (lambda p, c, l: self.mock_embed_model),
        )

        self.patcher_get_llm.start()
        self.patcher_get_embed.start()

        from pneuma_seeker.core.conductor.main import Conductor

        config = Config(".env.test")
        config.ENABLE_WEB_SEARCH = True

        self.logger = logging.getLogger("test_conductor")
        self.logger.setLevel(logging.ERROR)
        self.conductor = Conductor(
            llm_path="unused",
            embed_model_path="unused",
            logger=self.logger,
            data_sources=[],
            config=config,
        )

    def tearDown(self):
        patch.stopall()

    def test_pneuma_retriever_updates_retrieved_tables(self):
        plan1 = '{"action":"tool_call","tool":"pneuma_retriever","args":{"prompt":"find tables"}}'
        plan2 = '{"action":"communicate_with_user","message":"done"}'
        self.mock_llm._responses = [plan1, plan2]

        self.conductor.toolkit.retrieve_documents = MagicMock(
            return_value=[
                Table(
                    doc_id="table1",
                    retriever_type=RetrieverType.PNEUMA_RETRIEVER,
                    content=pd.DataFrame({"A": [1, 2], "B": [3, 4]}),
                    metadata={},
                )
            ]
        )

        gen = self.conductor.process_input(
            user_input="Find relevant tables",
            user_id="uX",
            chat_id="cX",
            interaction_history=[],
            external_table_paths=[],
        )
        responses = list(gen)
        self.assertIn(
            "done",
            responses[-1],
            "Expected final user-facing response to contain 'done'",
        )
        self.assertTrue(
            len(self.conductor.retrieved_tables) > 0,
            "retrieved_tables should have been updated",
        )

    def test_web_search_sets_web_search_result(self):
        plan1 = '{"action":"tool_call","tool":"web_search","args":{"prompt":"query"}}'
        plan2 = '{"action":"communicate_with_user","message":"web done"}'
        self.mock_llm._responses = [plan1, plan2]

        self.conductor.toolkit.retrieve_documents = MagicMock(
            return_value=[
                Text(
                    doc_id="web_result_1",
                    retriever_type=RetrieverType.WEB_SEARCH,
                    content="This is a web search result.",
                    metadata={},
                )
            ]
        )

        gen = self.conductor.process_input(
            user_input="Look up web",
            user_id="u1",
            chat_id="c1",
            interaction_history=[],
            external_table_paths=[],
        )
        responses = list(gen)
        self.assertIn("web done", responses[-1], "Expected web done in final response")
        self.assertIsNotNone(
            self.conductor.web_search_result,
            "web_search_result should be set after web_search call",
        )

    def test_table_enumerator_updates_enumerated_ids(self):
        plan1 = '{"action":"tool_call","tool":"table_enumerator","args":{"pattern":"pattern"}}'
        plan2 = '{"action":"communicate_with_user","message":"enum done"}'
        self.mock_llm._responses = [plan1, plan2]

        self.conductor.toolkit.retrieve_documents = MagicMock(
            return_value=[
                Table(
                    doc_id="table1",
                    retriever_type=RetrieverType.PNEUMA_RETRIEVER,
                    content=pd.DataFrame({"A": [1, 2], "B": [3, 4]}),
                    metadata={},
                )
            ]
        )

        gen = self.conductor.process_input(
            user_input="enumerate",
            user_id="u1",
            chat_id="c1",
            interaction_history=[],
            external_table_paths=[],
        )
        responses = list(gen)
        self.assertIn("enum done", responses[-1])
        self.assertIsInstance(self.conductor.enumerated_table_ids, list)

    def test_state_manipulation_sets_only_S(self):
        plan1 = """{"action":"tool_call","tool":"state_manipulation","args":{"S":"result = something"}}"""
        plan2 = '{"action":"communicate_with_user","message":"S set"}'
        self.mock_llm._responses = [plan1, plan2]

        gen = self.conductor.process_input(
            user_input="set S",
            user_id="u1",
            chat_id="c1",
            interaction_history=[],
            external_table_paths=[],
        )
        responses = list(gen)
        self.assertIn("S set", responses[-1])

        state = self.conductor.info_need_state
        self.assertEqual(state.S, "result = something")
        self.assertFalse(state.T)
        self.assertFalse(state.is_T_materialized)
        self.assertFalse(state.is_S_executed)
        self.assertEqual(state.column_descriptions, {})

    def test_state_manipulation_sets_only_T(self):
        plan1 = """{"action":"tool_call","tool":"state_manipulation","args":{"T":{"t1":["a","b"]},"column_descriptions":{"t1":{"a":"col a"}}}}"""
        plan2 = '{"action":"communicate_with_user","message":"T set"}'
        self.mock_llm._responses = [plan1, plan2]

        gen = self.conductor.process_input(
            user_input="set T",
            user_id="u1",
            chat_id="c1",
            interaction_history=[],
            external_table_paths=[],
        )
        responses = list(gen)
        self.assertIn("T set", responses[-1])

        state = self.conductor.info_need_state
        self.assertIn("t1", state.T)
        self.assertIsInstance(state.T["t1"], AbstractDocument)
        self.assertEqual(set(state.T["t1"].content.columns), {"a", "b"})
        self.assertEqual(state.column_descriptions, {"t1": {"a": "col a"}})
        self.assertEqual(state.S, "")
        self.assertFalse(state.is_T_materialized)
        self.assertFalse(state.is_S_executed)

    def test_state_manipulation_sets_S_and_T(self):
        plan1 = """{"action":"tool_call","tool":"state_manipulation","args":{"T":{"t1":["a","b"]},"column_descriptions":{"t1":{"a":"col a"}},"S":"result = something"}}"""
        plan2 = '{"action":"communicate_with_user","message":"state done"}'
        self.mock_llm._responses = [plan1, plan2]

        gen = self.conductor.process_input(
            user_input="set S and T",
            user_id="u1",
            chat_id="c1",
            interaction_history=[],
            external_table_paths=[],
        )
        responses = list(gen)

        self.assertIn("state done", responses[-1])

        state = self.conductor.info_need_state
        self.assertIn("t1", state.T)
        self.assertIsInstance(state.T["t1"], AbstractDocument)
        self.assertEqual(set(state.T["t1"].content.columns), {"a", "b"})
        self.assertEqual(state.column_descriptions, {"t1": {"a": "col a"}})
        self.assertEqual(state.S, "result = something")
        self.assertFalse(state.is_T_materialized)
        self.assertFalse(state.is_S_executed)

    def test_materializer_and_executor(self):
        plan1 = """{"action":"tool_call","tool":"state_manipulation","args":{"T":{"t1":["a","b"]},"column_descriptions":{"t1":{"a":"col a"}},"S":"result = something"}}"""
        plan2 = """{"action":"tool_call","tool":"materializer","args":{"note":""}}"""
        plan3 = """{"action":"tool_call","tool":"executor","args":{}}"""
        plan4 = '{"action":"communicate_with_user","message":"materialization and execution done"}'
        self.mock_llm._responses = [plan1, plan2, plan3, plan4]

        self.conductor.materializer.materialize_T = MagicMock(
            return_value={"t1": pd.DataFrame({"a": [1, 2], "b": [3, 4]})}
        )
        self.conductor.toolkit.execute_code = MagicMock(
            return_value={
                "exec_res": "ran:result = something",
                "used_table_ids": ["t1"],
            }
        )

        gen = self.conductor.process_input(
            user_input="materialize T",
            user_id="u1",
            chat_id="c1",
            interaction_history=[],
            external_table_paths=[],
        )
        responses = list(gen)
        self.assertIn("materialization and execution done", responses[-1])

        self.assertTrue(
            self.conductor.info_need_state.is_T_materialized,
            "T should be marked as materialized",
        )
        self.assertTrue(
            self.conductor.info_need_state.is_S_executed,
            "S should be marked as executed",
        )
        self.assertEqual(self.conductor.info_need_state.T["t1"].content.shape, (2, 2))
        self.assertEqual(
            list(self.conductor.info_need_state.T["t1"].content["a"]), [1, 2]
        )
        self.assertEqual(
            list(self.conductor.info_need_state.T["t1"].content["b"]), [3, 4]
        )

    def test_categorical_column_info_produces_expected_string(self):
        df = pd.DataFrame({"A": [1, 2, 3], "B": ["x", "x", "y"]})
        self.conductor.retrieved_tables = [
            Table(
                doc_id="table1",
                retriever_type=RetrieverType.PNEUMA_RETRIEVER,
                content=df,
                metadata={},
            )
        ]

        plan1 = """{"action":"tool_call","tool":"categorical_column_info","args":{"id":"table1","columns":["B"]}}"""
        plan2 = '{"action":"communicate_with_user","message":"info provided"}'
        self.mock_llm._responses = [plan1, plan2]

        gen = self.conductor.process_input(
            user_input="materialize T",
            user_id="u1",
            chat_id="c1",
            interaction_history=[],
            external_table_paths=[],
        )
        responses = list(gen)
        self.assertIn("info provided", responses[-1])  # Expected info: "B: x, y\n"

    def test_external_table_upload_creates_provenance_node(self):
        """Tests that uploading an external table results in a new provenance node."""
        import tempfile

        df = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        tmp_path = tmp.name
        tmp.close()
        df.to_csv(tmp_path, index=False)

        uploaded_table = Table(
            doc_id="uploaded_table_1",
            retriever_type=RetrieverType.USER,
            content=pd.DataFrame(),
            metadata={},
            path=tmp_path,
        )
        self.conductor.table_reader.process_external_tables = MagicMock(
            return_value=[uploaded_table]
        )

        self.mock_llm._responses = [
            '{"action":"communicate_with_user","message":"External data read successfuly."}'
        ]

        gen = self.conductor.process_input(
            user_input="upload",
            user_id="u1",
            chat_id="c1",
            interaction_history=[],
            external_table_paths=[tmp_path],
        )
        list(gen)

        self.assertTrue(len(self.conductor.prov_graph.nodes) == 2)
        prov_graph_code_lines = [
            self.conductor.prov_graph.ROOT_NODE_CODE,
            self.conductor.toolkit.generate_read_external_tables_code(
                1, uploaded_table
            ),
        ]
        expected_prov_graph_code_concat = "\n\n".join(prov_graph_code_lines)
        self.assertEqual(
            expected_prov_graph_code_concat,
            self.conductor.prov_graph.get_graph_code_concatenation(),
        )


if __name__ == "__main__":
    unittest.main()
