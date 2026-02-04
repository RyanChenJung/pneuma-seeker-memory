# services/db/main.py
import json
import os
from logging import Logger
from pathlib import Path

import duckdb
import pandas as pd
from pandas import DataFrame
from pneuma_seeker.shared.schemas.db.table_type import TableType
from pneuma_seeker.shared.str_processor import clean_column_table_name
from tqdm import tqdm


class PneumaDB:
    """
    PneumaDB manages:
      - dataset databases (one .db per dataset)
      - per-user workspace databases (one .db per user/chat)
      - external tables (uploaded by users)
      - intermediate & target tables
      - metadata tracking

    Notes / design choices:
    - Each dataset database file uses the `.db` extension.
    - Each workspace uses its own DB file (ws_{user}_{chat}.db).
    """

    def __init__(
        self,
        logger: Logger,
        dataset_db_path: str | None = None,
        workspace_db_path: str | None = None,
    ):
        self.logger = logger

        if dataset_db_path:
            self.dataset_db_path = Path(__file__).resolve().parent / dataset_db_path
        else:
            self.dataset_db_path = Path(__file__).resolve().parent / "datasets"

        if workspace_db_path:
            self.workspace_db_path = Path(__file__).resolve().parent / workspace_db_path
        else:
            self.workspace_db_path = Path(__file__).resolve().parent / "workspaces"

        os.makedirs(self.dataset_db_path, exist_ok=True)
        os.makedirs(self.workspace_db_path, exist_ok=True)

        self._conn_cache: dict[tuple[str, str], duckdb.DuckDBPyConnection] = {}

    # ------------------------------------------------------------------
    # Dataset Management (one .db per dataset)
    # ------------------------------------------------------------------
    def get_dataset_connection(self, dataset_name: str, read_only: bool = True):
        """Returns a DuckDB connection to the dataset DB file (uses .db extension)."""
        dataset_db_file = self.dataset_db_path / f"{dataset_name}.db"
        con = duckdb.connect(database=dataset_db_file.as_posix(), read_only=read_only)
        return con

    def register_dataset_table(self, dataset_name: str, dataset_path: str):
        """
        Stores CSV files inside the dataset's own DuckDB file.
        - table name = cleaned(Path(csv_file).stem)
        - cleans column names
        - only reads file once for ingestion (fast path)
        """
        dataset_db_file = self.dataset_db_path / f"{dataset_name}.db"
        os.makedirs(dataset_db_file.parent, exist_ok=True)

        dataset_con = self.get_dataset_connection(dataset_name, read_only=False)

        try:
            for table_file_name in tqdm(sorted(os.listdir(dataset_path))):
                if not table_file_name.lower().endswith(".csv"):
                    continue

                file_path = (Path(dataset_path) / table_file_name).as_posix()
                table_stem = Path(table_file_name).stem
                cleaned_table_name = clean_column_table_name(table_stem)

                # Read header only to get original column names (fast)
                try:
                    header_df = pd.read_csv(file_path, nrows=0)
                    original_cols = list(header_df.columns)
                except Exception:
                    # Fallback: let DuckDB auto-detect and ingest (still fine)
                    original_cols = None

                if original_cols:
                    cleaned_cols = self.__dedupe_columns(
                        [clean_column_table_name(c) for c in original_cols]
                    )
                    select_clause = ", ".join(
                        f'"{orig}" AS "{cleaned}"'
                        for orig, cleaned in zip(original_cols, cleaned_cols)
                    )

                    dataset_con.execute(
                        f"""
                        CREATE OR REPLACE TABLE "{cleaned_table_name}" AS
                        SELECT {select_clause}
                        FROM read_csv_auto(
                            '{file_path}',
                            HEADER=TRUE,
                            IGNORE_ERRORS=TRUE,
                            STRICT_MODE=FALSE,
                            NULL_PADDING=TRUE,
                            SAMPLE_SIZE=100_000,
                            PARALLEL=FALSE
                        );
                        """
                    )
                else:
                    # If we couldn't get header with pandas, let DuckDB create the table
                    dataset_con.execute(
                        f"""
                        CREATE OR REPLACE TABLE "{cleaned_table_name}" AS
                        SELECT * FROM read_csv_auto(
                            '{file_path}',
                            HEADER=TRUE,
                            IGNORE_ERRORS=TRUE,
                            STRICT_MODE=FALSE,
                            NULL_PADDING=TRUE,
                            SAMPLE_SIZE=100_000,
                            PARALLEL=FALSE
                        );
                        """
                    )
        finally:
            dataset_con.close()

    def __dedupe_columns(self, cols):
        seen = {}
        result = []
        for c in cols:
            if c not in seen:
                seen[c] = 0
                result.append(c)
            else:
                seen[c] += 1
                result.append(f"{c}_{seen[c]}")
        return result

    # ------------------------------------------------------------------
    # Workspace DB Management (one .db per user/chat)
    # ------------------------------------------------------------------
    def get_workspace_db_connection(self, user_id: str, chat_id: str):
        """
        Returns a cached DuckDB connection for the workspace.
        - If connection is new, create it and initialize metadata table.
        - Caller must not close the returned connection (use close_workspace_connection).
        """
        key = (user_id, chat_id)
        if key in self._conn_cache:
            return self._conn_cache[key]

        ws_db_file = self.__get_workspace_db_file_path(user_id, chat_id)
        os.makedirs(ws_db_file.parent, exist_ok=True)

        workspace_db_con = duckdb.connect(
            database=ws_db_file.as_posix(), read_only=False
        )

        workspace_db_con.execute(
            """
            CREATE TABLE IF NOT EXISTS metadata_tables (
                table_name TEXT PRIMARY KEY,
                table_type TEXT,
                origin_table TEXT,
                created_at TIMESTAMP DEFAULT now()
            );
            """
        )
        workspace_db_con.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_state (
                info_need_state_json TEXT,
                retrieved_tables_json TEXT,
                provenance_graph_json TEXT,
                ts TIMESTAMP DEFAULT now()
            );
            """
        )

        self._conn_cache[key] = workspace_db_con
        return workspace_db_con

    def __get_workspace_db_file_path(self, user_id: str, chat_id: str) -> Path:
        """Returns the Path to the workspace DB file for the given user/chat."""
        user_dir = self.workspace_db_path / user_id
        chat_dir = user_dir / chat_id
        chat_dir.mkdir(parents=True, exist_ok=True)
        return chat_dir / "ws.db"

    def close_workspace_connection(self, user_id: str, chat_id: str):
        """Closes and removes a cached workspace connection if it exists."""
        key = (user_id, chat_id)
        con = self._conn_cache.pop(key, None)
        if con:
            try:
                con.close()
            except Exception:
                pass

    def close_all_connections(self):
        """Closes all cached workspace connections."""
        for con in list(self._conn_cache.values()):
            try:
                con.close()
            except Exception:
                pass
        self._conn_cache.clear()

    # ------------------------------------------------------------------
    # Register External Tables (from DataFrame)
    # ------------------------------------------------------------------
    def register_external_table(
        self, user_id: str, chat_id: str, table_name: str, df: DataFrame
    ):
        """
        Uploads an external table (DataFrame) into the workspace DB.
        """
        self.logger.info(f"[PneumaDB] Registering external table: {table_name}")
        workspace_db_con = self.get_workspace_db_connection(user_id, chat_id)
        cleaned_table = clean_column_table_name(table_name)

        # Register DF temporarily with DuckDB, create persistent table, then unregister
        workspace_db_con.register("tmp_upload_df", df)
        try:
            workspace_db_con.execute(
                f'CREATE OR REPLACE TABLE "{cleaned_table}" AS SELECT * FROM tmp_upload_df;'
            )
        finally:
            # DuckDB's Python API supports unregister; use try/except to be safe
            try:
                workspace_db_con.unregister("tmp_upload_df")
            except Exception:
                pass

        self.__insert_metadata(
            workspace_db_con=workspace_db_con,
            table_name=cleaned_table,
            table_type=TableType.EXTERNAL.value,
            origin_table="(upload)",
        )
        self.__checkpoint_connection(workspace_db_con)

    def register_temporary_table(
        self,
        user_id: str,
        chat_id: str,
        table_name: str,
        df: pd.DataFrame,
    ) -> None:
        """Registers a temporary table in the workspace DB."""
        con = self.get_workspace_db_connection(user_id, chat_id)
        con.register(table_name, df)

    def unregister_temporary_table(
        self,
        user_id: str,
        chat_id: str,
        table_name: str,
    ) -> None:
        con = self.get_workspace_db_connection(user_id, chat_id)
        try:
            con.unregister(table_name)
        except duckdb.CatalogException:
            pass

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
        workspace_db_con = self.get_workspace_db_connection(user_id, chat_id)
        rows = workspace_db_con.execute(
            "SELECT table_name FROM metadata_tables WHERE table_type = ?;",
            [table_type.value],
        ).fetchall()

        tables_dict = {}
        for (table_name,) in rows:
            if use_sample:
                df = workspace_db_con.execute(
                    f'SELECT * FROM "{table_name}" LIMIT {int(sample_size)}'
                ).fetchdf()
            else:
                df = workspace_db_con.execute(f'SELECT * FROM "{table_name}"').fetchdf()
            tables_dict[table_name] = df

        return tables_dict

    # ------------------------------------------------------------------
    # Dataset DB Linking into Workspace DB
    # ------------------------------------------------------------------
    def link_dataset_tables(self, user_id: str, chat_id: str, dataset_name: str):
        """
        Attach a dataset DB into the workspace connection under a safe alias.
        The alias is the cleaned dataset_name.
        This is idempotent (no error if already attached).
        """
        self.logger.info(f"[PneumaDB] Linking dataset '{dataset_name}' into workspace.")
        workspace_db_con = self.get_workspace_db_connection(user_id, chat_id)
        dataset_db_file = self.dataset_db_path / f"{dataset_name}.db"
        if not dataset_db_file.exists():
            raise FileNotFoundError(
                f"Dataset DB not found: {dataset_db_file.as_posix()}"
            )

        alias = clean_column_table_name(dataset_name)

        # Check attached databases (PRAGMA database_list)
        attached = workspace_db_con.execute("PRAGMA database_list").fetchdf()
        # `name` column contains aliases; defensive checks
        if "name" in attached.columns and alias in attached["name"].tolist():
            return  # already attached

        # Attach read-only
        workspace_db_con.execute(
            f"ATTACH DATABASE '{dataset_db_file.as_posix()}' AS \"{alias}\" (READ_ONLY)"
        )

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
        self.logger.info(f"[PneumaDB] Registering table: {table_name}")
        workspace_db_con = self.get_workspace_db_connection(user_id, chat_id)
        cleaned_table = clean_column_table_name(table_name)

        workspace_db_con.register("tmp_result_df", df)
        try:
            workspace_db_con.execute(
                f'CREATE OR REPLACE TABLE "{cleaned_table}" AS SELECT * FROM tmp_result_df;'
            )
        finally:
            try:
                workspace_db_con.unregister("tmp_result_df")
            except Exception:
                pass

        self.__insert_metadata(
            workspace_db_con=workspace_db_con,
            table_name=cleaned_table,
            table_type=table_type.value,
            origin_table="(generated)",
        )
        self.__checkpoint_connection(workspace_db_con)

    # ------------------------------------------------------------------
    # Query Execution
    # ------------------------------------------------------------------
    def execute_query(
        self, user_id: str, chat_id: str, sql: str, sql_params: dict = {}
    ) -> DataFrame:
        """
        Execute SQL in the context of the workspace DB connection.
        Note: workspace connection is cached so ATTACH persists between calls.
        """
        # self.logger.info(f"[PneumaDB] Executing workspace query:\n{sql}")
        workspace_db_con = self.get_workspace_db_connection(user_id, chat_id)
        return workspace_db_con.execute(sql, sql_params).fetchdf()

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
        self.logger.info(f"[PneumaDB] Executing query into table: {dest_table}")
        if not query.strip().lower().startswith("select"):
            raise ValueError(
                "Only SELECT queries are allowed for execute_query_into_table()."
            )

        workspace_db_con = self.get_workspace_db_connection(user_id, chat_id)
        cleaned_table = clean_column_table_name(dest_table)

        create_query = f'CREATE OR REPLACE TABLE "{cleaned_table}" AS {query}'
        workspace_db_con.execute(create_query)

        # Update metadata (store cleaned table name)
        self.__insert_metadata(
            workspace_db_con=workspace_db_con,
            table_name=cleaned_table,
            table_type=table_type.value,
            origin_table="(query)",
        )

        sample_query = f'SELECT * FROM "{cleaned_table}" LIMIT {int(sample_size)}'
        self.__checkpoint_connection(workspace_db_con)
        return workspace_db_con.execute(sample_query).fetchdf()

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
        self.logger.info(f"[PneumaDB] Deleting all tables of type: {table_type.value}")
        workspace_db_con = self.get_workspace_db_connection(user_id, chat_id)

        rows = workspace_db_con.execute(
            "SELECT table_name FROM metadata_tables WHERE table_type = ?;",
            [table_type.value],
        ).fetchall()

        # Drop each table safely (quote names)
        for (table_name,) in rows:
            workspace_db_con.execute(f'DROP TABLE IF EXISTS "{table_name}";')

        # Remove metadata entries
        workspace_db_con.execute(
            "DELETE FROM metadata_tables WHERE table_type = ?;", [table_type.value]
        )

        return len(rows)

    # ------------------------------------------------------------------
    # Helpers - metadata upsert
    # ------------------------------------------------------------------
    def __insert_metadata(
        self,
        workspace_db_con: duckdb.DuckDBPyConnection,
        table_name: str,
        table_type: str,
        origin_table: str,
    ):
        """
        Upsert metadata row for a table_name (we store the cleaned table name).
        Uses delete + insert for portability.
        """
        self.logger.info(f"[PneumaDB] Inserting metadata for table: {table_name}")
        # ensure table_name is the cleaned (actual) table name
        cleaned_table_name = clean_column_table_name(table_name)

        workspace_db_con.execute(
            "DELETE FROM metadata_tables WHERE table_name = ?;", [cleaned_table_name]
        )
        workspace_db_con.execute(
            """
            INSERT INTO metadata_tables (table_name, table_type, origin_table)
            VALUES (?, ?, ?);
            """,
            [cleaned_table_name, table_type, origin_table],
        )

    # ------------------------------------------------------------------
    # Helper - checkpoint connection
    # ------------------------------------------------------------------
    def __checkpoint_connection(self, con: duckdb.DuckDBPyConnection):
        """
        Forces DuckDB to flush the WAL to the main .db file.
        Safe for cached connections; does not close the connection.
        """
        try:
            con.execute("CALL checkpoint();")
        except Exception as e:
            self.logger.warning(f"[PneumaDB] Failed to checkpoint connection: {e}")

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
        con = self.get_workspace_db_connection(user_id, chat_id)

        con.execute("DELETE FROM chat_state")

        con.execute(
            """
            INSERT INTO chat_state (
                info_need_state_json,
                retrieved_tables_json,
                provenance_graph_json,
                ts
            )
            VALUES (?, ?, ?, now())
            """,
            (
                json.dumps(
                    {
                        "info_need_state": info_need_state_json,
                        "enumerated_table_ids": enumerated_table_ids,
                    }
                ),
                json.dumps(retrieved_tables_json),
                json.dumps(provenance_graph_json),
            ),
        )

        self.__checkpoint_connection(con)

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
        con = self.get_workspace_db_connection(user_id, chat_id)

        row = con.execute(
            """
            SELECT info_need_state_json, retrieved_tables_json, provenance_graph_json
            FROM chat_state
            ORDER BY ts DESC
            LIMIT 1
            """
        ).fetchone()

        if not row:
            return {}, [], [], {}

        state_json, retr_json, prov_json = row

        state_blob = json.loads(state_json)

        return (
            state_blob.get("info_need_state", {}),
            json.loads(retr_json),
            state_blob.get("enumerated_table_ids", []),
            json.loads(prov_json),
        )
