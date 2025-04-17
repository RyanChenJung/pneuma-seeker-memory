from abc import ABC, abstractmethod
from typing import TypeVar

T = TypeVar("T")


class AbstractTableFormatter(ABC, T):
    @abstractmethod
    def format_table(table: T, num_rows: int, random_seed: int, consecutive=False):
        """
        Formats a table, with or without rows.
        """
        pass
