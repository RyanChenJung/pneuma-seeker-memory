from typing import Any, Type
from pandas import DataFrame
from processor.table.representation.impl.df_table import DFTable
from processor.table_store_legacy.table_store import AbstractTableStore


def get_table_impl(data: Any) -> Type[AbstractTableStore]:
    """Factory function to return the correct table class based on the data type."""
    if issubclass(data, DataFrame):
        return DFTable
    else:
        raise ValueError(f"No interface implementation for this type: {data}")
