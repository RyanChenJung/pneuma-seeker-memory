# tests/core/shared/test_table_store.py
import os
import sys
import unittest
import tempfile
import shutil
import pandas as pd

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../src"))
)

from pneuma_seeker.core.shared.table_store.table_store import (
    TableStore,
    TableType,
    clean_column_table_name,
)


class TableStoreTests(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for isolated DB files
        self.tmpdir = tempfile.mkdtemp()
        self.user_id = "user123"
        self.chat_id = "chat999"

        self.store = TableStore(base_path=self.tmpdir)

    def tearDown(self):
        try:
            self.store.close()
        except:
            pass
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_initialization_and_metadata_table(self):
        """Ensures DB file is created and metadata table exists."""
        self.assertTrue(os.path.exists(self.store.base_path))
        tables = self.store.list_tables(self.user_id, self.chat_id)["name"].tolist()
        self.assertIn("table_registry", tables)
    def test_clean_column_table_name(self):
        """Tests the normalization function for table/column names."""
        name = "My Table-(Version 2)"
        cleaned = clean_column_table_name(name)
        self.assertEqual(cleaned, "my_table_version_2")

    def test_create_intermediate_table(self):
        """Tests creating an intermediate table with auto metadata registration."""
        df = pd.DataFrame({"a": [1, 2, 3]})
        table_name = "Raw Table (A)"
        cleaned = self.store.create_or_replace(
            self.user_id,
            self.chat_id,
            table_name,
            df,
            table_type=TableType.INTERMEDIATE,
        )
        self.assertEqual(cleaned, "raw_table_a")

        # check table exists
        self.assertTrue(self.store.table_exists(self.user_id, self.chat_id, cleaned))

        # metadata correct
        meta = self.store.execute(
            self.user_id,
            self.chat_id,
            "SELECT table_type FROM table_registry WHERE table_name = ?",
            params=[cleaned],
        ).fetchdf()

        self.assertEqual(meta.iloc[0]["table_type"], "intermediate")

    def test_create_target_table(self):
        """Tests creating a target table with metadata."""
        df = pd.DataFrame({"x": [10, 20, 30]})
        table_name = "Final Result!"

        cleaned = self.store.create_or_replace(
            self.user_id,
            self.chat_id,
            table_name,
            df,
            table_type=TableType.TARGET,
        )
        self.assertEqual(cleaned, "final_result")

        # check table exists
        self.assertTrue(self.store.table_exists(self.user_id, self.chat_id, cleaned))
        # metadata correct
        meta = self.store.execute(
            self.user_id,
            self.chat_id,
            "SELECT table_type FROM table_registry WHERE table_name = ?",
            params=[cleaned],
        ).fetchdf()

        self.assertEqual(meta.iloc[0]["table_type"], "target")

    def test_read_table_with_sampling(self):
        """Tests reading a table with sampling enabled."""
        df = pd.DataFrame({"a": list(range(20))})
        t = self.store.create_or_replace(
            self.user_id,
            self.chat_id,
            "sample_test",
            df,
            table_type=TableType.INTERMEDIATE,
        )

        # normal read
        full = self.store.read_table(
            self.user_id, self.chat_id, t, sample_only=False
        ).fetchdf()
        self.assertEqual(len(full), 20)

        # sampled read
        sampled = self.store.read_table(
            self.user_id, self.chat_id, t, sample_only=True, sample_size=5
        ).fetchdf()
        self.assertEqual(len(sampled), 5)

    def test_list_tables(self):
        """Tests listing all tables."""
        df = pd.DataFrame({"a": [1]})
        t1 = self.store.create_or_replace(
            self.user_id,
            self.chat_id,
            "T1",
            df,
            table_type=TableType.INTERMEDIATE,
        )
        t2 = self.store.create_or_replace(
            self.user_id,
            self.chat_id,
            "T2",
            df,
            table_type=TableType.INTERMEDIATE,
        )

        tables = self.store.list_tables(self.user_id, self.chat_id)
        self.assertIn(t1, tables["name"].tolist())
        self.assertIn(t2, tables["name"].tolist())

    def test_table_exists(self):
        """Tests table existence checking."""
        df = pd.DataFrame({"a": [1]})
        t = self.store.create_or_replace(
            self.user_id,
            self.chat_id,
            "exists_test",
            df,
            table_type=TableType.INTERMEDIATE,
        )

        self.assertTrue(self.store.table_exists(self.user_id, self.chat_id, t))
        self.assertFalse(
            self.store.table_exists(self.user_id, self.chat_id, "not_here")
        )

    def test_drop_table(self):
        """Tests dropping a table."""
        df = pd.DataFrame({"a": [1]})
        t = self.store.create_or_replace(
            self.user_id,
            self.chat_id,
            "drop_me",
            df,
            table_type=TableType.INTERMEDIATE,
        )

        self.assertTrue(self.store.table_exists(self.user_id, self.chat_id, t))
        self.store.drop_table(self.user_id, self.chat_id, t)
        self.assertFalse(self.store.table_exists(self.user_id, self.chat_id, t))

    def test_drop_all_tables(self):
        """Tests dropping all non-metadata tables."""
        df = pd.DataFrame({"a": [1]})
        t1 = self.store.create_or_replace(
            self.user_id,
            self.chat_id,
            "AA",
            df,
            table_type=TableType.INTERMEDIATE,
        )
        t2 = self.store.create_or_replace(
            self.user_id,
            self.chat_id,
            "BB",
            df,
            table_type=TableType.INTERMEDIATE,
        )

        self.store.drop_all_tables(self.user_id, self.chat_id)

        # metadata must remain
        tables = self.store.list_tables(self.user_id, self.chat_id)["name"].tolist()
        self.assertIn("table_registry", tables)
        self.assertNotIn(t1, tables)
        self.assertNotIn(t2, tables)

    def test_execute_with_and_without_params(self):
        """Tests generic SQL execution path."""
        df = pd.DataFrame({"a": [1, 2, 3]})
        t = self.store.create_or_replace(
            self.user_id,
            self.chat_id,
            "exec_test",
            df,
            table_type=TableType.INTERMEDIATE,
        )
        res1 = self.store.execute(
            self.user_id, self.chat_id, f"SELECT COUNT(*) AS c FROM {t}"
        )
        self.assertEqual(res1.fetchdf().iloc[0]["c"], 3)

        res2 = self.store.execute(
            self.user_id,
            self.chat_id,
            f"SELECT COUNT(*) AS c FROM {t} WHERE a > ?",
            params=(1,),
        )
        self.assertEqual(res2.fetchdf().iloc[0]["c"], 2)


if __name__ == "__main__":
    unittest.main()
