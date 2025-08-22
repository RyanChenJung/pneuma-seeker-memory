import os
from threading import Lock
from typing import Optional
import duckdb
import pandas as pd
from contextlib import contextmanager

from pneuma_seeker.table.representation.abstract_table import AbstractTable
from pneuma_seeker.table.representation.impl.df_table import DFTable
from pneuma_seeker.table.representation.metadata import Metadata, TableMetadataType
from pneuma_seeker.table.store.abstract_table_store import AbstractTableStore


class DuckDBTableStore(AbstractTableStore):
    def __init__(self, db_path: str):
        """Initializes a table store using DuckDB."""
        self.db_path = os.path.join(db_path, "store.duckdb")
        self.__lock = Lock()

        # Initialize database on first creation
        with self._get_connection() as conn:
            self._initialize_db(conn)

    @contextmanager
    def _get_connection(self):
        """Context manager for getting a database connection."""
        conn = None
        try:
            conn = duckdb.connect(self.db_path)
            yield conn
        finally:
            if conn:
                conn.close()

    def _initialize_db(self, conn: duckdb.DuckDBPyConnection):
        """Initialize database tables if they don't exist."""
        # Table for storing schema information
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schemas (
                schema_name VARCHAR PRIMARY KEY
            )
        """
        )

        # Table for storing table metadata
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS table_metadata (
                db_schema VARCHAR,
                table_id VARCHAR,
                metadata_type VARCHAR,
                metadata TEXT,
                PRIMARY KEY (db_schema, table_id, metadata_type)
            )
        """
        )

    def create_db_schema(self, db_schema_name: str) -> None:
        with self.__lock, self._get_connection() as conn:
            # Check if schema exists
            result = conn.execute(
                """
                SELECT schema_name FROM schemas 
                WHERE schema_name = ?
            """,
                [db_schema_name],
            ).fetchone()

            if result:
                raise ValueError(f"DB schema `{db_schema_name}` already exists.")

            # Create DuckDB schema and record it
            conn.execute(f"CREATE SCHEMA IF NOT EXISTS {db_schema_name}")
            conn.execute("INSERT INTO schemas VALUES (?)", [db_schema_name])

    def add_table(
        self,
        db_schema: str,
        table_id: str,
        table: AbstractTable,
        overwrite=False,
        checkpoint=False,
    ) -> None:
        if not isinstance(table, DFTable):
            raise ValueError("Only DFTable is supported in DuckDBTableStore")

        with self.__lock, self._get_connection() as conn:
            # Check if schema exists
            if not conn.execute(
                """
                SELECT 1 FROM schemas WHERE schema_name = ?
            """,
                [db_schema],
            ).fetchone():
                raise ValueError(f"DB schema `{db_schema}` does not exist.")

            table_name = f"{db_schema}.{table_id}"

            if overwrite:
                conn.execute(f"DROP TABLE IF EXISTS {table_name}")

            # Create table from DataFrame
            df = table.get_data()
            conn.register("temp_df", df)  # Register temporary table
            conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM temp_df")

    def get_table(self, db_schema: str, table_id: str) -> AbstractTable:
        with self.__lock, self._get_connection() as conn:
            table_name = f"{db_schema}.{table_id}"

            # Check if table exists
            if not conn.execute(
                f"""
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = ? AND table_name = ?
            """,
                [db_schema, table_id],
            ).fetchone():
                raise ValueError(f"Table `{table_id}` does not exist.")

            # Fetch data as DataFrame
            df = conn.execute(f"SELECT * FROM {table_name}").df()
            return DFTable(df)

    def delete_table(self, db_schema: str, table_id: str) -> None:
        with self.__lock, self._get_connection() as conn:
            table_name = f"{db_schema}.{table_id}"

            # Check if table exists
            if not conn.execute(
                f"""
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = ? AND table_name = ?
            """,
                [db_schema, table_id],
            ).fetchone():
                raise ValueError(f"Table `{table_id}` does not exist.")

            # Drop table and its metadata
            conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            conn.execute(
                """
                DELETE FROM table_metadata 
                WHERE db_schema = ? AND table_id = ?
            """,
                [db_schema, table_id],
            )

    def add_table_metadata(
        self,
        db_schema: str,
        table_id: str,
        metadata_type: TableMetadataType,
        metadata: str,
        overwrite: bool = False,
    ) -> None:
        with self.__lock, self._get_connection() as conn:
            if not overwrite:
                # Check if metadata exists
                existing = conn.execute(
                    """
                    SELECT 1 FROM table_metadata 
                    WHERE db_schema = ? AND table_id = ? AND metadata_type = ?
                """,
                    [db_schema, table_id, metadata_type.value],
                ).fetchone()

                if existing:
                    raise ValueError(
                        "Metadata already exists and `overwrite` is set to False."
                    )

            # Insert or replace metadata
            conn.execute(
                """
                INSERT OR REPLACE INTO table_metadata (db_schema, table_id, metadata_type, metadata)
                VALUES (?, ?, ?, ?)
            """,
                [db_schema, table_id, metadata_type.value, metadata],
            )

    def get_all_db_schemas(self) -> list[str]:
        with self.__lock, self._get_connection() as conn:
            result = conn.execute("SELECT schema_name FROM schemas").fetchall()
            return [r[0] for r in result]

    def check_if_table_exists(self, db_schema: str, table_id: str) -> bool:
        with self.__lock, self._get_connection() as conn:
            result = conn.execute(
                f"""
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = ? AND table_name = ?
            """,
                [db_schema, table_id],
            ).fetchone()
            return bool(result)

    def execute_sql_query(
        self, sql_query: str, tables_involved: Optional[dict[str, AbstractTable]] = None
    ) -> AbstractTable:
        """Execute SQL query directly on DuckDB."""
        with self.__lock, self._get_connection() as conn:
            # If tables_involved is provided, register them as temporary views
            if tables_involved:
                for table_id, table in tables_involved.items():
                    if not isinstance(table, DFTable):
                        raise ValueError("Only DFTable is supported")
                    conn.register(table_id.lower(), table.get_data())

            # Execute query and return result as DFTable
            result_df = conn.execute(sql_query).df()
            return DFTable(result_df)

    def load_checkpoint(self, db_path: Optional[str] = None):
        """Load checkpoint is a no-op for DuckDB as data is always persisted."""
        # DuckDB persists data automatically, so we don't need to implement this
        pass

    def checkpoint(self):
        """Checkpoint is a no-op for DuckDB as data is always persisted."""
        # DuckDB persists data automatically, so we don't need to implement this
        pass

    def rename_db_schema(self, db_schema_name: str, new_db_schema_name: str) -> None:
        with self.__lock, self._get_connection() as conn:
            # Check if source schema exists
            if not conn.execute(
                """
                SELECT 1 FROM schemas WHERE schema_name = ?
            """,
                [db_schema_name],
            ).fetchone():
                raise ValueError(f"DB schema `{db_schema_name}` does not exist.")

            # Check if target schema already exists
            if conn.execute(
                """
                SELECT 1 FROM schemas WHERE schema_name = ?
            """,
                [new_db_schema_name],
            ).fetchone():
                raise ValueError(f"DB schema `{new_db_schema_name}` already exists.")

            # Rename the schema in DuckDB
            conn.execute(
                f"ALTER SCHEMA {db_schema_name} RENAME TO {new_db_schema_name}"
            )

            # Update the schemas table
            conn.execute("DELETE FROM schemas WHERE schema_name = ?", [db_schema_name])
            conn.execute("INSERT INTO schemas VALUES (?)", [new_db_schema_name])

            # Update metadata references
            conn.execute(
                """
                UPDATE table_metadata 
                SET db_schema = ?
                WHERE db_schema = ?
            """,
                [new_db_schema_name, db_schema_name],
            )

    def delete_db_schema(self, db_schema_name: str) -> None:
        with self.__lock, self._get_connection() as conn:
            # Check if schema exists
            if not conn.execute(
                """
                SELECT 1 FROM schemas WHERE schema_name = ?
            """,
                [db_schema_name],
            ).fetchone():
                raise ValueError(f"DB schema `{db_schema_name}` does not exist.")

            # Drop the schema and all its tables
            conn.execute(f"DROP SCHEMA {db_schema_name} CASCADE")

            # Remove schema from schemas table
            conn.execute("DELETE FROM schemas WHERE schema_name = ?", [db_schema_name])

            # Clean up metadata
            conn.execute(
                "DELETE FROM table_metadata WHERE db_schema = ?", [db_schema_name]
            )

    def get_table_metadata(
        self, db_schema: str, table_id: str, metadata_type: TableMetadataType
    ) -> str:
        with self.__lock, self._get_connection() as conn:
            result = conn.execute(
                """
                SELECT metadata FROM table_metadata 
                WHERE db_schema = ? AND table_id = ? AND metadata_type = ?
            """,
                [db_schema, table_id, metadata_type.value],
            ).fetchone()

            if not result:
                raise ValueError(f"Metadata `{metadata_type}` does not exist.")
            return result[0]

    def delete_table_metadata(
        self, db_schema: str, table_id: str, metadata_type: TableMetadataType
    ) -> None:
        with self.__lock, self._get_connection() as conn:
            result = conn.execute(
                """
                DELETE FROM table_metadata 
                WHERE db_schema = ? AND table_id = ? AND metadata_type = ?
                RETURNING 1
            """,
                [db_schema, table_id, metadata_type.value],
            ).fetchone()

            if not result:
                raise ValueError("Metadata does not exist.")

    def get_table_ids_in_db_schema(self, db_schema: str) -> list[str]:
        with self.__lock, self._get_connection() as conn:
            # Check if schema exists
            if not conn.execute(
                """
                SELECT 1 FROM schemas WHERE schema_name = ?
            """,
                [db_schema],
            ).fetchone():
                raise ValueError(f"DB schema `{db_schema}` does not exist.")

            # Get all tables in the schema
            results = conn.execute(
                """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = ?
            """,
                [db_schema],
            ).fetchall()

            return [r[0] for r in results]

    def get_all_tables_in_db_schema(self, db_schema: str) -> dict[str, AbstractTable]:
        with self.__lock, self._get_connection() as conn:
            table_ids = self.get_table_ids_in_db_schema(db_schema)
            tables = {}

            for table_id in table_ids:
                tables[table_id] = self.get_table(db_schema, table_id)

            return tables
