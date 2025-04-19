from enum import Enum
from typing import Type
from processor.table.store.abstract_table_store import AbstractTableStore
from processor.table.store.impl.py_table_store import PyTableStore


class ImplementedTableStore(Enum):
    PY_TABLE_STORE = "py_table_store"


def get_table_store(table_store: ImplementedTableStore) -> Type[AbstractTableStore]:
    """Factory function to return the correct store class."""
    if table_store == ImplementedTableStore.PY_TABLE_STORE:
        return PyTableStore
    else:
        raise ValueError(f"No interface implementation for this type: {table_store}")
