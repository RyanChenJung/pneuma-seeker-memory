from typing import TypedDict
from pandas import DataFrame

from processor.table_store.table_store import AbstractTableStore


class DFStore(AbstractTableStore[DataFrame]):
    def __init__(self):
        # Internal store: maps schema names to SchemaData (table_id, DataFrame)
        self._store: dict[str, SchemaData] = {}

    def create_new_schema(self, schema: str) -> None:
        """Creates a new schema in the store. Raises error if it already exists."""
        if schema in self._store:
            raise ValueError(f"Schema '{schema}' already exists.")
        self._store[schema] = {}

    def delete_schema(self, schema: str) -> None:
        """Deletes a schema and all of its tables. Raises error if not found."""
        if schema not in self._store:
            raise KeyError(f"Schema '{schema}' does not exist.")
        del self._store[schema]

    def add_table(
        self, schema: str, table_id: str, df: DataFrame, overwrite: bool = False
    ) -> None:
        """
        Adds or updates a table in a schema. If overwrite is False and table exists, raises error.
        """
        if schema not in self._store:
            self._store[schema] = {}
        if table_id in self._store[schema] and not overwrite:
            raise ValueError(
                f"Table '{table_id}' already exists in schema '{schema}'. Use overwrite=True to replace."
            )
        self._store[schema][table_id] = df

    def retrieve_table(self, schema: str, table_id: str) -> DataFrame:
        """Returns a specific table from a schema. Raises error if not found."""
        try:
            return self._store[schema][table_id]
        except KeyError:
            raise KeyError(f"Table '{schema}.{table_id}' not found.")

    def delete_table(self, schema: str, table_id: str) -> None:
        """Deletes a specific table from a schema. Raises error if not found."""
        try:
            del self._store[schema][table_id]
        except KeyError:
            raise KeyError(f"Table '{schema}.{table_id}' not found.")

    def list_all_store(self) -> list[str]:
        """Returns a list of all schema names."""
        return list(self._store.keys())

    def list_tables_in_schema(self, schema: str) -> list[str]:
        """Returns all table IDs in a schema. Raises error if schema not found."""
        if schema not in self._store:
            raise KeyError(f"Schema '{schema}' does not exist.")
        return list(self._store[schema].keys())

    def check_if_table_exists(self, schema: str, table_id: str) -> bool:
        """Returns True if a table exists within the given schema."""
        return schema in self._store and table_id in self._store[schema]

    def get_all_tables_in_schema(self, schema: str) -> dict[str, DataFrame]:
        """Returns a dictionary of all tables in a schema. Raises error if schema not found."""
        if schema not in self._store:
            raise KeyError(f"Schema '{schema}' does not exist.")
        return self._store[schema]

    def __contains__(self, schema: str) -> bool:
        """Returns True if schema exists in the store."""
        return schema in self._store

    def __len__(self) -> int:
        """Returns total number of tables across all schemas."""
        return sum(len(tables) for tables in self._store.values())

    def __getitem__(self, schema: str) -> dict[str, DataFrame]:
        """Enables bracket-access for schemas, returns all tables inside."""
        return self.get_all_tables_in_schema(schema)


class SchemaData(TypedDict):
    id: str
    table: DataFrame
