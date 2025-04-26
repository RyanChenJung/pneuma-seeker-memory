import os
import pickle
import sqlite3
from threading import Lock
from typing import Optional

import pandas as pd

from processor.table.representation.abstract_table import AbstractTable
from processor.table.representation.impl.df_table import DFTable
from processor.table.representation.metadata import Metadata, TableMetadataType
from processor.table.store.abstract_table_store import AbstractTableStore


class PyTableStore(AbstractTableStore):
    def __init__(self, db_path: str):
        """Initializes a table store using an underlying database system."""
        if not os.path.exists(db_path):
            os.mkdir(db_path)
        self.__table_store: dict[str, dict[str, AbstractTable]] = dict()
        self.__metadata_store: list[Metadata] = []
        self.__lock = Lock()
        self.db_path = db_path

        try:
            self.load_checkpoint()
        except RuntimeError:
            self.checkpoint()

    def load_checkpoint(self, db_path: str = None):
        """Loads a table store."""
        if db_path is None:
            db_path = self.db_path
        with self.__lock:
            try:
                with open(os.path.join(db_path, "table_store.pkl"), "rb") as f:
                    self.__table_store = pickle.load(f)
                with open(os.path.join(db_path, "metadata_store.pkl"), "rb") as f:
                    self.__metadata_store = pickle.load(f)
            except (OSError, IOError, pickle.UnpicklingError) as e:
                raise RuntimeError(f"Failed to load checkpoint: {e}")

    def checkpoint(self):
        with self.__lock:
            try:
                with open(os.path.join(self.db_path, "table_store.pkl"), "wb") as f:
                    pickle.dump(self.__table_store, f)
                with open(os.path.join(self.db_path, "metadata_store.pkl"), "wb") as f:
                    pickle.dump(self.__metadata_store, f)
            except (OSError, IOError) as e:
                raise RuntimeError(f"Failed to save checkpoint: {e}")

    def create_db_schema(self, db_schema_name: str) -> None:
        """
        Creates a new DB schema in the store. Raises error if it already exists.

        Args:
            db_schema_name (str): Name of the DB schema to add.
        """
        if db_schema_name in self.__table_store:
            raise ValueError(f"DB schema `{db_schema_name}` already exists.")
        self.__table_store[db_schema_name] = dict()
        self.checkpoint()

    def rename_db_schema(self, db_schema_name: str, new_db_schema_name: str) -> None:
        """
        Renames a DB schema in the store. Raises error if it does not exists.

        Args:
            db_schema_name (str): Name of the DB schema to rename.
            new_db_schema_name (str): New name for the DB schema.
        """
        if db_schema_name not in self.__table_store:
            raise ValueError(f"DB schema `{db_schema_name}` does not exist.")

        self.__table_store[new_db_schema_name] = self.__table_store[
            db_schema_name
        ].copy()
        del self.__table_store[db_schema_name]
        self.checkpoint()

    def delete_db_schema(self, db_schema_name: str) -> None:
        """
        Deletes a DB schema and all of its tables. Raises error if not found.

        Args:
            db_schema_name (str): Name of the DB schema to delete.
        """
        if db_schema_name not in self.__table_store:
            raise ValueError(f"DB schema `{db_schema_name}` does not exist.")
        del self.__table_store[db_schema_name]
        self.checkpoint()

    def add_table(
        self,
        db_schema: str,
        table_id: str,
        table: AbstractTable,
        overwrite=False,
        checkpoint=False,
    ) -> None:
        """
        Adds or updates a table in a schema. If overwrite is False and table exists, raises error.

        Args:
            db_schema (str): Name of the DB schema to add the table into.
            table_id (str): The ID of the new table.
            table (AbstractTable): The new table to add/overwrite existing one.
            overwrite (bool): Whether to overwrite existing table if exists.
        """
        if db_schema not in self.__table_store:
            raise ValueError(f"DB schema `{db_schema}` does not exist.")
        if table_id in self.__table_store[db_schema] and not overwrite:
            raise ValueError(
                f"Table `{table_id}` already exists in the DB schema. To overwrite, set `overwrite=True`."
            )
        self.__table_store[db_schema][table_id] = table
        if checkpoint:
            self.checkpoint()

    def get_table(self, db_schema: str, table_id: str) -> AbstractTable:
        """
        Returns a specific table from a DB schema. Raises error if not found.

        Args:
            db_schema (str): The DB schema to find a table from.
            table_id (str): The ID of the table to find.
        """
        if db_schema not in self.__table_store:
            raise ValueError(f"DB schema `{db_schema}` does not exist.")
        if table_id not in self.__table_store[db_schema]:
            raise ValueError(f"Table `{table_id}` does not exist.")
        return self.__table_store[db_schema][table_id]

    def delete_table(self, db_schema: str, table_id: str) -> None:
        """
        Deletes a specific table from a DB schema. Raises error if not found.
        """
        if db_schema not in self.__table_store:
            raise ValueError(f"DB schema `{db_schema}` does not exist.")
        if table_id not in self.__table_store[db_schema]:
            raise ValueError(f"Table `{table_id}` does not exist.")
        del self.__table_store[db_schema][table_id]
        self.checkpoint()

    def add_table_metadata(
        self,
        db_schema: str,
        table_id: str,
        metadata_type: TableMetadataType,
        metadata_info: str,
        overwrite: bool = False,
    ) -> None:
        """
        Adds or updates metadata of a table in a schema. If overwrite is False and metadata exists, raises error.
        """
        if db_schema not in self.__table_store:
            raise ValueError(f"DB schema `{db_schema}` does not exist.")
        if table_id not in self.__table_store[db_schema]:
            raise ValueError(f"Table `{table_id}` does not exist.")

        table_metadata = list(
            filter(
                lambda x: x["db_schema"] == db_schema and x["table_id"] == table_id,
                self.__metadata_store,
            )
        )
        if metadata_type in [i["type"] for i in table_metadata] and not overwrite:
            raise ValueError(
                f"Metadata already exists and `overwrite` is set to False."
            )

        filtered_metadata_store = [
            i
            for i in self.__metadata_store
            if not (
                i["db_schema"] == db_schema
                and i["table_id"] == table_id
                and i["type"] == metadata_type
            )
        ]
        filtered_metadata_store.append(
            Metadata(
                db_schema=db_schema,
                table_id=table_id,
                information=metadata_info,
                type=metadata_type,
            )
        )
        self.__metadata_store = filtered_metadata_store
        self.checkpoint()

    def get_table_metadata(
        self, db_schema: str, table_id: str, metadata_type: TableMetadataType
    ) -> str:
        """Returns a specific table metadata from a schema. Raises error if not found."""
        if db_schema not in self.__table_store:
            raise ValueError(f"DB schema `{db_schema}` does not exist.")
        if table_id not in self.__table_store[db_schema]:
            raise ValueError(f"Table `{table_id}` does not exist.")

        table_metadata = list(
            filter(
                lambda x: x["db_schema"] == db_schema
                and x["table_id"] == table_id
                and x["type"] == metadata_type,
                self.__metadata_store,
            )
        )
        if len(table_metadata) == 0:
            raise ValueError(f"Metadata `{metadata_type}` does not exist.")
        return table_metadata[0]["information"]

    def delete_table_metadata(
        self, db_schema: str, table_id: str, metadata_type: TableMetadataType
    ) -> None:
        """Deletes a specific table metadata from a schema. Raises error if not found."""
        if db_schema not in self.__table_store:
            raise ValueError(f"DB schema `{db_schema}` does not exist.")
        if table_id not in self.__table_store[db_schema]:
            raise ValueError(f"Table `{table_id}` does not exist.")

        filtered_metadata_store = [
            i
            for i in self.__metadata_store
            if not (
                i["db_schema"] == db_schema
                and i["table_id"] == table_id
                and i["type"] == metadata_type
            )
        ]
        if len(filtered_metadata_store) == len(self.__metadata_store):
            raise ValueError("Metadata does not exists.")
        self.__metadata_store = filtered_metadata_store
        self.checkpoint()

    def get_all_db_schemas(self) -> list[str]:
        """Returns a list of all schema names."""
        return list(self.__table_store.keys())

    def get_table_ids_in_db_schema(self, db_schema: str) -> list[str]:
        """Returns all table IDs in a DB schema. Raises error if schema not found."""
        return list(self.__table_store[db_schema].keys())

    def check_if_table_exists(self, db_schema: str, table_id: str) -> bool:
        """Returns True if a table exists within the given DB schema."""
        return (
            db_schema in self.__table_store
            and table_id in self.__table_store[db_schema]
        )

    def get_all_tables_in_db_schema(self, db_schema: str) -> dict[str, AbstractTable]:
        """Returns a dictionary of all tables in a DB schema. Raises error if schema not found."""
        return self.__table_store[db_schema]

    def execute_sql_query(
        self, sql_query: str, tables_involved: Optional[dict[str, AbstractTable]] = None
    ) -> AbstractTable:
        """
        [EXPERIMENTAL] Executes SQL query

        Args:
            sql_query (str): SQL query to execute
            tables_involved (list[AbstractTable]): OPTIONAL - Specify tables to query over (used by, e.g., PyTableStore)
        """
        import duckdb

        # Create an in-memory DuckDB connection
        conn = duckdb.connect(database=":memory:")

        # Make sure you pass a dictionary of DFTable
        if tables_involved is None or len(tables_involved) == 0:
            raise ValueError(
                "PyTableStore requires `tables_involved` to execute SQL queries."
            )

        if not isinstance(tables_involved[list(tables_involved.keys())[0]], DFTable):
            raise ValueError("Only Pandas DataFrame is supported for now.")

        # Register each DataFrame as a DuckDB view
        for table_id, table in tables_involved.items():
            conn.register(table_id.lower(), table.get_data())

        # Run your SQL query
        data = conn.execute(sql_query).fetchdf()
        return DFTable(data)
