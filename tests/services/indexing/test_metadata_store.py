import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../src"))
)

from pneuma_seeker.services.indexing.metadata_store import (
    IndexingMetadataStore,
    IndexingStatus,
)


class TestIndexingMetadataStore(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = Path(self.tmpdir) / "indexing.db"
        self.store = IndexingMetadataStore(db_path=str(self.db_path))

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_record_run_started_and_get_run(self):
        run_id = self.store.record_run_started(
            dataset_name="ds1",
            source_type="csv",
            source_config={"path": "/data"},
            snapshot_id="snap-1",
        )
        self.assertIsInstance(run_id, str)

        row = self.store.get_run(run_id)
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row["run_id"], run_id)
        self.assertEqual(row["dataset_name"], "ds1")
        self.assertEqual(row["source_type"], "csv")
        # source_config_json should be a JSON string equal to the dumped dict
        self.assertEqual(json.loads(row["source_config_json"]), {"path": "/data"})
        self.assertEqual(row["snapshot_id"], "snap-1")
        self.assertEqual(row["status"], IndexingStatus.RUNNING.value)

    def test_mark_run_succeeded_and_failed(self):
        run_id = self.store.record_run_started(
            dataset_name="ds2",
            source_type="api",
            source_config={"url": "https://example"},
            snapshot_id="snap-2",
        )

        # Mark succeeded
        self.store.mark_run_succeeded(
            run_id, indexed_stream_count=3, indexed_table_count=2
        )
        row = self.store.get_run(run_id)
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row["status"], IndexingStatus.SUCCEEDED.value)
        self.assertEqual(row["indexed_stream_count"], 3)
        self.assertEqual(row["indexed_table_count"], 2)

        # Start another run and mark failed
        run_id2 = self.store.record_run_started(
            dataset_name="ds2",
            source_type="api",
            source_config={"url": "https://example"},
            snapshot_id="snap-3",
        )
        self.store.mark_run_failed(run_id2, "some error")
        row2 = self.store.get_run(run_id2)
        self.assertIsNotNone(row2)
        assert row2 is not None
        self.assertEqual(row2["status"], IndexingStatus.FAILED.value)
        self.assertEqual(row2["error_message"], "some error")

    def test_get_latest_run(self):
        # Start two runs for the same dataset and ensure latest is returned
        rid1 = self.store.record_run_started(
            dataset_name="latest_ds",
            source_type="s1",
            source_config={"k": 1},
            snapshot_id="a",
        )
        rid2 = self.store.record_run_started(
            dataset_name="latest_ds",
            source_type="s2",
            source_config={"k": 2},
            snapshot_id="b",
        )

        latest = self.store.get_latest_run("latest_ds")
        self.assertIsNotNone(latest)
        assert latest is not None
        self.assertEqual(latest["run_id"], rid2)
        self.assertEqual(latest["source_type"], "s2")

    def test_db_file_created(self):
        # Ensure the db file was created at the provided path
        self.assertTrue(self.db_path.exists())


if __name__ == "__main__":
    unittest.main()
