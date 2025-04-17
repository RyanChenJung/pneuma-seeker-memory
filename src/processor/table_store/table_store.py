from abc import ABC, abstractmethod
from typing import TypeVar, Generic


T = TypeVar("T")

class AbstractTableStore(ABC, Generic[T]):
    @abstractmethod
    def create_new_schema(self, schema: str) -> None:
        """Creates a new schema in the store. Raises error if it already exists."""
        pass

    @abstractmethod
    def delete_schema(self, schema: str) -> None:
        """Deletes a schema and all of its tables. Raises error if not found."""
        pass

    @abstractmethod
    def add_table(
        self, schema: str, table_id: str, table: T, overwrite: bool = False
    ) -> None:
        """
        Adds or updates a table in a schema. If overwrite is False and table exists, raises error.
        """
        pass

    @abstractmethod
    def retrieve_table(self, schema: str, table_id: str) -> T:
        """Returns a specific table from a schema. Raises error if not found."""
        pass

    @abstractmethod
    def delete_table(self, schema: str, table_id: str) -> None:
        """Deletes a specific table from a schema. Raises error if not found."""
        pass
    
    @abstractmethod
    def add_table_metadata(
        self, schema: str, table_id: str, metadata_id: str, metadata: str, overwrite: bool = False
    ) -> None:
        """
        Adds or updates metadata of a table in a schema. If overwrite is False and metadata exists, raises error.
        """
        pass

    @abstractmethod
    def retrieve_table_metadata(self, schema: str, table_id: str, metadata_id: str) -> str:
        """Returns a specific table metadata from a schema. Raises error if not found."""
        pass

    @abstractmethod
    def delete_table_metadata(self, schema: str, table_id: str, metadata_id: str) -> None:
        """Deletes a specific table metadata from a schema. Raises error if not found."""
        pass

    @abstractmethod
    def list_all_store(self) -> list[str]:
        """Returns a list of all schema names."""
        pass

    @abstractmethod
    def list_tables_in_schema(self, schema: str) -> list[str]:
        """Returns all table IDs in a schema. Raises error if schema not found."""
        pass

    @abstractmethod
    def check_if_table_exists(self, schema: str, table_id: str) -> bool:
        """Returns True if a table exists within the given schema."""
        pass

    @abstractmethod
    def get_all_tables_in_schema(self, schema: str) -> dict[str, T]:
        """Returns a dictionary of all tables in a schema. Raises error if schema not found."""
        pass

    def __contains__(self, schema: str) -> bool:
        """Returns True if schema exists in the store."""
        return schema in self.list_all_store()

    def __len__(self) -> int:
        """Returns total number of tables across all schemas."""
        return sum(len(self.list_tables_in_schema(s)) for s in self.list_all_store())

    def __getitem__(self, schema: str) -> dict[str, T]:
        """Enables bracket-access for schemas, returns all tables inside."""
        return self.get_all_tables_in_schema(schema)
