# tests/pneuma_seeker/shared/test_table_reader.py
import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src"))
)

import tempfile
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd

from pneuma_seeker.shared.table_reader import TableReader
from pneuma_seeker.shared.schemas.core.ir_system import Table


class TableReaderTests(unittest.TestCase):
    def setUp(self):
        # Temporary directory for test CSV/XLSX files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_url = "https://example.com/"
        self.api_key = "fake_api_key"
        self.reader = TableReader(base_url=self.base_url, api_key=self.api_key)

    def tearDown(self):
        self.temp_dir.cleanup()
        patch.stopall()

    def _make_csv_file(self, filename: str, content: str) -> str:
        path = os.path.join(self.temp_dir.name, filename)
        with open(path, "w") as f:
            f.write(content)
        return path

    def _make_excel_file(self, filename: str, sheets: dict[str, pd.DataFrame]) -> str:
        path = os.path.join(self.temp_dir.name, filename)
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            for sheet_name, df in sheets.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        return path

    def test_read_csv_file(self):
        csv_path = self._make_csv_file("test.csv", "A,B\n1,2\n3,4")
        tables = self.reader.process_external_tables([csv_path])
        self.assertEqual(len(tables), 1)
        table = tables[0]
        self.assertIsInstance(table, Table)
        self.assertEqual(list(table.content.columns), ["a", "b"])
        self.assertEqual(table.content.shape, (2, 2))

    def test_read_excel_file_multiple_sheets(self):
        sheets = {
            "Sheet1": pd.DataFrame({"A": [1, 2], "B": [3, 4]}),
            "Sheet2": pd.DataFrame({"X": [5, 6], "Y": [7, 8]}),
        }
        excel_path = self._make_excel_file("test.xlsx", sheets)
        tables = self.reader.process_external_tables([excel_path])
        self.assertEqual(len(tables), 2)
        sheet_names = {t.metadata["sheet_name"] for t in tables}
        self.assertEqual(sheet_names, {"Sheet1", "Sheet2"})

    @patch("pneuma_seeker.shared.table_reader.requests.get")
    def test_download_csv_from_api(self, mock_get):
        # Mock CSV response
        csv_content = b"A,B\n1,2\n3,4"
        mock_resp = MagicMock()
        mock_resp.headers = {"Content-Type": "text/csv"}
        mock_resp.content = csv_content
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        tables = self.reader.process_external_tables(["/api/fake.csv/content"])
        self.assertEqual(len(tables), 1)
        self.assertEqual(list(tables[0].content.columns), ["a", "b"])
        self.assertEqual(tables[0].content.shape, (2, 2))

    @patch("pneuma_seeker.shared.table_reader.TableReader._download_from_api")
    def test_download_excel_from_api(self, mock_download):
        # Write to a temp file in the test dir
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        excel_path = os.path.join(self.temp_dir.name, "fake.xlsx")
        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Sheet1", index=False)

        mock_download.return_value = excel_path

        tables = self.reader.process_external_tables(["/api/fake.xlsx/content"])
        self.assertEqual(len(tables), 1)
        self.assertEqual(list(tables[0].content.columns), ["a", "b"])


if __name__ == "__main__":
    unittest.main()
