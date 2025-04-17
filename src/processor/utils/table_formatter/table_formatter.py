from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class AbstractTableFormatter(ABC, Generic[T]):
    @abstractmethod
    def format_table(
        self, table: T, num_rows: int, random_seed: int, consecutive=False
    ):
        """
        Formats a table, with or without rows.
        """
        pass

    @abstractmethod
    def get_table_schema(self, table: T):
        """Returns the schema of a table."""
        pass
