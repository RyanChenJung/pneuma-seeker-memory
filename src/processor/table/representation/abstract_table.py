from abc import ABC, abstractmethod
from typing import Any, Optional, TypeVar, Generic


T = TypeVar("T")


class AbstractTable(ABC, Generic[T]):
    @abstractmethod
    def __init__(self, id: str, data: T):
        """Initializes a table."""
        pass

    @abstractmethod
    def get_schema(self) -> list[str]:
        """Returns the schema of a table, represented as a list of strings."""
        pass

    @abstractmethod
    def get_representation(
        self,
        num_rows: int,
        consecutive=False,
        random_seed=42,
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
