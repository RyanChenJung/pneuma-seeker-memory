import os
import sys
import unittest
from unittest.mock import MagicMock

import pytest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../src"))
)

import pandas as pd

from pneuma_seeker.services.core.actions.executors.sql_executor import SQLExecutor
from pneuma_seeker.shared.config import Config


class SQLExecutorTests(unittest.TestCase):
    """Unit tests for SQLExecutor."""

    def setUp(self) -> None:
        self.config = Config()
        self.logger = MagicMock()
        self.db_api = MagicMock()
        self.lm_api = MagicMock()
        self.sql_executor = SQLExecutor(
            self.config, self.logger, self.db_api, self.lm_api
        )

    def test_execute_sql_happy_path(self):
        """Test successful SQL execution with a simple query."""
        tables = {
            "tbl_1": pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]}),
            "tbl_2": pd.DataFrame({"c": [7, 8], "d": [9, 10]})
        }
        sql_query = "SELECT SUM(a) as sum_a FROM tbl_1"

        result = self.sql_executor.execute({
            "sql_query": sql_query,
            "tables": tables
        })

        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(result.iloc[0, 0], 6)

    def test_execute_sql_with_join(self):
        """Test SQL execution with a JOIN operation."""
        tables = {
            "users": pd.DataFrame({"id": [1, 2], "name": ["Alice", "Bob"]}),
            "orders": pd.DataFrame({"user_id": [1, 1, 2], "amount": [100, 200, 150]})
        }
        sql_query = """
            SELECT u.name, SUM(o.amount) as total
            FROM users u
            JOIN orders o ON u.id = o.user_id
            GROUP BY u.name
            ORDER BY u.name
        """

        result = self.sql_executor.execute({
            "sql_query": sql_query,
            "tables": tables
        })

        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)
        self.assertEqual(result.iloc[0]["name"], "Alice")
        self.assertEqual(result.iloc[0]["total"], 300)

    def test_execute_sql_invalid_query_raises(self):
        """Test that invalid SQL raises an exception."""
        tables = {"tbl_1": pd.DataFrame({"a": [1, 2]})}
        sql_query = "SELECT * FROM nonexistent_table"

        with pytest.raises(Exception):
            self.sql_executor.execute({
                "sql_query": sql_query,
                "tables": tables
            })

    def test_execute_sql_invalid_input_types(self):
        """Test that invalid input types raise ValueError."""
        tables = {"tbl_1": pd.DataFrame({"a": [1, 2]})}

        # Test non-string sql_query
        with self.assertRaises(ValueError) as context:
            self.sql_executor.execute({
                "sql_query": 123,
                "tables": tables
            })
        self.assertIn("Input 'sql_query' must be a string", str(context.exception))

        # Test non-dict tables
        with self.assertRaises(ValueError) as context:
            self.sql_executor.execute({
                "sql_query": "SELECT * FROM tbl_1",
                "tables": "not a dict"
            })
        self.assertIn("Input 'tables' must be a dictionary", str(context.exception))

        # Test dict with non-DataFrame values
        with self.assertRaises(ValueError) as context:
            self.sql_executor.execute({
                "sql_query": "SELECT * FROM tbl_1",
                "tables": {"tbl_1": "not a dataframe"}
            })
        self.assertIn("Input 'tables' must be a dictionary of DataFrames", str(context.exception))

    def test_extract_table_ids_simple_from(self):
        """Test table ID extraction from simple FROM clause."""
        sql = "SELECT * FROM tbl_1"
        table_ids = self.sql_executor.extract_table_ids(sql)
        self.assertIn("tbl_1", table_ids)

    def test_extract_table_ids_with_join(self):
        """Test table ID extraction from query with JOIN."""
        sql = """
            SELECT * FROM users u
            JOIN orders o ON u.id = o.user_id
        """
        table_ids = self.sql_executor.extract_table_ids(sql)
        self.assertIn("users", table_ids)
        self.assertIn("orders", table_ids)

    def test_extract_table_ids_multiple_joins(self):
        """Test table ID extraction from query with multiple JOINs."""
        sql = """
            SELECT * FROM table_a
            JOIN table_b ON table_a.id = table_b.a_id
            LEFT JOIN table_c ON table_b.id = table_c.b_id
        """
        table_ids = self.sql_executor.extract_table_ids(sql)
        self.assertIn("table_a", table_ids)
        self.assertIn("table_b", table_ids)
        self.assertIn("table_c", table_ids)

    def test_extract_table_ids_quoted_names(self):
        """Test table ID extraction with quoted table names."""
        sql = 'SELECT * FROM "my_table" JOIN \'another_table\' ON 1=1'
        table_ids = self.sql_executor.extract_table_ids(sql)
        self.assertIn("my_table", table_ids)
        self.assertIn("another_table", table_ids)

    def test_extract_table_ids_schema_qualified(self):
        """Test table ID extraction with schema-qualified names."""
        sql = "SELECT * FROM schema1.table1 JOIN schema2.table2 ON 1=1"
        table_ids = self.sql_executor.extract_table_ids(sql)
        # Should include schema-qualified names
        self.assertTrue(
            any("table1" in tid for tid in table_ids) or 
            any("schema1.table1" in tid for tid in table_ids)
        )

    def test_extract_table_ids_subquery(self):
        """Test table ID extraction with subqueries."""
        sql = """
            SELECT * FROM (
                SELECT * FROM inner_table
            ) AS subquery
            JOIN outer_table ON subquery.id = outer_table.id
        """
        table_ids = self.sql_executor.extract_table_ids(sql)
        # Should extract at least some table names
        self.assertTrue(len(table_ids) > 0)

    def test_extract_table_ids_empty_query(self):
        """Test table ID extraction from empty or invalid query."""
        sql = ""
        table_ids = self.sql_executor.extract_table_ids(sql)
        self.assertEqual(table_ids, [])

    def test_execute_empty_tables(self):
        """Test SQL execution with no tables provided."""
        sql_query = "SELECT 1 as value"
        result = self.sql_executor.execute({
            "sql_query": sql_query,
            "tables": {}
        })
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(result.iloc[0, 0], 1)
