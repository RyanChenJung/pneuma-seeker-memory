import os
import sys
import unittest
from unittest.mock import MagicMock

import pytest

sys.path.insert(
	0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../src"))
)

import pandas as pd

from pneuma_seeker.services.core.actions.operators.table_projection import TableProjection
from pneuma_seeker.shared.config import Config


class TableProjectionTests(unittest.TestCase):
	"""Unit tests for TableProjection."""

	def setUp(self) -> None:
		self.config = Config()
		self.logger = MagicMock()
		self.db_api = MagicMock()
		self.lm_api = MagicMock()
		self.table_projection = TableProjection(
			self.config, self.logger, self.db_api, self.lm_api
		)

	def test_apply_happy_path(self):
		table = pd.DataFrame({"a": [1, 2], "b": [3, 4], "c": [5, 6]})
		relevant_columns = ["a", "c"]

		result = self.table_projection.apply(
			{"table": table, "relevant_columns": relevant_columns}
		)

		self.assertIsInstance(result, pd.DataFrame)
		self.assertEqual(list(result.columns), ["a", "c"])
		self.assertEqual(result.iloc[0]["a"], 1)
		self.assertEqual(result.iloc[1]["c"], 6)

	def test_apply_invalid_table_raises(self):
		with self.assertRaises(ValueError) as context:
			self.table_projection.apply(
				{"table": "not a dataframe", "relevant_columns": ["a"]}
			)
		self.assertIn("Input 'table' must be a pandas DataFrame", str(context.exception))

	def test_apply_invalid_relevant_columns_type_raises(self):
		table = pd.DataFrame({"a": [1, 2]})

		with self.assertRaises(ValueError) as context:
			self.table_projection.apply(
				{"table": table, "relevant_columns": "a"}
			)
		self.assertIn(
			"Input 'relevant_columns' must be a list of strings",
			str(context.exception),
		)

	def test_apply_invalid_relevant_columns_values_raises(self):
		table = pd.DataFrame({"a": [1, 2]})

		with self.assertRaises(ValueError) as context:
			self.table_projection.apply(
				{"table": table, "relevant_columns": [1, 2]}
			)
		self.assertIn(
			"Input 'relevant_columns' must be a list of strings",
			str(context.exception),
		)

	def test_apply_missing_column_raises_key_error(self):
		table = pd.DataFrame({"a": [1, 2]})

		with pytest.raises(KeyError):
			self.table_projection.apply(
				{"table": table, "relevant_columns": ["b"]}
			)
