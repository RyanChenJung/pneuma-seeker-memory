from typing import Any, Hashable, Optional
from numpy.random import default_rng
from numpy import nan
from pandas import DataFrame, Series, concat

from pneuma_seeker.table.representation.abstract_table import AbstractTable


class DFTable(AbstractTable[DataFrame]):
    def __init__(self, data: DataFrame, name: Optional[str] = None):
        """Initializes a table."""
        self.data = data
        self.name = name

    def get_schema(self) -> list[str]:
        """Returns the schema of a table, represented as a list of strings."""
        return list(self.data.columns)

    def set_schema(self, new_schema: list[str]):
        """Set the schema of a table."""
        self.data.columns = new_schema

    def rename_schema(self, schema_mapping: dict[str, str]):
        """Renames the schema of a table."""
        self.data.rename(columns=schema_mapping, inplace=True)

    def get_data(self) -> DataFrame:
        """Returns the data of the table."""
        return self.data

    def get_representation(
        self,
        num_rows: int,
        random_seed=42,
        consecutive=False,
        consecutive_indices: tuple[int, int] = None,
        show_unique_values=False,
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

    def __eq__(self, value):
        if not isinstance(value, DFTable):
            return NotImplemented
        return self.get_data().equals(value.get_data())

    def select_columns(self, columns: list[str]) -> "DFTable":
        return DFTable(self.data[columns].copy(), name=self.name)

    def add_missing_columns(self, columns: list[str], default_value: Any = None):
        for col in columns:
            if col not in self.data.columns:
                if default_value is None:
                    # Create a nullable Int64 (or object if truly no info)
                    self.data[col] = Series([None] * len(self.data), dtype="Int64")
                else:
                    self.data[col] = default_value

    @staticmethod
    def concat(tables: list["DFTable"]) -> "DFTable":
        dfs = [table.get_data() for table in tables]
        combined_df = concat(dfs, ignore_index=True)
        return DFTable(combined_df)

    def __getitem__(self, key: str):
        return self.data[key]

    def __setitem__(self, key: str, value):
        self.data[key] = value

    def get_row(self, idx: Any):
        """Retrieves the whole row of the given index."""
        return self.data.loc[idx]

    @staticmethod
    def merge_rows(rows: list[dict[str, Any]]) -> "DFTable":
        """
        Creates a new DFTable by merging rows.

        Args:
            rows (list[dict[str, Any]]): A list of rows, where each row is represented as a dictionary.

        Returns:
            DFTable: A new table containing the merged rows.
        """
        merged_data = DataFrame(rows)
        return DFTable(merged_data)
    
    @staticmethod
    def merge_columns(columns: dict[str, list[Any]]) -> "DFTable":
        """
        Creates a new table by merging columns.

        Args:
            columns (dict[str, list[Any]]): A dictionary of columns.

        Returns:
            AbstractTable: A new table containing the merged columns.
        """
        print(f"DEBUGGY: columns: {columns}")
        merged_data = DataFrame(columns)
        return DFTable(merged_data)
    
    def drop_duplicates(self) -> "DFTable":
        """Drops duplicates in the rows of a table and resets the index."""
        return DFTable(
            data=self.data.drop_duplicates().reset_index(drop=True)
        )
    
    def iterrows(self) -> tuple[Hashable, Series]:
        """Returns the rows of a table, along with the index."""
        return self.data.iterrows()
    
    def merge_rows_with_duplicate_ids(self, id_col: Optional[str] = None) -> None:
        """Merges rows with duplicate IDs (default to first column as ID column)."""
        if id_col is None:
            id_col = self.get_schema()[0]
        df = self.data.copy()
        non_id_cols = [col for col in df.columns if col != id_col]

        grouped = df.groupby(id_col)
        cleaned_rows = []

        for id_val, group in grouped:
            if len(group) == 1:
                cleaned_rows.append(group.iloc[0].to_dict())
                continue

            misalign_count = 0
            total_checks = 0
            combined = {}

            for col in non_id_cols:
                non_null_vals = group[col].dropna().unique()
                if len(non_null_vals) > 1:
                    misalign_count += 1
                if len(non_null_vals) >= 1:
                    total_checks += 1
                combined[col] = non_null_vals[0] if len(non_null_vals) > 0 else nan

            if total_checks > 0 and misalign_count == total_checks:
                cleaned_rows.extend(group.to_dict(orient='records'))
                continue

            combined[id_col] = id_val
            cleaned_rows.append(combined)
        self.data = DataFrame(cleaned_rows)[df.columns].reset_index(drop=True)

    def __len__(self) -> int:
        """Returns the number of rows in a table."""
        return len(self.data)
