from typing import Any
from pandas import DataFrame
import numpy as np

from processor.utils.table_reader.table_reader import AbstractTableReader


class DFReader(AbstractTableReader[DataFrame]):
    def format_table(
        self,
        table: DataFrame,
        num_rows: int,
        random_seed: int,
        consecutive=False,
        consecutive_indices: tuple[int, int] = None
    ) -> str:
        """
        Formats a DataFrame, with or without rows.
        """
        representation = "col: " + " | ".join(table.columns)
        if num_rows > 0:
            rows = []
            if not consecutive:
                np.random.seed(random_seed)
                if len(table) <= num_rows:
                    sample_indices = range(len(table))
                else:
                    sample_indices = np.random.choice(
                        len(table), num_rows, replace=False
                    )
                for i, idx in enumerate(sample_indices):
                    row_str = f"sample row {i+1}: " + " | ".join(
                        table.iloc[idx].astype(str)
                    )
                    rows.append(row_str)
            else:
                low_idx = 0
                high_idx = min(num_rows, len(table))
                if consecutive_indices:
                    low_idx = consecutive_indices[0]
                    high_idx = consecutive_indices[1]

                for idx, i in enumerate(range(low_idx, high_idx)):
                    row_str = f"row {idx+1}: " + " | ".join(table.iloc[i].astype(str))
                    rows.append(row_str)
            representation += f"\n{'\n'.join(rows)}"
        return representation

    def get_column_values(
        self, table: DataFrame, column_name: str, num_values: int = None, random_seed=42
    ) -> list[Any]:
        """Returns column values of a table."""
        if num_values is None:
            return table[column_name].tolist()
        return table[column_name].sample(num_values, random_state=random_seed).tolist()

    def get_table_schema(self, table: DataFrame) -> list[str]:
        """Returns the schema of a table."""
        return table.columns.tolist()
