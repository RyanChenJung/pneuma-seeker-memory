# tests/pneuma_seeker/core/materializer/test_main.py
import logging
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../src"))
)
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from pneuma_seeker.provenance.graph import ProvenanceGraph
from pneuma_seeker.services.core.api.db import DBAPI
from pneuma_seeker.services.core.api.language_model import LanguageModelAPI
from pneuma_seeker.services.core.materializer.main import Materializer
from pneuma_seeker.services.core.toolkit.main import Toolkit
from pneuma_seeker.shared.config import Config
from pneuma_seeker.shared.schemas.core.ir_system import RetrieverType, Table, Text


class MaterializerTests(unittest.TestCase):
    def setUp(self):
        self.logger = logging.getLogger("test_materializer")
        self.logger.setLevel(logging.ERROR)
        self.config = Config(".env.test")
        self.prov_graph = ProvenanceGraph(self.logger)

        self.tmpdir = tempfile.mkdtemp()
        dataset_db_path = Path(os.path.join(self.tmpdir, "datasets"))
        workspace_db_path = Path(os.path.join(self.tmpdir, "workspaces"))

        self.config.ENABLE_WEB_SEARCH = True
        self.config.ENABLE_WEB_CRAWL = True
        self.config.LLM_PATH = "mock"
        self.config.EMBED_MODEL_PATH = "mock"

        self.db_api = DBAPI(
            self.config, self.logger, str(dataset_db_path), str(workspace_db_path)
        )
        self.lm_api = LanguageModelAPI(self.config, self.logger)

        self.toolkit = Toolkit(
            self.config,
            self.logger,
            self.prov_graph,
            self.db_api,
            self.lm_api,
        )

        self.materializer = Materializer(
            user_id="uX",
            chat_id="cX",
            config=self.config,
            logger=self.logger,
            prov_graph=self.prov_graph,
            toolkit=self.toolkit,
            db_api=self.db_api,
            language_model_api=self.lm_api,
        )

    def tearDown(self):
        patch.stopall()

    def test_pneuma_retriever_and_table_select_materializes_T(self):
        # LLM will ask to call pneuma_retriever then table_select to materialize t1
        plan1 = '{"action_type":"operation","name":"pneuma_retriever","args":{"prompt":"find tables"}}'
        plan2 = '{"action_type":"operation","name":"table_select","args":{"t1":{"id":"table_1","columns":["a","b"]}}}'
        self.lm_api.llm._responses = [plan1, plan2]  # type: ignore

        table_df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        table_doc = Table(
            doc_id="table_1",
            retriever_type=RetrieverType.PNEUMA_RETRIEVER,
            content=table_df,
            metadata={},
        )

        # First call to retrieve_documents returns the table for pneuma_retriever
        self.toolkit.retrieve_documents = MagicMock(return_value=[table_doc])

        # Define target T (schema only) so materializer knows it needs t1
        T = {"t1": pd.DataFrame(columns=["a", "b"])}

        result = self.materializer.materialize_T(T=T, column_descriptions={}, S="")

        self.assertIn("t1", result)
        pd.testing.assert_frame_equal(result["t1"].reset_index(drop=True), table_df)

        self.assertTrue(len(self.materializer.prov_graph.nodes) == 3)
        prov_graph_code_lines = [
            self.materializer.prov_graph.ROOT_NODE_CODE,
            self.toolkit.generate_pandas_read_csv_code(table_doc),
            self.toolkit.generate_table_select_code("t1", "table_1", ["a", "b"]),
        ]
        self.assertEqual(
            "\n\n".join(prov_graph_code_lines),
            self.materializer.prov_graph.get_graph_code(),
        )

    def test_web_search_sets_web_search_result(self):
        # LLM will call pneuma_retriever, web_search, then table_select to finish
        plan1 = '{"action_type":"operation","name":"pneuma_retriever","args":{"prompt":"find tables"}}'
        plan2 = (
            '{"action_type":"operation","name":"web_search","args":{"prompt":"query"}}'
        )
        plan3 = '{"action_type":"operation","name":"table_select","args":{"t1":{"id":"table_1","columns":["a","b"]}}}'
        self.lm_api.llm._responses = [plan1, plan2, plan3]  # type: ignore

        table_df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        table_doc = Table(
            doc_id="table_1",
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
        self.toolkit.retrieve_documents = MagicMock(
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

        self.assertTrue(len(self.materializer.prov_graph.nodes) == 4)
        prov_graph_code_lines_1 = [
            self.materializer.prov_graph.ROOT_NODE_CODE,
            self.toolkit.generate_pandas_read_csv_code(table_doc),
            self.toolkit.generate_view_textual_document_code(web_text),
            self.toolkit.generate_table_select_code("t1", "table_1", ["a", "b"]),
        ]
        prov_graph_code_lines_2 = [
            self.materializer.prov_graph.ROOT_NODE_CODE,
            self.toolkit.generate_view_textual_document_code(web_text),
            self.toolkit.generate_pandas_read_csv_code(table_doc),
            self.toolkit.generate_table_select_code("t1", "table_1", ["a", "b"]),
        ]
        self.assertIn(
            self.materializer.prov_graph.get_graph_code(),
            (
                "\n\n".join(prov_graph_code_lines_1),
                "\n\n".join(prov_graph_code_lines_2),
            ),
        )

    def test_web_crawl_sets_web_crawl_result(self):
        # LLM will call pneuma_retriever, web_crawl, then table_select to finish
        plan1 = '{"action_type":"operation","name":"pneuma_retriever","args":{"prompt":"find tables"}}'
        plan2 = '{"action_type":"operation","name":"web_crawl","args":{"url":"http://example.com"}}'
        plan3 = '{"action_type":"operation","name":"table_select","args":{"t1":{"id":"table_1","columns":["a","b"]}}}'
        self.lm_api.llm._responses = [plan1, plan2, plan3]  # type: ignore

        table_df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        table_doc = Table(
            doc_id="table_1",
            retriever_type=RetrieverType.PNEUMA_RETRIEVER,
            content=table_df,
            metadata={},
        )

        web_text = Text(
            doc_id="web_result_1",
            retriever_type=RetrieverType.WEB_CRAWL,
            content="This is a web crawl result.",
            metadata={},
        )

        # First call returns the table, second call returns the web result
        self.toolkit.retrieve_documents = MagicMock(
            side_effect=[[table_doc], [web_text]]
        )

        T = {"t1": pd.DataFrame(columns=["a", "b"])}

        result = self.materializer.materialize_T(T=T, column_descriptions={}, S="")

        # After web_crawl operation the state should have web_crawl_result set
        self.assertIsNotNone(self.materializer.state.web_crawl_result)
        assert self.materializer.state.web_crawl_result is not None
        self.assertEqual(
            self.materializer.state.web_crawl_result.content,
            "This is a web crawl result.",
        )

        # Ensure final materialized result still contains t1
        self.assertIn("t1", result)

        self.assertTrue(len(self.materializer.prov_graph.nodes) == 4)
        prov_graph_code_lines_1 = [
            self.materializer.prov_graph.ROOT_NODE_CODE,
            self.toolkit.generate_pandas_read_csv_code(table_doc),
            self.toolkit.generate_view_textual_document_code(web_text),
            self.toolkit.generate_table_select_code("t1", "table_1", ["a", "b"]),
        ]
        prov_graph_code_lines_2 = [
            self.materializer.prov_graph.ROOT_NODE_CODE,
            self.toolkit.generate_view_textual_document_code(web_text),
            self.toolkit.generate_pandas_read_csv_code(table_doc),
            self.toolkit.generate_table_select_code("t1", "table_1", ["a", "b"]),
        ]
        self.assertIn(
            self.materializer.prov_graph.get_graph_code(),
            (
                "\n\n".join(prov_graph_code_lines_1),
                "\n\n".join(prov_graph_code_lines_2),
            ),
        )

    def test_semantic_column_generator_adds_column(self):
        # LLM will call pneuma_retriever, semantic_column_generator, then table_select
        plan1 = '{"action_type":"operation","name":"pneuma_retriever","args":{"prompt":"find tables"}}'
        plan2 = '{"action_type":"operation","name":"semantic_column_generator","args":{"table_id":"table_1","new_column_name":"newcol","relevant_columns":["b"],"instruction":"make new"}}'
        plan3 = '{"action_type":"operation","name":"table_select","args":{"t1":{"id":"table_1","columns":["a","b","newcol"]}}}'
        self.lm_api.llm._responses = [plan1, plan2, plan3]  # type: ignore

        table_df = pd.DataFrame({"a": [1, 2], "b": [10, 20]})
        table_doc = Table(
            doc_id="table_1",
            retriever_type=RetrieverType.PNEUMA_RETRIEVER,
            content=table_df.copy(),
            metadata={},
        )

        self.toolkit.retrieve_documents = MagicMock(return_value=[table_doc])

        # Mock generation of semantic column
        self.toolkit.generate_semantic_column = MagicMock(return_value=[100, 200])

        T = {"t1": pd.DataFrame(columns=["a", "b", "newcol"])}

        result = self.materializer.materialize_T(T=T, column_descriptions={}, S="")

        self.assertIn("t1", result)
        res_df = result["t1"].reset_index(drop=True)
        self.assertIn("newcol", res_df.columns)
        self.assertEqual(list(res_df["newcol"]), [100, 200])

        self.assertTrue(len(self.materializer.prov_graph.nodes) == 4)
        prov_graph_code_lines_1 = [
            self.materializer.prov_graph.ROOT_NODE_CODE,
            self.toolkit.generate_pandas_read_csv_code(table_doc),
            self.toolkit.generate_semantic_col_generator_code(
                ["b"],
                table_doc,
                "newcol",
                [100, 200],
                os.path.join(
                    self.materializer._get_intermediate_table_dir_path(),
                    f"{table_doc.doc_id}.csv",
                ),
            ),
            self.toolkit.generate_table_select_code(
                "t1", "table_1", ["a", "b", "newcol"]
            ),
        ]
        self.assertEqual(
            self.materializer.prov_graph.get_graph_code(),
            "\n\n".join(prov_graph_code_lines_1),
        )


if __name__ == "__main__":
    unittest.main()
