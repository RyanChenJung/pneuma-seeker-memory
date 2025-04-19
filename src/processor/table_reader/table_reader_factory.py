from typing import Any, Type

from pandas import DataFrame

from processor.utils.table_reader.impl.df_reader import DFReader
from processor.utils.table_reader.table_reader import AbstractTableReader


def get_table_reader(table_type: Any) -> Type[AbstractTableReader]:
    if issubclass(table_type, DataFrame):
        return DFReader
    else:
        raise ValueError(
            f"No implementation for this table_representation: {table_type}"
        )
