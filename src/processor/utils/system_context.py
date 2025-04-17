from dataclasses import dataclass
from logging import Logger

from processor.llm.interface.model import AbstractModel
from processor.table_store.table_store import AbstractTableStore
from processor.utils.table_formatter.table_formatter import AbstractTableFormatter


@dataclass
class SystemContext:
    table_store: AbstractTableStore
    table_formatter: AbstractTableFormatter
    logger: Logger
    llm: AbstractModel
    config: None  # May be supported in the future
