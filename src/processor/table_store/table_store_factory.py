from typing import Any, Type
from pandas import DataFrame
from processor.table_store.impl.df_store import DFStore
from processor.table_store.table_store import AbstractTableStore


def get_table_store(table_type: Any) -> Type[AbstractTableStore]:
    """Factory function to return the correct store class based on the implementation type."""
    if issubclass(table_type, DataFrame):
        return DFStore
    else:
        raise ValueError(f"No interface implementation for this type: {table_type}")
