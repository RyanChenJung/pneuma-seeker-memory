# services/core/api/db.py
from logging import Logger

import pandas as pd
from pandas import DataFrame

from pneuma_seeker.services.db.main import PneumaDB
from pneuma_seeker.shared.config import Config
from pneuma_seeker.shared.schemas.db.table_type import TableType


class DBAPI:
    """
    DBAPI communicates with DB Service for datasets and workspaces management.
    """

    def __init__(self, config: Config, logger: Logger) -> None:
        self.config = config
        self.logger = logger
        self.pneuma_db = PneumaDB(self.logger)

    # ------------------------------------------------------------------
    # Dataset Management (one .db per dataset)
    # ------------------------------------------------------------------
    def register_dataset_table(self, dataset_name: str, dataset_path: str):
        """
        Stores CSV files inside the dataset's own DuckDB file.
        - table name = cleaned(Path(csv_file).stem)
        - cleans column names
        - only reads file once for ingestion (fast path)
        """
        self.pneuma_db.register_dataset_table(dataset_name, dataset_path)

    # ------------------------------------------------------------------
    # Register External Tables (from DataFrame)
    # ------------------------------------------------------------------
    def register_external_table(
        self, user_id: str, chat_id: str, table_name: str, df: DataFrame
    ):
        """
        Uploads an external table (DataFrame) into the workspace DB.
        """
        self.pneuma_db.register_external_table(user_id, chat_id, table_name, df)

    def register_temporary_table(
        self,
        user_id: str,
        chat_id: str,
        table_name: str,
        df: pd.DataFrame,
    ) -> None:
        """Registers a temporary table in the workspace DB."""
        self.pneuma_db.register_temporary_table(
            user_id, chat_id, table_name, df
        )

    def unregister_temporary_table(
        self,
        user_id: str,
        chat_id: str,
        table_name: str,
    ) -> None:
        self.pneuma_db.unregister_temporary_table(user_id, chat_id, table_name)

    def get_tables_of_type_as_dfs(
        self,
        user_id: str,
        chat_id: str,
        table_type: TableType,
        use_sample: bool = False,
        sample_size: int = 5,
    ) -> dict[str, pd.DataFrame]:
        """
        Returns a dictionary of table_name -> DataFrame for all tables of the given type.
        If use_sample is True, returns only a sample of rows from each table.
        """
        return self.pneuma_db.get_tables_of_type_as_dfs(
            user_id, chat_id, table_type, use_sample, sample_size
        )

    # ------------------------------------------------------------------
    # Dataset DB Linking into Workspace DB
    # ------------------------------------------------------------------
    def link_dataset_tables(self, user_id: str, chat_id: str, dataset_name: str):
        """
        Attach a dataset DB into the workspace connection under a safe alias.
        The alias is the cleaned dataset_name.
        This is idempotent (no error if already attached).
        """
        self.pneuma_db.link_dataset_tables(user_id, chat_id, dataset_name)

    # ------------------------------------------------------------------
    # Intermediate & Target Tables Registration
    # ------------------------------------------------------------------
    def register_table(
        self,
        user_id: str,
        chat_id: str,
        table_name: str,
        df: DataFrame,
        table_type: TableType = TableType.INTERMEDIATE,
    ):
        """Stores an intermediate or target result (from pandas DataFrame)."""
        self.pneuma_db.register_table(
            user_id, chat_id, table_name, df, table_type
        )

    # ------------------------------------------------------------------
    # Query Execution
    # ------------------------------------------------------------------
    def execute_workspace_query(
        self, user_id: str, chat_id: str, sql: str, sql_params: dict = {}
    ) -> DataFrame:
        """
        Execute SQL in the context of the workspace DB connection.
        Note: workspace connection is cached so ATTACH persists between calls.
        """
        return self.pneuma_db.execute_workspace_query(user_id, chat_id, sql, sql_params)

    # ------------------------------------------------------------------
    # Execute SELECT query into intermediate table
    # ------------------------------------------------------------------
    def execute_query_into_table(
        self,
        user_id: str,
        chat_id: str,
        query: str,
        dest_table: str,
        sample_size: int = 5,
        table_type: TableType = TableType.INTERMEDIATE,
    ) -> DataFrame:
        """
        Executes a SQL SELECT query, saves its result into dest_table (overwriting if exists),
        and returns sample rows of the resulting table.

        For safety, `query` must start with SELECT (simple heuristic).
        """
        return self.pneuma_db.execute_query_into_table(
            user_id,
            chat_id,
            query,
            dest_table,
            sample_size,
            table_type,
        )

    # ------------------------------------------------------------------
    # Delete all tables of a specific type in workspace
    # ------------------------------------------------------------------
    def delete_all_tables_of_type(
        self, user_id: str, chat_id: str, table_type: TableType
    ):
        """
        Deletes all tables of the given table_type in a workspace DB, and
        removes the corresponding metadata entries.
        Returns number of tables removed (metadata rows).
        """
        return self.pneuma_db.delete_all_tables_of_type(
            user_id, chat_id, table_type
        )

    # ------------------------------------------------------------------
    # State Persistence (info_need_state, retrieved_tables, provenance graph)
    # ------------------------------------------------------------------
    def save_state(
        self,
        user_id: str,
        chat_id: str,
        info_need_state_json: dict,
        retrieved_tables_json: list[dict],
        enumerated_table_ids: list[str],
        provenance_graph_json: dict,
    ):
        """
        Saves the chat state into the chat_state table (overwrites previous).
        """
        self.pneuma_db.save_state(
            user_id,
            chat_id,
            info_need_state_json,
            retrieved_tables_json,
            enumerated_table_ids,
            provenance_graph_json,
        )

    def load_state(
        self,
        user_id: str,
        chat_id: str,
    ) -> tuple[dict, list[dict], list[str], dict]:
        """
        Loads the latest chat state from the chat_state table.
        Returns (info_need_state, retrieved_tables, enumerated_table_ids, provenance_graph).
        If no state is found, returns empty structures.
        """
        return self.pneuma_db.load_state(user_id, chat_id)