import io
import logging
import os
import shutil
import sys
import tempfile
import unittest
import uuid
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../src")))

from pneuma_seeker.services.db.main import PneumaDB
from pneuma_seeker.shared.schemas.db.table_type import TableType


class TestDBServiceAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Instantiate service-backed DB for tests
        global db
        db = PneumaDB(logger=logging.getLogger("test"))

        cls.tmpdir = tempfile.mkdtemp()
        db.dataset_db_path = Path(cls.tmpdir) / "datasets"
        db.workspace_db_path = Path(cls.tmpdir) / "workspaces"

        db.dataset_db_path.mkdir(parents=True, exist_ok=True)
        db.workspace_db_path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        db.close_all_connections()
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _new_workspace(self):
        return f"user_{uuid.uuid4()}", f"chat_{uuid.uuid4()}"

    def _register_external_table(self, user_id, chat_id, name="t1"):
        df = pd.DataFrame({"a": [1, 2, 3]})
        # Register DataFrame directly into workspace
        db.register_external_table(user_id, chat_id, name, df)

    # ------------------------------------------------------------------
    # Dataset registration
    # ------------------------------------------------------------------
    def test_register_dataset_success(self):
        tmp = tempfile.mkdtemp()
        try:
            df = pd.DataFrame({"x": [1, 2]})
            csv = os.path.join(tmp, "tbl.csv")
            df.to_csv(csv, index=False)
            # Register dataset by pointing to directory with CSVs
            db.register_dataset_table("my_ds", tmp)

            ds_file = db.dataset_db_path / "my_ds.db"
            self.assertTrue(ds_file.exists())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_register_dataset_rejects_non_csv(self):
        tmp = tempfile.mkdtemp()
        try:
            # Create a non-csv file; registration should not crash
            with open(os.path.join(tmp, "x.txt"), "wb") as f:
                f.write(b"123")

            db.register_dataset_table("bad", tmp)
            ds_file = db.dataset_db_path / "bad.db"
            self.assertTrue(ds_file.exists())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    # ------------------------------------------------------------------
    # Dataset linking
    # ------------------------------------------------------------------
    def test_link_dataset_not_found(self):
        user_id, chat_id = self._new_workspace()
        with self.assertRaises(FileNotFoundError):
            db.link_dataset_tables(user_id, chat_id, "missing")

    # ------------------------------------------------------------------
    # Workspace table registration
    # ------------------------------------------------------------------
    def test_register_and_list_external_table(self):
        user_id, chat_id = self._new_workspace()
        self._register_external_table(user_id, chat_id, "t1")
        tables = db.get_tables_of_type_as_dfs(user_id, chat_id, TableType.EXTERNAL)
        self.assertIn("t1", tables.keys())

    def test_preview_table(self):
        user_id, chat_id = self._new_workspace()
        self._register_external_table(user_id, chat_id, "preview_me")
        df = db.execute_query(
            user_id, chat_id, 'SELECT * FROM "preview_me" LIMIT 2'
        )
        self.assertEqual(len(df), 2)

    # ------------------------------------------------------------------
    # Temporary tables
    # ------------------------------------------------------------------
    def test_register_and_unregister_temporary_table(self):
        user_id, chat_id = self._new_workspace()
        df = pd.DataFrame({"x": [1]})
        db.register_temporary_table(user_id, chat_id, "tmp", df)

        # ensure temp table is queryable
        tmp_df = db.execute_query(user_id, chat_id, 'SELECT * FROM "tmp"')
        self.assertEqual(len(tmp_df), 1)

        db.unregister_temporary_table(user_id, chat_id, "tmp")

    # ------------------------------------------------------------------
    # Query execution
    # ------------------------------------------------------------------
    def test_execute_query(self):
        user_id, chat_id = self._new_workspace()
        self._register_external_table(user_id, chat_id, "src")
        df = db.execute_query(
            user_id, chat_id, "SELECT COUNT(*) AS c FROM src"
        )
        self.assertEqual(int(df.iloc[0]["c"]), 3)

    def test_execute_query_into_table(self):
        user_id, chat_id = self._new_workspace()
        self._register_external_table(user_id, chat_id, "src")
        out_df = db.execute_query_into_table(
            user_id,
            chat_id,
            "SELECT a * 2 AS b FROM src",
            "derived",
            sample_size=10,
        )

        self.assertEqual(len(out_df), 3)

    # ------------------------------------------------------------------
    # Delete tables
    # ------------------------------------------------------------------
    def test_delete_tables_of_type(self):
        user_id, chat_id = self._new_workspace()
        self._register_external_table(user_id, chat_id, "t1")
        self._register_external_table(user_id, chat_id, "t2")
        deleted = db.delete_all_tables_of_type(user_id, chat_id, TableType.EXTERNAL)
        self.assertEqual(deleted, 2)

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------
    def test_download_tables_zip(self):
        user_id, chat_id = self._new_workspace()
        self._register_external_table(user_id, chat_id, "t1")
        tables = db.get_tables_of_type_as_dfs(user_id, chat_id, TableType.EXTERNAL)
        self.assertIn("t1", tables)

        # create zip in-memory (simulate export) and ensure t1.csv would be present
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode="w") as zf:
            for name, df in tables.items():
                zf.writestr(f"{name}.csv", df.to_csv(index=False))

        z = zipfile.ZipFile(io.BytesIO(buf.getvalue()))
        self.assertIn("t1.csv", z.namelist())

    def test_download_tables_empty(self):
        user_id, chat_id = self._new_workspace()
        tables = db.get_tables_of_type_as_dfs(user_id, chat_id, TableType.EXTERNAL)
        self.assertEqual(len(tables), 0)

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------
    def test_save_and_load_state(self):
        user_id, chat_id = self._new_workspace()

        payload = {
            "info_need_state": {"q": "hello"},
            "retrieved_tables": [{"t": "x"}],
            "enumerated_table_ids": ["a", "b"],
            "provenance_graph": {"edges": []},
        }

        db.save_state(
            user_id,
            chat_id,
            payload["info_need_state"],
            payload["retrieved_tables"],
            payload["enumerated_table_ids"],
            payload["provenance_graph"],
        )

        info_need_state, retrieved, enumerated, prov = db.load_state(user_id, chat_id)
        self.assertEqual(info_need_state, payload["info_need_state"])


if __name__ == "__main__":
    unittest.main()
