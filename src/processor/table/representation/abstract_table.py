from abc import ABC, abstractmethod
import copy
from typing import Any, Optional, TypeVar, Generic

from pandas import Series


T = TypeVar("T")


class AbstractTable(ABC, Generic[T]):
    @abstractmethod
    def __init__(self, data: T, name: Optional[str] = None):
        """Initializes a table."""
        pass

    @abstractmethod
    def get_schema(self) -> list[str]:
        """Returns the schema of a table, represented as a list of strings."""
        pass

    @abstractmethod
    def set_schema(self, new_schema: list[str]):
        """Set the schema of a table."""
        pass

    @abstractmethod
    def rename_schema(self, schema_mapping: dict[str, str]):
        """Renames the schema of a table."""
        pass

    @abstractmethod
    def get_data(self) -> T:
        """Returns the data of the table."""
        pass

    @abstractmethod
    def get_representation(
        self,
        num_rows: int,
        random_seed=42,
        consecutive=False,
        consecutive_indices: Optional[tuple[int, int]] = None,
    ) -> str:
        """
        Returns a string representation of a table.

        Args:
            num_rows (int): Number of rows to include.
            consecutive (bool): Whether to return consecutive rows or not.
            random_seed (int): Seed to randomly sample rows.
            consecutive_indices (tuple[int, int]): Lower and upper bound of consecutive rows.
        """
        pass

    @abstractmethod
    def get_attribute_values(
        self, attr_name: str, num_values: Optional[int] = None, random_seed=42
    ) -> list[Any]:
        """
        Returns column values of an attribute of a table. Throws an error if
        `attr_name` is not available.

        Args:
            attr_name (str): The attribute name.
            num_values (int): OPTIONAL - The number of values to include.
            random_seed (int): Seed to randomly sample rows.
        """
        pass

    @abstractmethod
    def __eq__(self, value):
        """Checks if two tables are equal."""
        pass

    @abstractmethod
    def select_columns(self, columns: list[str]) -> "AbstractTable":
        """Returns a new table with only the selected columns."""
        pass

    @abstractmethod
    def add_missing_columns(self, columns: list[str], default_value: Any = None):
        """Adds missing columns with default values."""
        pass

    @staticmethod
    @abstractmethod
    def concat(tables: list["AbstractTable"]) -> "AbstractTable":
        """Concatenates a list of tables into one."""
        pass

    @abstractmethod
    def __getitem__(self, key: str) -> Series:
        pass

    @abstractmethod
    def __setitem__(self, key: str, value):
        pass

    @abstractmethod
    def get_row(self, idx: Any):
        """Retrieves the whole row of the given index."""
        pass

    @staticmethod
    @abstractmethod
    def merge_rows(rows: list[dict[str, Any]]) -> "AbstractTable":
        """
        Creates a new table by merging rows.

        Args:
            rows (list[dict[str, Any]]): A list of rows, where each row is represented as a dictionary.

        Returns:
            AbstractTable: A new table containing the merged rows.
        """
        pass

    def copy(self):
        return copy.deepcopy(self)
