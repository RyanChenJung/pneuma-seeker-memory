import logging
import os
import sys
from typing import Any
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

from pandas import DataFrame

from pneuma_seeker.core.conductor.main import Conductor


sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../src"))
)


class TestBaseTableReducer(unittest.TestCase):
    def setUp(self):
        self.temp_dir_1 = TemporaryDirectory()
        self.temp_dir_2 = TemporaryDirectory()

        self.conductor = Conductor(
            "azure_openai"
        )

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

    def test_communicate_with_user(self):
        mock_return_value = """
            { 
                "action": "communicate_with_user",
                "message": "I keep an internal “state” with three parts:\n\n1. T: a dictionary of target tables, each with its list of columns.\n2. column_descriptions: for each table, a description of what each column means.\n3. Q: an ordered list of SQL queries that will run against those tables.\n\nRight now, all three are empty (no tables defined, no columns described, no SQL written). \n\nNext, please tell me what data or business question you’d like to explore. From there, I’ll propose a target table schema (T), describe its columns, and build the SQL (Q) step by step—ensuring every query only references columns actually in our defined tables."
            }
        """


    def test_compute_target_table(self):
        self.conductor_state.llm.chat = MagicMock(return_value=mock_return_value)
        output_node = self.base_table_reducer.compute_target_table(
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
        output_node = self.base_table_reducer.apply_predicate_to_target_table(
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
