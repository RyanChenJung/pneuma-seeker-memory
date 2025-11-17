# src/pneuma_seeker/core/shared/table_store/table_store.py
import duckdb
import os
import re
from pathlib import Path
from datetime import datetime, timezone
from enum import Enum

from pandas import DataFrame


def clean_column_table_name(name: str) -> str:
    """Cleans and normalizes column/table names."""
    name = name.lower()
    name = name.replace("-", "_").replace(" ", "_")
    name = name.replace("(", "_").replace(")", "_")
    name = re.sub(r"[^0-9a-z_]", "_", name)
    name = re.sub(r"_+", "_", name)
    name = name.strip("_")
    return name


class TableType(Enum):
    INTERMEDIATE = "intermediate"
    TARGET = "target"


class TableStore:
    """
    A singleton-like manager that handles DuckDB-backed intermediate/product tables.

    Database file is determined *per operation* using user_id and chat_id:
        intermediate_tables/{user_id}_{chat_id}.db

    No instance-level binding to any specific user/chat.
    """

    def __init__(self, base_path: str = "intermediate_tables"):
        self.base_path = Path(__file__).parent / base_path
        self.base_path.mkdir(parents=True, exist_ok=True)

        # Key: "{user_id}_{chat_id}" -> duckdb.DuckDBPyConnection
        self._connections: dict[str, duckdb.DuckDBPyConnection] = {}

    def _get_connection(self, user_id: str, chat_id: str):
        """Returns a DuckDB connection to the appropriate per-user/chat DB."""
        key = f"{user_id}_{chat_id}"
        if key in self._connections:
            return self._connections[key]

        db_path = os.path.join(self.base_path, f"{user_id}_{chat_id}.db")
        con = duckdb.connect(db_path)
        self.__init_metadata_table(con)
        self._connections[key] = con
        return con

    def close(self, user_id: str | None = None, chat_id: str | None = None):
        """Closes cached DuckDB connections.

        - If both `user_id` and `chat_id` are provided, close only that connection.
        - If neither is provided, close all cached connections.
        """
        if user_id is not None and chat_id is not None:
            key = f"{user_id}_{chat_id}"
            con = self._connections.pop(key, None)
            if con is not None:
                try:
                    con.close()
                except Exception:
                    pass
            return

        # Close all
        keys = list(self._connections.keys())
        for k in keys:
            con = self._connections.pop(k, None)
            if con is not None:
                try:
                    con.close()
                except Exception:
                    pass

    def execute(self, user_id: str, chat_id: str, query: str, params=None):
        con = self._get_connection(user_id, chat_id)
        if params:
            return con.execute(query, params)
        return con.execute(query)

    def _select_from_table(
        self,
        con,
        table_name: str,
        sample_only: bool = False,
        sample_size: int | None = None,
    ):
        cleaned = clean_column_table_name(table_name)
        query = f"SELECT * FROM {cleaned}"

        if sample_only:
            if sample_size is None or sample_size <= 0:
                sample_size = 5
            query += f" LIMIT {sample_size}"

        return con.execute(query)

    def create_or_replace(
        self,
        user_id: str,
        chat_id: str,
        table_name: str,
        df: DataFrame,
        table_type: TableType,
    ):
        """
        Creates or replaces a table from a DataFrame and updates registry.
        table_type: "intermediate" or "target"
        """
        con = self._get_connection(user_id, chat_id)
        cleaned = clean_column_table_name(table_name)
        con.execute(f"CREATE OR REPLACE TABLE {cleaned} AS SELECT * FROM df")
        self.register_table(con, cleaned, table_type)
        return cleaned

    def read_table(
        self,
        user_id: str,
        chat_id: str,
        table_name: str,
        sample_only: bool = False,
        sample_size: int | None = None,
    ):
        con = self._get_connection(user_id, chat_id)
        return self._select_from_table(con, table_name, sample_only, sample_size)

    def read_table_df(
        self,
        user_id: str,
        chat_id: str,
        table_name: str,
        sample_only: bool = False,
        sample_size: int | None = None,
    ):
        con = self._get_connection(user_id, chat_id)
        rel = self._select_from_table(con, table_name, sample_only, sample_size)
        return rel.fetchdf()

    def drop_table(self, user_id: str, chat_id: str, table_name: str):
        con = self._get_connection(user_id, chat_id)
        cleaned = clean_column_table_name(table_name)
        con.execute(f"DROP TABLE IF EXISTS {cleaned}")
        self.unregister_table(con, cleaned)

    def table_exists(self, user_id: str, chat_id: str, table_name: str) -> bool:
        con = self._get_connection(user_id, chat_id)
        cleaned = clean_column_table_name(table_name)
        df = con.execute(
            """
            SELECT table_name FROM information_schema.tables WHERE table_name = ?
            """,
            [cleaned],
        ).fetchdf()
        return not df.empty

    def __init_metadata_table(self, con):
        """Ensures we have a metadata table describing all known tables."""
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS table_registry (
                table_name TEXT PRIMARY KEY,
                table_type TEXT CHECK(table_type IN ('intermediate', 'target')),
                created_at TIMESTAMP DEFAULT now()
            )
            """
        )

    def register_table(self, con, table_name: str, table_type: TableType):
        """Registers a table in the metadata registry."""
        con.execute(
            """
            DELETE FROM table_registry WHERE table_name = ?
            """,
            [table_name],
        )
        con.execute(
            """
            INSERT INTO table_registry(table_name, table_type, created_at)
            VALUES (?, ?, ?)
            """,
            (table_name, table_type.value, datetime.now(timezone.utc)),
        )

    def unregister_table(self, con, table_name: str):
        con.execute(
            """
            DELETE FROM table_registry WHERE table_name = ?
            """,
            [table_name],
        )

    def list_tables(self, user_id: str, chat_id: str):
        con = self._get_connection(user_id, chat_id)
        return con.execute("SHOW TABLES").fetchdf()

    def list_intermediate_tables(self, user_id: str, chat_id: str):
        con = self._get_connection(user_id, chat_id)
        return con.execute(
            """
            SELECT table_name FROM table_registry WHERE table_type = 'intermediate'
            """
        ).fetchdf()

    def list_target_tables(self, user_id: str, chat_id: str):
        con = self._get_connection(user_id, chat_id)
        return con.execute(
            """
            SELECT table_name FROM table_registry WHERE table_type = 'target'
            """
        ).fetchdf()

    def drop_intermediate_tables(self, user_id: str, chat_id: str):
        names = self.list_intermediate_tables(user_id, chat_id)
        for name in names["table_name"]:
            self.drop_table(user_id, chat_id, name)

    def drop_all_tables(self, user_id: str, chat_id: str):
        names = self.list_tables(user_id, chat_id)
        for name in names["name"]:
            # Never drop the metadata registry table
            if name == "table_registry":
                continue
            self.drop_table(user_id, chat_id, name)
