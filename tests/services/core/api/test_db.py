import logging
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import uuid

import pandas as pd

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../src"))
)

from pneuma_seeker.provenance.graph import ProvenanceGraph
from pneuma_seeker.services.core.api.db import DBAPI
from pneuma_seeker.shared.config import Config
from pneuma_seeker.shared.schemas.core.conductor import InformationNeedState
from pneuma_seeker.shared.schemas.core.ir_system import Table, RetrieverType


class TestDBAPIPersistence(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.config = Config()
        self.logger = logging.getLogger("test_db_api")

        self.config.DATA_SOURCES = ["test_dataset_db"]

        self.dbapi = DBAPI(self.config, self.logger)
        self.dbapi.pneuma_db.dataset_db_path = Path(
            os.path.join(self.tmpdir, "datasets")
        )
        self.dbapi.pneuma_db.workspace_db_path = Path(
            os.path.join(self.tmpdir, "workspaces")
        )
        os.makedirs(self.dbapi.pneuma_db.dataset_db_path, exist_ok=True)
        os.makedirs(self.dbapi.pneuma_db.workspace_db_path, exist_ok=True)

    def tearDown(self):
        try:
            self.dbapi.pneuma_db.close_all_connections()
        finally:
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _new_workspace(self):
        return f"user_{uuid.uuid4()}", f"chat_{uuid.uuid4()}"

    def test_save_and_load_state_T_entry(self):
        user_id, chat_id = self._new_workspace()

        # create a small dataframe and register as external table in workspace
        df = pd.DataFrame({"a": [1, 2, 3]})
        table_name = "t_state"

        os.makedirs(
            os.path.join(self.tmpdir, self.config.DATA_SOURCES[0]), exist_ok=True
        )
        df.to_csv(
            os.path.join(self.tmpdir, self.config.DATA_SOURCES[0], f"{table_name}.csv"),
            index=False,
        )
        self.dbapi.register_dataset_table(
            self.config.DATA_SOURCES[0],
            os.path.join(self.tmpdir, self.config.DATA_SOURCES[0]),
        )

        # Build InformationNeedState with T containing a Table entry referencing the uploaded table
        ins = InformationNeedState()
        t_doc = Table(
            doc_id=table_name,
            retriever_type=RetrieverType.PNEUMA_RETRIEVER,
            content=df,
            metadata={},
        )
        ins.T[table_name] = t_doc

        # Save state
        self.dbapi.save_state(
            user_id,
            chat_id,
            ins,
            retrieved_tables=[],
            enumerated_table_ids=[table_name],
            provenance_graph=ProvenanceGraph(self.logger),
        )

        # Load state back
        info_state, retrieved, enumerated, prov = self.dbapi.load_state(
            user_id, chat_id
        )

        self.assertIn(table_name, info_state.T.keys())
        loaded_table = info_state.T[table_name]
        self.assertIsInstance(loaded_table.content, pd.DataFrame)
        self.assertEqual(len(loaded_table.content), 3)

    def test_save_and_load_state_retrieved_tables_from_dataset(self):
        # Ensure there is a dataset matching config.DATA_SOURCES[0]
        dataset_name = self.config.DATA_SOURCES[0]
        ds_con = self.dbapi.pneuma_db.get_dataset_connection(
            dataset_name, read_only=False
        )
        try:
            # create a table inside the dataset DB
            ds_df = pd.DataFrame({"x": [10, 20]})
            ds_con.register("tmp_ds", ds_df)
            ds_con.execute(
                f'CREATE OR REPLACE TABLE "ds_table" AS SELECT * FROM tmp_ds;'
            )
            try:
                ds_con.unregister("tmp_ds")
            except Exception:
                pass
        finally:
            ds_con.close()

        # Prepare retrieved_tables list: a Table doc referencing the dataset table
        retrieved_doc = Table(
            doc_id="ds_table",
            retriever_type=RetrieverType.PNEUMA_RETRIEVER,
            content=pd.DataFrame(),
            metadata={},
        )

        user_id, chat_id = self._new_workspace()

        # Save state with retrieved_tables referencing a dataset table
        ins = InformationNeedState()
        self.dbapi.save_state(
            user_id,
            chat_id,
            ins,
            retrieved_tables=[retrieved_doc],
            enumerated_table_ids=[],
            provenance_graph=ProvenanceGraph(self.logger),
        )

        # Load state back; DBAPI.load_state should link the dataset and reconstruct retrieved_tables
        info_state, retrieved_tables, enumerated, prov = self.dbapi.load_state(
            user_id, chat_id
        )

        self.assertEqual(len(retrieved_tables), 1)
        self.assertIsInstance(retrieved_tables[0].content, pd.DataFrame)
        self.assertEqual(len(retrieved_tables[0].content), 2)


if __name__ == "__main__":
    unittest.main()
