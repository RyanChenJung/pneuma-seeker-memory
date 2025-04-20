import logging
import os
import sys
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

from pandas import DataFrame



sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../src"))
)

from processor.conductor_state import ConductorState
from processor.schema_processor.schema_processor import SchemaProcessor
from processor.table.representation.impl.df_table import DFTable
from processor.computation_graph import ComputationGraph
from processor.models.interface.impl.gpt import GPT
from processor.utils.string_processor import parse_code_string
from processor.utils.logger import setup_logger
from processor.table.store.impl.py_table_store import PyTableStore


class TestSchemaProcessor(unittest.TestCase):
    def setUp(self):
        self.temp_dir_1 = TemporaryDirectory()
        self.temp_dir_2 = TemporaryDirectory()
        self.schema_processor = SchemaProcessor()

        table_store = PyTableStore(self.temp_dir_1.name)
        table_store.create_db_schema("test_db")
        table_store.add_table(
            "test_db", "test_table", DFTable(DataFrame({"test": ["a"]}))
        )

        os.environ["OPENAI_API_KEY"] = "test_api_key"
        self.conductor_state = ConductorState(
            table_store=table_store,
            logger=setup_logger(
                name="processor_logger",
                log_file=f"{self.temp_dir_2.name}/processor.log",
                level=logging.INFO,
                max_bytes=10_000_000,
                backup_count=5,
            ),
            llm=GPT(),
            embedding_model=None,
            computation_graph=ComputationGraph(),
        )

    def tearDown(self):
        self.temp_dir_1.cleanup()
        logger = logging.getLogger("processor_logger")
        handlers = logger.handlers[:]
        for handler in handlers:
            handler.close()
            logger.removeHandler(handler)

        self.temp_dir_2.cleanup()

    def test_get_target_schema(self):
        mock_return_value = "['test_col_1', 'test_col_2']"
        self.conductor_state.llm.chat = MagicMock(return_value=mock_return_value)
        self.schema_processor.get_target_schema(
            ctx=self.conductor_state,
            question="Test question.",
        )
        computation_graph_nodes = self.conductor_state.computation_graph.nodes
        self.assertTrue(len(computation_graph_nodes), 1)

        computation_node = computation_graph_nodes[0]
        self.assertEqual(computation_node.input_nodes, [])
        self.assertEqual(
            computation_node.computation_output, parse_code_string(mock_return_value)
        )
        self.assertTrue(computation_node.function_name, "get_target_schema")
        self.assertTrue(computation_node.class_name, "SchemaProcessor")


if __name__ == "__main__":
    unittest.main()
