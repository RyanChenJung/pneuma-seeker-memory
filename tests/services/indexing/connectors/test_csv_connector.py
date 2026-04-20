import os
import shutil
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../src")),
)

from pneuma_seeker.services.indexing.connectors.csv_connector import CSVConnector


class TestCSVConnector(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        # top-level CSVs
        pd.DataFrame({"id": [1, 2], "name": ["Alice", "Bob"]}).to_csv(
            os.path.join(self.tmpdir, "users.csv"), index=False
        )
        pd.DataFrame({"order_id": [10], "amount": [100]}).to_csv(
            os.path.join(self.tmpdir, "orders.csv"), index=False
        )

        # nested CSV with same base name to exercise dedupe behavior
        nested = os.path.join(self.tmpdir, "nested")
        os.makedirs(nested, exist_ok=True)
        pd.DataFrame({"id": [3], "name": ["Carol"]}).to_csv(
            os.path.join(nested, "users.csv"), index=False
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_check_connection_with_directory(self):
        connector = CSVConnector({"type": "csv", "directory_path": self.tmpdir})
        self.assertTrue(connector.check_connection())

    def test_discover_streams(self):
        connector = CSVConnector({"type": "csv", "directory_path": self.tmpdir})
        streams = connector.discover()
        names = [item["stream"] for item in streams]
        # base files
        self.assertIn("users", names)
        self.assertIn("orders", names)
        # nested file with same stem should be deduped to users_1
        self.assertIn("users_1", names)

        # ensure discover includes file paths and they point to actual files
        path_map = {item["stream"]: item["path"] for item in streams}
        self.assertTrue(os.path.exists(path_map["users"]))
        self.assertTrue(os.path.exists(path_map["users_1"]))

    def test_read_stream_records(self):
        connector = CSVConnector({"type": "csv", "directory_path": self.tmpdir})
        # determine which discovered stream corresponds to root vs nested users.csv
        streams = connector.discover()
        path_map = {item["stream"]: item["path"] for item in streams}

        root_stream = None
        nested_stream = None
        # normalize using realpath to account for macOS /private symlink differences
        root_dir = os.path.normpath(os.path.realpath(self.tmpdir))
        nested_dir = os.path.normpath(
            os.path.realpath(os.path.join(self.tmpdir, "nested"))
        )
        for s, p in path_map.items():
            pnorm = os.path.normpath(os.path.realpath(p))
            if os.path.basename(pnorm) == "users.csv":
                parent = os.path.dirname(pnorm)
                if parent == root_dir:
                    root_stream = s
                elif parent == nested_dir:
                    nested_stream = s

        self.assertIsNotNone(root_stream)
        self.assertIsNotNone(nested_stream)

        assert root_stream is not None
        assert nested_stream is not None

        # root users.csv has two rows
        rows_root = list(connector.read(root_stream))
        self.assertEqual(len(rows_root), 2)

        # nested users.csv has one row
        rows_nested = list(connector.read(nested_stream))
        self.assertEqual(len(rows_nested), 1)
        self.assertEqual(rows_nested[0]["id"], 3)
        self.assertEqual(rows_nested[0]["name"], "Carol")

    def test_read_unknown_stream_raises(self):
        connector = CSVConnector({"type": "csv", "directory_path": self.tmpdir})
        with self.assertRaises(KeyError):
            list(connector.read("unknown"))

    def test_check_connection_with_no_csv(self):
        empty_dir = tempfile.mkdtemp()
        try:
            connector = CSVConnector({"type": "csv", "directory_path": empty_dir})
            self.assertFalse(connector.check_connection())
        finally:
            shutil.rmtree(empty_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
