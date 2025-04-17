from pandas import DataFrame
import numpy as np

from processor.utils.table_formatter.table_formatter import AbstractTableFormatter


class DFFormatter(AbstractTableFormatter[DataFrame]):
    def format_table(
        self, table: DataFrame, num_rows: int, random_seed: int, consecutive=False
    ):
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
                for idx, i in enumerate(range(min(num_rows, len(table)))):
                    row_str = f"row {idx+1}: " + " | ".join(table.iloc[i].astype(str))
                    rows.append(row_str)
            representation += f"\n{'\n'.join(rows)}"
        return representation

    def get_table_schema(self, table: DataFrame):
        """Returns the schema of a table."""
        return table.columns