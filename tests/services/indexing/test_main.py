import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../src")),
)

from logging import getLogger

import pneuma_seeker.services.indexing.main as indexing_main
from pneuma_seeker.services.indexing.connectors.base import SourceConnector
from pneuma_seeker.shared.config import Config
from typing import cast


class DummyDBAPI:
    def __init__(self, config, logger):
        self.logger = logger
        self.registered = None
        self.ingested = None

    def register_postgres_dataset(self, dataset_name, connection_string):
        self.registered = (dataset_name, connection_string)

    def ingest_dataset(self, dataset_name, tmpdir, metadata_path, overwrite):
        self.ingested = (dataset_name, tmpdir, metadata_path, overwrite)


class DummyLM:
    def __init__(self, config, logger):
        pass


class DummyRetriever:
    def __init__(self, user_id, chat_id, config, db_api, language_model_api):
        self.user_id = user_id
        self.chat_id = chat_id
        self.index_called = False
        self.index_with_existing_schema_summaries_called = False
        self.indexed_docs = None
        self.existing_schema_summaries = None

    def index(self, documents, overwrite):
        self.index_called = True
        self.indexed_docs = documents

    def index_with_existing_schema_summaries(
        self, documents, existing_schema_summaries
    ):
        self.index_with_existing_schema_summaries_called = True
        self.indexed_docs = documents
        self.existing_schema_summaries = existing_schema_summaries


class DummyMetadataStore:
    def __init__(self):
        self.started_runs = []
        self.succeeded = None
        self.failed = None

    def record_run_started(self, dataset_name, source_type, source_config, snapshot_id):
        run_id = f"run-{len(self.started_runs)+1}"
        self.started_runs.append({"id": run_id, "dataset": dataset_name})
        return run_id

    def mark_run_succeeded(self, run_id, indexed_stream_count, indexed_table_count):
        self.succeeded = (run_id, indexed_stream_count, indexed_table_count)

    def mark_run_failed(self, run_id, reason):
        self.failed = (run_id, reason)

    def get_latest_run(self, dataset_name):
        return {"id": "latest", "dataset": dataset_name}

    def close(self):
        pass


class TestIndexingService(unittest.TestCase):
    def setUp(self):
        # Patch module-level dependencies so IndexingService doesn't create real DB/LM/retriever
        indexing_main.DBAPI = DummyDBAPI
        indexing_main.LanguageModelAPI = DummyLM
        indexing_main.PneumaRetriever = DummyRetriever
        indexing_main.IndexingMetadataStore = DummyMetadataStore

        self.logger = getLogger("test")
        self.config = Config()

    def _make_tmp_csv_dir(self):
        tmpdir = tempfile.mkdtemp()
        # top-level CSVs
        with open(os.path.join(tmpdir, "users.csv"), "w") as f:
            f.write("id,name\n1,Alice\n2,Bob\n")
        with open(os.path.join(tmpdir, "orders.csv"), "w") as f:
            f.write("order_id,amount\n10,100\n")

        nested = os.path.join(tmpdir, "nested")
        os.makedirs(nested, exist_ok=True)
        with open(os.path.join(nested, "users.csv"), "w") as f:
            f.write("id,name\n3,Carol\n")

        return tmpdir

    def tearDown(self):
        # nothing global to clean here
        pass

    def test_register_and_instantiate_custom_connector(self):
        service = indexing_main.IndexingService(self.config, self.logger)

        class FakeConnector(SourceConnector):
            def __init__(self, cfg):
                self.cfg = cfg

            @property
            def source_type(self) -> str:
                return "fake"

            def check_connection(self):
                return True

            def discover(self):
                return []

            def read(self, stream):  # type: ignore
                return iter([])

        service.register_connector("fake", FakeConnector)
        inst = service.instantiate_connector({"type": "fake", "x": 1})
        self.assertIsInstance(inst, FakeConnector)

    def test_index_dataset_csv_calls_retriever_and_ingest(self):
        tmpdir = self._make_tmp_csv_dir()
        try:
            service = indexing_main.IndexingService(self.config, self.logger)

            # ensure metadata_store and db_api are the dummy instances we expect
            self.assertIsInstance(service.metadata_store, DummyMetadataStore)
            self.assertIsInstance(service.db_api, DummyDBAPI)

            connector_config = {"type": "csv", "directory_path": tmpdir}

            run_id = service.index_dataset("mydataset", connector_config)

            # run should be recorded and succeeded
            self.assertIsNotNone(run_id)
            self.assertIsNotNone(
                cast(DummyMetadataStore, service.metadata_store).succeeded
            )

            # retriever should have been called
            retriever = cast(DummyRetriever, service.retriever)
            self.assertTrue(
                retriever.index_called
                or retriever.index_with_existing_schema_summaries_called
            )

            # ingest_dataset should have been called on the dummy DBAPI
            dbapi = cast(DummyDBAPI, service.db_api)
            self.assertIsNotNone(dbapi.ingested)
            self.assertEqual(dbapi.ingested[0], "mydataset")  # type: ignore
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
