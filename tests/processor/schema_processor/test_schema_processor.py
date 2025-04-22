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
from processor.computation_graph import ComputationGraph, Node
from processor.model.interface.impl.gpt import GPT
from processor.utils.string_processor import parse_code_string
from processor.utils.logger import setup_logger
from processor.table.store.impl.py_table_store import PyTableStore


class TestSchemaProcessor(unittest.TestCase):
    def setUp(self):
        self.temp_dir_1 = TemporaryDirectory()
        self.temp_dir_2 = TemporaryDirectory()
        self.schema_processor = SchemaProcessor()

        self.db_schema = "test_db"
        self.table_id = "test_table"

        table_store = PyTableStore(self.temp_dir_1.name)
        table_store.create_db_schema(self.db_schema)
        table_store.add_table(
            self.db_schema,
            self.table_id,
            DFTable(
                DataFrame(
                    {
                        "test_col_1": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                        "test_col_2": [10, 9, 8, 7, 6, 5, 4, 3, 2, 1],
                    }
                )
            ),
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
        output_node = self.schema_processor.get_target_schema(
            ctx=self.conductor_state,
            question="Test question.",
        )
        target_schema: list[str] = output_node.computation_output

        computation_graph_nodes = self.conductor_state.computation_graph.nodes
        self.assertTrue(len(computation_graph_nodes), 1)
        self.assertEqual(output_node.input_nodes, [])
        self.assertEqual(target_schema, output_node.computation_output)
        self.assertEqual(
            output_node.computation_output, parse_code_string(mock_return_value)
        )
        self.assertTrue(output_node.function_name, "get_target_schema")
        self.assertTrue(output_node.class_name, "SchemaProcessor")

    def test_get_table_descriptions(self):
        mock_return_value = "This table represents a sample table."
        self.conductor_state.llm.chat = MagicMock(return_value=mock_return_value)
        output_node = self.schema_processor.get_table_descriptions(
            ctx=self.conductor_state,
            db_schema=self.db_schema,
        )
        table_descriptions: dict[str, str] = output_node.computation_output
        expected_table_descriptions = {
            self.table_id: "This table represents a sample table.",
        }
        computation_graph_nodes = self.conductor_state.computation_graph.nodes
        self.assertTrue(len(computation_graph_nodes), 1)

        self.assertEqual(output_node.input_nodes, [])
        self.assertEqual(table_descriptions, output_node.computation_output)
        self.assertEqual(
            output_node.computation_output, expected_table_descriptions
        )
        self.assertTrue(output_node.function_name, "get_table_descriptions")
        self.assertTrue(output_node.class_name, "SchemaProcessor")
    
    def test_get_enhanced_schemas(self):
        mock_return_value = "New column name: new_col_name"
        self.conductor_state.llm.chat = MagicMock(return_value=mock_return_value)

        input_nodes: list[Node] = [
            self.conductor_state.computation_graph.create_node(
                f"Described tables in DB schema `{self.db_schema}`",
                {
                    self.table_id: "This table represents a sample table.",
                },
            )
        ]

        output_node = self.schema_processor.get_enhanced_schemas(
            ctx=self.conductor_state,
            db_schema=self.db_schema,
            table_descriptions=input_nodes[0].computation_output,
            input_computation_nodes=input_nodes,
        )
        enhanced_schemas: dict[str, list[str]] = output_node.computation_output
        expected_enhanced_schemas = {
            self.table_id: ["new_col_name", "new_col_name"]
        }

        computation_graph_nodes = self.conductor_state.computation_graph.nodes
        self.assertTrue(len(computation_graph_nodes), 2)

        self.assertEqual(output_node.input_nodes[0], input_nodes[0])
        self.assertEqual(enhanced_schemas, output_node.computation_output)
        self.assertEqual(
            output_node.computation_output, expected_enhanced_schemas
        )
        self.assertTrue(output_node.function_name, "get_enhanced_schemas")
        self.assertTrue(output_node.class_name, "SchemaProcessor")

if __name__ == "__main__":
    unittest.main()
