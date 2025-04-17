from typing import Any, Type

from pandas import DataFrame

from processor.utils.table_formatter.impl.df_formatter import DFFormatter
from processor.utils.table_formatter.table_formatter import AbstractTableFormatter


def get_table_formatter(table_type: Any) -> Type[AbstractTableFormatter]:
    if issubclass(table_type, DataFrame):
        return DFFormatter
    else:
        raise ValueError(
            f"No implementation for this table_representation: {table_type}"
        )
