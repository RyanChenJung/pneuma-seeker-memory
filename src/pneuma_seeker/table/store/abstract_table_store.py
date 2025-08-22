from abc import ABC, abstractmethod
from typing import Optional

from pneuma_seeker.table.representation.abstract_table import AbstractTable
from pneuma_seeker.table.representation.metadata import TableMetadataType


class AbstractTableStore(ABC):
    @abstractmethod
    def __init__(self, db_path: str):
        """Initializes a table store using an underlying database system."""
        pass

    @abstractmethod
    def checkpoint(self):
        """Checkpoints data."""
        pass
    
    @abstractmethod
    def load_checkpoint(self, db_path: Optional[str] = None):
        """Loads a table store."""
        pass

    @abstractmethod
    def create_db_schema(self, db_schema_name: str) -> None:
        """
        Creates a new DB schema in the store. Raises error if it already exists.

        Args:
            db_schema_name (str): Name of the DB schema to add.
        """
        pass

    @abstractmethod
    def rename_db_schema(self, db_schema_name: str, new_db_schema_name: str) -> None:
        """
        Renames a DB schema in the store. Raises error if it does not exists.

        Args:
            db_schema_name (str): Name of the DB schema to rename.
            new_db_schema_name (str): New name for the DB schema.
        """
        pass

    @abstractmethod
    def delete_db_schema(self, db_schema_name: str) -> None:
        """
        Deletes a DB schema and all of its tables. Raises error if not found.

        Args:
            db_schema_name (str): Name of the DB schema to delete.
        """
        pass

    @abstractmethod
    def add_table(
        self,
        db_schema: str,
        table_id: str,
        table: AbstractTable,
        overwrite = False,
        checkpoint = False,
    ) -> None:
        """
        Adds or updates a table in a schema. If overwrite is False and table exists, raises error.

        Args:
            db_schema (str): Name of the DB schema to add the table into.
            table_id (str): The ID of the new table.
            table (AbstractTable): The new table to add/overwrite existing one.
            overwrite (bool): Whether to overwrite existing table if exists.
        """
        pass

    @abstractmethod
    def get_table(self, db_schema: str, table_id: str) -> AbstractTable:
        """
        Returns a specific table from a DB schema. Raises error if not found.

        Args:
            db_schema (str): The DB schema to find a table from.
            table_id (str): The ID of the table to find.
        """
        pass

    @abstractmethod
    def delete_table(self, db_schema: str, table_id: str) -> None:
        """
        Deletes a specific table from a DB schema. Raises error if not found.
        """
        pass

    @abstractmethod
    def add_table_metadata(
        self,
        db_schema: str,
        table_id: str,
        metadata_type: TableMetadataType,
        metadata: str,
        overwrite: bool = False,
    ) -> None:
        """
        Adds or updates metadata of a table in a schema. If overwrite is False and metadata exists, raises error.
        """
        pass

    @abstractmethod
    def get_table_metadata(
        self, db_schema: str, table_id: str, metadata_type: TableMetadataType
    ) -> str:
        """Returns a specific table metadata from a schema. Raises error if not found."""
        pass

    @abstractmethod
    def delete_table_metadata(
        self, db_schema: str, table_id: str, metadata_type: TableMetadataType
    ) -> None:
        """Deletes a specific table metadata from a schema. Raises error if not found."""
        pass

    @abstractmethod
    def get_all_db_schemas(self) -> list[str]:
        """Returns a list of all schema names."""
        pass

    @abstractmethod
    def get_table_ids_in_db_schema(self, db_schema: str) -> list[str]:
        """Returns all table IDs in a DB schema. Raises error if schema not found."""
        pass

    @abstractmethod
    def check_if_table_exists(self, db_schema: str, table_id: str) -> bool:
        """Returns True if a table exists within the given DB schema."""
        pass

    @abstractmethod
    def get_all_tables_in_db_schema(self, db_schema: str) -> dict[str, AbstractTable]:
        """Returns a dictionary of all tables in a DB schema. Raises error if schema not found."""
        pass

    @abstractmethod
    def execute_sql_query(self, sql_query: str, tables_involved: Optional[dict[str, AbstractTable]] = None) -> AbstractTable:
        """
        [EXPERIMENTAL] Executes SQL query

        Args:
            sql_query (str): SQL query to execute
            tables_involved (list[AbstractTable]): OPTIONAL - Specify tables to query over (used by, e.g., PyTableStore)
        """
        pass

    def __contains__(self, db_schema: str) -> bool:
        """Returns True if DB schema exists in the store."""
        return db_schema in self.get_all_db_schemas()

    def __len__(self) -> int:
        """Returns total number of tables across all DB schemas."""
        return sum(
            len(self.get_table_ids_in_db_schema(s)) for s in self.get_all_db_schemas()
        )

    def __getitem__(self, db_schema: str) -> dict[str, AbstractTable]:
        """Enables bracket-access for DB schemas, returns all tables inside."""
        return self.get_all_tables_in_db_schema(db_schema)
