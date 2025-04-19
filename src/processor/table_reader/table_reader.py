from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class AbstractTableReader(ABC, Generic[T]):
    @abstractmethod
    def format_table(
        self,
        table: T,
        num_rows: int,
        random_seed: int,
        consecutive=False,
        consecutive_indices: tuple[int, int] = None
    ) -> str:
        """
        Formats a table, with or without rows.
        """
        pass

    @abstractmethod
    def get_column_values(
        self, table: T, column_name: str, num_values: int = None, random_seed=42
    ) -> list[Any]:
        """Returns column values of a table."""
        pass

    @abstractmethod
    def get_table_schema(self, table: T) -> list[str]:
        """Returns the schema of a table."""
        pass
