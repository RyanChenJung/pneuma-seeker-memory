import logging
import os
import sys
from typing import Any
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

from pandas import DataFrame


sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../src"))
)

from processor.conductor_state import ConductorState
from processor.base_table_reducer.base_table_reducer import BaseTableReducer
from processor.table.representation.abstract_table import AbstractTable
from processor.table.representation.impl.df_table import DFTable
from processor.computation_graph import ComputationGraph
from processor.models.interface.impl.gpt import GPT
from processor.utils.logger import setup_logger
from processor.table.store.impl.py_table_store import PyTableStore


class TestBaseTableReducer(unittest.TestCase):
    def setUp(self):
        self.temp_dir_1 = TemporaryDirectory()
        self.temp_dir_2 = TemporaryDirectory()
        self.base_table_reducer = BaseTableReducer()

        self.target_schema = ["target_col_1"]
        self.question = "This is a sample question."
        self.db_schema = "test_db"
        self.table_id = "base_table"
        self.table_descriptions = {
            self.table_id: "This is the base table.",
        }

        self.table_store = PyTableStore(self.temp_dir_1.name)
        self.table_store.create_db_schema(self.db_schema)
        self.table_store.add_table(
            self.db_schema,
            self.table_id,
            DFTable(
                DataFrame(
                    {
                        "id": [1, 2, 3, 4, 5],
                        "school_name": [
                            "school 1",
                            "school 2",
                            "school 3",
                            "school 4",
                            "school 5",
                        ],
                    }
                )
            ),
        )

        os.environ["OPENAI_API_KEY"] = "test_api_key"
        self.conductor_state = ConductorState(
            table_store=self.table_store,
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

    def test_project_columns(self):
        mock_return_value = """{
            "operation": "select_column",
            "columns_involved": ["school_name"],
            "description": "Select SRC.school_name."
        }"""
        self.conductor_state.llm.chat = MagicMock(return_value=mock_return_value)
        output_node = self.base_table_reducer.project_columns(
            ctx=self.conductor_state,
            base_table=self.conductor_state.table_store.get_table(
                self.db_schema, self.table_id
            ),
            target_schema=self.target_schema,
        )
        target_table: AbstractTable = output_node.computation_output
        expected_data = self.conductor_state.table_store.get_table(
            self.db_schema, self.table_id
        ).get_data()[["school_name"]]
        expected_data.columns = self.target_schema
        expected_table = DFTable(expected_data)
        self.assertEqual(target_table, expected_table)
        self.assertTrue(output_node.function_name, "project_columns")
        self.assertTrue(output_node.class_name, "BaseTableReducer")

    def test_apply_predicate_to_rows(self):
        mock_return_value = """SELECT * FROM target_table;"""
        self.conductor_state.llm.chat = MagicMock(return_value=mock_return_value)
        output_node = self.base_table_reducer.apply_predicate_to_rows(
            self.conductor_state,
            self.table_store.get_table(self.db_schema, self.table_id),
            self.question,
        )
        final_table = output_node.computation_output
        self.assertEqual(
            final_table, self.table_store.get_table(self.db_schema, self.table_id)
        )
        self.assertTrue(output_node.function_name, "apply_predicate_to_rows")
        self.assertTrue(output_node.class_name, "BaseTableReducer")


if __name__ == "__main__":
    unittest.main()
