from typing import TypedDict
from pandas import DataFrame

from processor.table_store.table_store import AbstractTableStore


class DFStore(AbstractTableStore[DataFrame]):
    def __init__(self):
        # Internal store: maps schema names to (table_id, DataFrame)
        self.__store: dict[str, dict[str, DataFrame]] = {}

        # Metadata store: maps `schema_id<DFStoreKeySeparator>table_id` to (metadata_id, metadata)
        self.key_separator = '<DFStoreKeySeparator>'
        self.__metadata: dict[str, dict[str, str]] = {}

    def create_new_schema(self, schema: str) -> None:
        """Creates a new schema in the store. Raises error if it already exists."""
        if schema in self.__store:
            raise ValueError(f"Schema '{schema}' already exists.")
        self.__store[schema] = {}

    def delete_schema(self, schema: str) -> None:
        """Deletes a schema and all of its tables. Raises error if not found."""
        if schema not in self.__store:
            raise KeyError(f"Schema '{schema}' does not exist.")
        del self.__store[schema]

    def add_table(
        self, schema: str, table_id: str, df: DataFrame, overwrite: bool = False
    ) -> None:
        """
        Adds or updates a table in a schema. If overwrite is False and table exists, raises error.
        """
        if schema not in self.__store:
            self.__store[schema] = {}
        if table_id in self.__store[schema] and not overwrite:
            raise ValueError(
                f"Table '{table_id}' already exists in schema '{schema}'. Use overwrite=True to replace."
            )
        self.__store[schema][table_id] = df

    def get_table(self, schema: str, table_id: str) -> DataFrame:
        """Returns a specific table from a schema. Raises error if not found."""
        try:
            return self.__store[schema][table_id]
        except KeyError:
            raise KeyError(f"Table '{schema}.{table_id}' not found.")

    def delete_table(self, schema: str, table_id: str) -> None:
        """Deletes a specific table from a schema. Raises error if not found."""
        try:
            del self.__store[schema][table_id]
        except KeyError:
            raise KeyError(f"Table '{schema}.{table_id}' not found.")

    def add_table_metadata(
        self,
        schema: str,
        table_id: str,
        metadata_id: str,
        metadata: str,
        overwrite: bool = False,
    ) -> None:
        """
        Adds or updates metadata of a table in a schema. If overwrite is False and metadata exists, raises error.
        """
        try:
            metadata_accessor = self.__combine_schema_table_ids(schema, table_id)
            table_metadata = self.__metadata[metadata_accessor]
            if metadata_id in table_metadata and not overwrite:
                raise ValueError(f"Metadata already exists. Set `overwrite = True` to overwrite it.")
            table_metadata[metadata_id] = metadata
        except KeyError:
            raise KeyError(f"Table '{schema}.{table_id}' not found.")

    def get_table_metadata(
        self, schema: str, table_id: str, metadata_id: str
    ) -> str:
        """Returns a specific table metadata from a schema. Raises error if not found."""
        try:
            metadata_accessor = self.__combine_schema_table_ids(schema, table_id)
            table_metadata = self.__metadata[metadata_accessor]
            if metadata_id not in table_metadata:
                raise KeyError(f"Metadata '{metadata_id}' not found.")
            return table_metadata[metadata_id]
        except KeyError:
            raise KeyError(f"Table '{schema}.{table_id}' not found.")

    def delete_table_metadata(
        self, schema: str, table_id: str, metadata_id: str
    ) -> None:
        """Deletes a specific table metadata from a schema. Raises error if not found."""
        try:
            metadata_accessor = self.__combine_schema_table_ids(schema, table_id)
            table_metadata = self.__metadata[metadata_accessor]
            if metadata_id not in table_metadata:
                raise KeyError(f"Metadata '{metadata_id}' not found.")
            del table_metadata[metadata_id]
        except KeyError:
            raise KeyError(f"Table '{schema}.{table_id}' not found.")

    def __combine_schema_table_ids(self, schema: str, table_id: str):
        return f"{schema}{self.key_separator}{table_id}"

    def list_all_store(self) -> list[str]:
        """Returns a list of all schema names."""
        return list(self.__store.keys())

    def list_tables_in_schema(self, schema: str) -> list[str]:
        """Returns all table IDs in a schema. Raises error if schema not found."""
        if schema not in self.__store:
            raise KeyError(f"Schema '{schema}' does not exist.")
        return list(self.__store[schema].keys())

    def check_if_table_exists(self, schema: str, table_id: str) -> bool:
        """Returns True if a table exists within the given schema."""
        return schema in self.__store and table_id in self.__store[schema]

    def get_all_tables_in_schema(self, schema: str) -> dict[str, DataFrame]:
        """Returns a dictionary of all tables in a schema. Raises error if schema not found."""
        if schema not in self.__store:
            raise KeyError(f"Schema '{schema}' does not exist.")
        return self.__store[schema]

    def __contains__(self, schema: str) -> bool:
        """Returns True if schema exists in the store."""
        return schema in self.__store

    def __len__(self) -> int:
        """Returns total number of tables across all schemas."""
        return sum(len(tables) for tables in self.__store.values())

    def __getitem__(self, schema: str) -> dict[str, DataFrame]:
        """Enables bracket-access for schemas, returns all tables inside."""
        return self.get_all_tables_in_schema(schema)
