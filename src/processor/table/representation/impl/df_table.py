from typing import Any, Optional
from numpy.random import default_rng
from pandas import DataFrame

from processor.table.representation.abstract_table import AbstractTable


class DFTable(AbstractTable[DataFrame]):
    def __init__(self, id: str, data: DataFrame):
        """Initializes a table."""
        self.id = id
        self.data = data

    def get_schema(self) -> list[str]:
        """Returns the schema of a table, represented as a list of strings."""
        return list(self.data.columns)

    def get_representation(
        self,
        num_rows: int,
        consecutive=False,
        random_seed=42,
        consecutive_indices: tuple[int, int] = None,
    ) -> str:
        """
        Returns a string representation of a table.

        Args:
            num_rows (int): Number of rows to include.
            consecutive (bool): Whether to return consecutive rows or not.
            random_seed (int): Seed to randomly sample rows.
            consecutive_indices (tuple[int, int]): Lower and upper bound of consecutive rows.
        """
        representation = "col: " + " | ".join(self.data.columns)
        if num_rows > 0:
            rows = []
            if not consecutive:
                rng = default_rng(seed=random_seed)
                if len(self.data) <= num_rows:
                    sample_indices = range(len(self.data))
                else:
                    sample_indices = rng.choice(
                        a=len(self.data), size=num_rows, replace=False
                    )
                for i, idx in enumerate(sample_indices):
                    row_str = f"sample row {i+1}: " + " | ".join(
                        self.data.iloc[idx].astype(str)
                    )
                    rows.append(row_str)
            else:
                low_idx = 0
                high_idx = min(num_rows, len(self.data))
                if consecutive_indices:
                    low_idx = consecutive_indices[0]
                    high_idx = consecutive_indices[1]

                for idx, i in enumerate(range(low_idx, high_idx)):
                    row_str = f"row {idx+1}: " + " | ".join(
                        self.data.iloc[i].astype(str)
                    )
                    rows.append(row_str)
            representation += "\n" + "\n".join(rows)
        return representation

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
        if attr_name not in self.data.columns:
            raise ValueError(f"Attribute '{attr_name}' not found in table.")
        if num_values is None:
            return self.data[attr_name].tolist()
        return (
            self.data[attr_name].sample(num_values, random_state=random_seed).tolist()
        )
