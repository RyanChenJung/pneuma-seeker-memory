import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../src"))
)

import pandas as pd

from pneuma_seeker.shared.schemas.core.ir_system import AbstractDocument, RetrieverType
from pneuma_seeker.services.core.toolkit.python_executor import PythonExecutor


class PythonExecutorTests(unittest.TestCase):
    """Unit tests for PythonExecutor."""

    def setUp(self) -> None:
        self.logger = MagicMock()
        self.exec = PythonExecutor(logger=self.logger)

    def test_execute_code_happy_path_and_table_ids(self):
        # Prepare a table and code that references it and sets `result`
        tables = {"tbl_1": pd.DataFrame({"a": [1, 2], "b": [3, 4]})}
        code = 'result = tables["tbl_1"]["a"].sum()'

        out = self.exec.execute_code(tables, code)

        # exec_res should be the sum of column `a`
        self.assertIn("exec_res", out)
        self.assertEqual(out["exec_res"], 3)

        # used_table_ids should list the referenced table id
        self.assertEqual(out["used_table_ids"], ["tbl_1"])

    def test_execute_code_exception_returns_exception_and_no_table_ids(self):
        tables = {}
        code = 'raise ValueError("boom")'

        out = self.exec.execute_code(tables, code)

        # exec_res should be an exception instance and used_table_ids empty
        self.assertIsInstance(out.get("exec_res"), Exception)
        self.assertEqual(out.get("used_table_ids"), [])

    def test_execute_code_multiple_table_references_extracts_ids(self):
        tables = {"a": pd.DataFrame({"x": [1]}), "b": pd.DataFrame({"y": [2]})}
        code = 'tmp = tables["a"]; tmp2 = tables["b"]; tmp3 = tables["a"]'

        out = self.exec.execute_code(tables, code)

        # Should extract ids in the order referenced
        self.assertEqual(out.get("used_table_ids"), ["a", "b", "a"])

    def test_generate_read_external_tables_code_csv_and_xlsx(self):
        # CSV document
        csv_doc = AbstractDocument(
            doc_id="doc_csv",
            retriever_type=RetrieverType.USER,
            content=None,
            metadata={},
            path="/tmp/data.csv",
            last_node_id=None,
        )
        csv_code = self.exec.generate_read_external_tables_code(1, csv_doc)
        self.assertIn("pd.read_csv", csv_code)
        self.assertIn('tables["doc_csv"]', csv_code)

        # XLSX document
        xlsx_doc = AbstractDocument(
            doc_id="doc_xlsx",
            retriever_type=RetrieverType.USER,
            content=None,
            metadata={},
            path="/tmp/data.xlsx",
            last_node_id=None,
        )
        xlsx_code = self.exec.generate_read_external_tables_code(2, xlsx_doc)
        self.assertIn("pd.read_excel", xlsx_code)
        self.assertIn('tables["doc_xlsx"]', xlsx_code)
