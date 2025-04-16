import pandas as pd


class DataFrameStore:
    def __init__(self):
        # Internal store: maps schema names to a dict of table_id -> DataFrame
        self._schemas: dict[str, dict[str, pd.DataFrame]] = {}

    def create_new_schema(self, schema: str) -> None:
        """Creates a new schema in the store. Raises error if it already exists."""
        if schema in self._schemas:
            raise ValueError(f"Schema '{schema}' already exists.")
        self._schemas[schema] = {}

    def delete_schema(self, schema: str) -> None:
        """Deletes a schema and all of its tables. Raises error if not found."""
        if schema not in self._schemas:
            raise KeyError(f"Schema '{schema}' does not exist.")
        del self._schemas[schema]

    def add_table(self, schema: str, table_id: str, df: pd.DataFrame, overwrite: bool = False) -> None:
        """
        Adds or updates a table in a schema. If overwrite is False and table exists, raises error.
        """
        if schema not in self._schemas:
            self._schemas[schema] = {}
        if table_id in self._schemas[schema] and not overwrite:
            raise ValueError(
                f"Table '{table_id}' already exists in schema '{schema}'. Use overwrite=True to replace."
            )
        self._schemas[schema][table_id] = df

    def retrieve_table(self, schema: str, table_id: str) -> pd.DataFrame:
        """Returns a specific table from a schema. Raises error if not found."""
        try:
            return self._schemas[schema][table_id]
        except KeyError:
            raise KeyError(f"Table '{schema}.{table_id}' not found.")

    def delete_table(self, schema: str, table_id: str) -> None:
        """Deletes a specific table from a schema. Raises error if not found."""
        try:
            del self._schemas[schema][table_id]
        except KeyError:
            raise KeyError(f"Table '{schema}.{table_id}' not found.")

    def list_all_schemas(self) -> list[str]:
        """Returns a list of all schema names."""
        return list(self._schemas.keys())

    def list_tables_in_schema(self, schema: str) -> list[str]:
        """Returns all table IDs in a schema. Raises error if schema not found."""
        if schema not in self._schemas:
            raise KeyError(f"Schema '{schema}' does not exist.")
        return list(self._schemas[schema].keys())

    def check_if_table_exists(self, schema: str, table_id: str) -> bool:
        """Returns True if a table exists within the given schema."""
        return schema in self._schemas and table_id in self._schemas[schema]

    def get_all_tables_in_schema(self, schema: str) -> dict[str, pd.DataFrame]:
        """Returns a dictionary of all tables in a schema. Raises error if schema not found."""
        if schema not in self._schemas:
            raise KeyError(f"Schema '{schema}' does not exist.")
        return self._schemas[schema]

    def __contains__(self, schema: str) -> bool:
        """Returns True if schema exists in the store."""
        return schema in self._schemas

    def __len__(self) -> int:
        """Returns total number of tables across all schemas."""
        return sum(len(tables) for tables in self._schemas.values())

    def __getitem__(self, schema: str) -> dict[str, pd.DataFrame]:
        """Enables bracket-access for schemas, returns all tables inside."""
        return self.get_all_tables_in_schema(schema)
