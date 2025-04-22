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
from processor.base_table_producer.base_table_producer import BaseTableProducer
from processor.table.representation.abstract_table import AbstractTable
from processor.table.representation.impl.df_table import DFTable
from processor.computation_graph import ComputationGraph
from processor.model.interface.impl.gpt import GPT
from processor.utils.logger import setup_logger
from processor.table.store.impl.py_table_store import PyTableStore


class TestBaseTableProducer(unittest.TestCase):
    def setUp(self):
        self.temp_dir_1 = TemporaryDirectory()
        self.temp_dir_2 = TemporaryDirectory()
        self.base_table_producer = BaseTableProducer()

        self.target_schema = ["target_col_1", "target_col_2"]

        self.db_schema = "test_db"
        self.table_id_1 = "test_table_1"
        self.table_id_2 = "test_table_2"
        self.table_id_3 = "test_table_3"
        self.table_descriptions = {
            self.table_id_1: "This is the test table 1.",
            self.table_id_2: "This is the test table 2.",
            self.table_id_3: "This is the test table 3.",
        }

        self.table_store = PyTableStore(self.temp_dir_1.name)
        self.table_store.create_db_schema(self.db_schema)
        self.table_store.add_table(
            self.db_schema,
            self.table_id_1,
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
        self.table_store.add_table(
            self.db_schema,
            self.table_id_2,
            DFTable(
                DataFrame(
                    {
                        "school_id": [3, 2, 1, 5, 4],
                        "city": [
                            "Chicago",
                            "Los Angeles",
                            "New York City",
                            "San Fransisco",
                            "Seattle",
                        ],
                    }
                )
            ),
        )
        self.table_store.add_table(
            self.db_schema,
            self.table_id_3,
            DFTable(
                DataFrame(
                    {
                        "SchoolID": [3, 2, 1, 5, 4],
                        "City": [
                            "Chicago",
                            "Los Angeles",
                            "New York City",
                            "San Fransisco",
                            "Seattle",
                        ],
                    }
                )
            ),
        )

        self.join_operations = """[
            {
                "Join Result": "Join_1",
                "Left Table": "test_table_1",
                "Right Table": "test_table_2",
                "Left Join Key": "id",
                "Right Join Key": "school_id"
            }
        ]"""

        self.union_operations = """[
            {
                "Output Table ID": "Union_1",
                "Tables": ["test_table_2", "test_table_3"],
                "Unified Schema": ["school_id", "city"],
                "Mappings": {
                "test_table_2": {"school_id": "school_id", "city": "city"},
                "test_table_3": {"SchoolID": "school_id", "City": "city"},
                }
            }
        ]"""

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

    def test_get_relevant_table_ids(self):
        mock_return_value = "YES"
        self.conductor_state.llm.chat = MagicMock(return_value=mock_return_value)
        input_nodes = [
            self.conductor_state.computation_graph.create_node(
                computation_description="Produced target schema.",
                computation_output=self.target_schema,
            )
        ]
        target_schema: list[str] = input_nodes[0].computation_output

        output_node = self.base_table_producer.select_relevant_table_ids(
            ctx=self.conductor_state,
            db_schema=self.db_schema,
            target_schema=target_schema,
            table_descriptions=self.table_descriptions,
            input_computation_nodes=input_nodes,
        )
        relevant_table_ids = output_node.computation_output
        expected_relevant_table_ids = [
            self.table_id_1,
            self.table_id_2,
            self.table_id_3,
        ]
        computation_graph_nodes = self.conductor_state.computation_graph.nodes
        self.assertTrue(len(computation_graph_nodes), 2)
        self.assertEqual(output_node.input_nodes, input_nodes)
        self.assertEqual(relevant_table_ids, expected_relevant_table_ids)
        self.assertTrue(output_node.function_name, "get_relevant_table_ids")
        self.assertTrue(output_node.class_name, "BaseTableProducer")

    def test_produce_union_operations(self):
        self.conductor_state.llm.chat = MagicMock(return_value=self.union_operations)
        output_node = self.base_table_producer.produce_union_operations(
            ctx=self.conductor_state,
            db_schema=self.db_schema,
            table_descriptions=self.table_descriptions,
        )
        union_operations: list[dict[str, Any]] = output_node.computation_output
        expected_operations = [
            {
                "Output Table ID": "Union_1",
                "Tables": [self.table_id_2, self.table_id_3],
                "Unified Schema": ["school_id", "city"],
                "Mappings": {
                    self.table_id_2: {"school_id": "school_id", "city": "city"},
                    self.table_id_3: {"SchoolID": "school_id", "City": "city"},
                },
            }
        ]

        computation_graph_nodes = self.conductor_state.computation_graph.nodes
        self.assertTrue(len(computation_graph_nodes), 1)
        self.assertEqual(union_operations, expected_operations)
        self.assertTrue(output_node.function_name, "produce_union_operations")
        self.assertTrue(output_node.class_name, "BaseTableProducer")

    def test_run_union_operations(self):
        output_node = self.base_table_producer.run_union_operations(
            ctx=self.conductor_state,
            table_mappings=self.table_store.get_all_tables_in_db_schema(self.db_schema),
            operations=[
                {
                    "Output Table ID": "Union_1",
                    "Tables": [self.table_id_2, self.table_id_3],
                    "Unified Schema": ["school_id", "city"],
                    "Mappings": {
                        self.table_id_2: {"school_id": "school_id", "city": "city"},
                        self.table_id_3: {"SchoolID": "school_id", "City": "city"},
                    },
                }
            ],
        )
        actual_table_mappings: dict[str, AbstractTable] = output_node.computation_output

        expected_table_mappings: dict[str, AbstractTable] = {
            self.table_id_1: self.table_store.get_table(
                self.db_schema, self.table_id_1
            ),
            "Union_1": DFTable.concat(
                [
                    self.table_store.get_table(self.db_schema, self.table_id_2),
                    self.table_store.get_table(self.db_schema, self.table_id_2),
                ]
            ),
        }

        computation_graph_nodes = self.conductor_state.computation_graph.nodes
        self.assertTrue(len(computation_graph_nodes), 1)
        self.assertEqual(
            list(actual_table_mappings.keys()), list(expected_table_mappings.keys())
        )
        self.assertEqual(
            actual_table_mappings["Union_1"], expected_table_mappings["Union_1"]
        )
        self.assertTrue(output_node.function_name, "run_union_operations")
        self.assertTrue(output_node.class_name, "BaseTableProducer")

    def test_produce_join_operations(self):
        self.conductor_state.llm.chat = MagicMock(return_value=self.join_operations)
        output_node = self.base_table_producer.produce_join_operations(
            ctx=self.conductor_state,
            db_schema=self.db_schema,
            table_descriptions=self.table_descriptions,
        )
        join_operations: list[dict[str, Any]] = output_node.computation_output
        expected_operations = [
            {
                "Join Result": "Join_1",
                "Left Table": "test_table_1",
                "Right Table": "test_table_2",
                "Left Join Key": "id",
                "Right Join Key": "school_id",
            }
        ]

        computation_graph_nodes = self.conductor_state.computation_graph.nodes
        self.assertTrue(len(computation_graph_nodes), 1)
        self.assertEqual(join_operations, expected_operations)
        self.assertTrue(output_node.function_name, "produce_join_operations")
        self.assertTrue(output_node.class_name, "BaseTableProducer")

    def test_run_join_operations(self):
        self.conductor_state.llm.chat = MagicMock(
            return_value="""SELECT * FROM test_table_1 JOIN test_table_2 ON test_table_1.id = test_table_2.school_id"""
        )
        output_node = self.base_table_producer.run_join_operations(
            ctx=self.conductor_state,
            table_mapping=self.table_store.get_all_tables_in_db_schema(self.db_schema),
            operations=[
                {
                    "Join Result": "Join_1",
                    "Left Table": "test_table_1",
                    "Right Table": "test_table_2",
                    "Left Join Key": "id",
                    "Right Join Key": "school_id",
                }
            ],
        )
        actual_table_mapping: dict[str, AbstractTable] = output_node.computation_output
        expected_table_mapping = {
            self.table_id_3: self.conductor_state.table_store.get_table(
                self.db_schema, self.table_id_3
            ),
            "Join_1": DFTable(
                data=DataFrame(
                    {
                        "id": [1, 2, 3, 4, 5],
                        "school_name": [
                            "school 1",
                            "school 2",
                            "school 3",
                            "school 4",
                            "school 5",
                        ],
                        "school_id": [1, 2, 3, 4, 5],
                        "city": [
                            "New York City",
                            "Los Angeles",
                            "Chicago",
                            "Seattle",
                            "San Fransisco",
                        ],
                    }
                )
            ),
        }

        computation_graph_nodes = self.conductor_state.computation_graph.nodes
        self.assertTrue(len(computation_graph_nodes), 2)
        self.assertEqual(
            list(actual_table_mapping.keys()), list(expected_table_mapping.keys())
        )
        self.assertEqual(
            actual_table_mapping["Join_1"], expected_table_mapping["Join_1"]
        )
        self.assertTrue(output_node.function_name, "run_join_operations")
        self.assertTrue(output_node.class_name, "BaseTableProducer")


if __name__ == "__main__":
    unittest.main()
