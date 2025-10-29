# tests/pneuma_seeker/core/materializer/test_main.py
import logging
import os
import sys
from typing import Optional

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../src"))
)

import tempfile
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from pneuma_seeker.core.ir_system.data_model import (
    RetrieverType,
    Table,
    Text,
)
from pneuma_seeker.core.materializer.main import Materializer
from pneuma_seeker.model.llm_message import LLMMessage
from pneuma_seeker.model.option import EmbeddingModelOption, LLMOption
from pneuma_seeker.utils.config import Config


class MockLLM:
    """Simple deterministic LLM mock that returns queued JSON strings."""

    def __init__(self, responses=None):
        self._responses = list(responses or [])

    def chat(self, messages: list[LLMMessage], llm_option: Optional[LLMOption] = None):
        # return a list (chat API returns iterable); use last queued response or default
        if not self._responses:
            yield '{"step_type":"operation","name":"noop","args":{}}'
            return
        yield self._responses.pop(0)


class MockEmbedModel:
    def encode(
        self,
        texts: str | list[str],
        embed_model_option: EmbeddingModelOption = EmbeddingModelOption(),
    ):
        import numpy as _np

        return _np.ndarray(0)


class MaterializerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.logger = logging.getLogger("test_materializer")
        self.logger.setLevel(logging.ERROR)

        # Create mocks
        self.mock_llm = MockLLM()
        self.mock_embed_model = MockEmbedModel()
        self.mock_toolkit = MagicMock()
        self.mock_prov_graph = MagicMock()

        # Provide a config similar to other tests
        self.config = Config(".env.test")

        # Instantiate materializer with mocks
        self.materializer = Materializer(
            llm=self.mock_llm,  # type: ignore
            embed_model=self.mock_embed_model,  # type: ignore
            logger=self.logger,
            data_sources=[],
            prov_graph=self.mock_prov_graph,
            toolkit=self.mock_toolkit,
            config=self.config,
        )

    def tearDown(self):
        self.temp_dir.cleanup()
        patch.stopall()

    def test_pneuma_retriever_and_table_select_materializes_T(self):
        # LLM will ask to call pneuma_retriever then table_select to materialize t1
        plan1 = '{"step_type":"operation","name":"pneuma_retriever","args":{"prompt":"find tables"}}'
        plan2 = '{"step_type":"operation","name":"table_select","args":{"t1":{"id":"table1","columns":["a","b"]}}}'
        self.mock_llm._responses = [plan1, plan2]

        table_df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        table_doc = Table(
            doc_id="table1",
            retriever_type=RetrieverType.PNEUMA_RETRIEVER,
            content=table_df,
            metadata={},
        )

        # First call to retrieve_documents returns the table for pneuma_retriever
        self.mock_toolkit.retrieve_documents = MagicMock(return_value=[table_doc])

        # Define target T (schema only) so materializer knows it needs t1
        T = {"t1": pd.DataFrame(columns=["a", "b"])}

        result = self.materializer.materialize_T(T=T, column_descriptions={}, S="")

        self.assertIn("t1", result)
        pd.testing.assert_frame_equal(result["t1"].reset_index(drop=True), table_df)

    def test_web_search_sets_web_search_result(self):
        # LLM will call pneuma_retriever, web_search, then table_select to finish
        plan1 = '{"step_type":"operation","name":"pneuma_retriever","args":{"prompt":"find tables"}}'
        plan2 = (
            '{"step_type":"operation","name":"web_search","args":{"prompt":"query"}}'
        )
        plan3 = '{"step_type":"operation","name":"table_select","args":{"t1":{"id":"table1","columns":["a","b"]}}}'
        self.mock_llm._responses = [plan1, plan2, plan3]

        self.materializer.config.ENABLE_WEB_SEARCH = True

        table_df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        table_doc = Table(
            doc_id="table1",
            retriever_type=RetrieverType.PNEUMA_RETRIEVER,
            content=table_df,
            metadata={},
        )

        web_text = Text(
            doc_id="web_result_1",
            retriever_type=RetrieverType.WEB_SEARCH,
            content="This is a web search result.",
            metadata={},
        )

        # First call returns the table, second call returns the web result
        self.mock_toolkit.retrieve_documents = MagicMock(
            side_effect=[[table_doc], [web_text]]
        )

        T = {"t1": pd.DataFrame(columns=["a", "b"])}

        result = self.materializer.materialize_T(T=T, column_descriptions={}, S="")

        # After web_search operation the state should have web_search_result set
        self.assertIsNotNone(self.materializer.state.web_search_result)
        assert self.materializer.state.web_search_result is not None
        self.assertEqual(
            self.materializer.state.web_search_result.content,
            "This is a web search result.",
        )

        # Ensure final materialized result still contains t1
        self.assertIn("t1", result)

    def test_semantic_column_generator_adds_column(self):
        # LLM will call pneuma_retriever, semantic_column_generator, then table_select
        plan1 = '{"step_type":"operation","name":"pneuma_retriever","args":{"prompt":"find tables"}}'
        plan2 = '{"step_type":"operation","name":"semantic_column_generator","args":{"table_id":"table1","new_column_name":"newcol","relevant_columns":["b"],"instruction":"make new"}}'
        plan3 = '{"step_type":"operation","name":"table_select","args":{"t1":{"id":"table1","columns":["a","b","newcol"]}}}'
        self.mock_llm._responses = [plan1, plan2, plan3]

        table_df = pd.DataFrame({"a": [1, 2], "b": [10, 20]})
        table_doc = Table(
            doc_id="table1",
            retriever_type=RetrieverType.PNEUMA_RETRIEVER,
            content=table_df.copy(),
            metadata={},
        )

        self.mock_toolkit.retrieve_documents = MagicMock(return_value=[table_doc])

        # Mock generation of semantic column
        self.mock_toolkit.generate_semantic_column = MagicMock(return_value=[100, 200])

        T = {"t1": pd.DataFrame(columns=["a", "b", "newcol"])}

        result = self.materializer.materialize_T(T=T, column_descriptions={}, S="")

        self.assertIn("t1", result)
        res_df = result["t1"].reset_index(drop=True)
        self.assertIn("newcol", res_df.columns)
        self.assertEqual(list(res_df["newcol"]), [100, 200])


if __name__ == "__main__":
    unittest.main()
