from dataclasses import dataclass
from logging import Logger

from processor.llm.interface.model import AbstractModel
from processor.table_store.table_store import AbstractTableStore


@dataclass
class SystemContext:
    table_store: AbstractTableStore
    logger: Logger
    llm: AbstractModel
    config: None  # May be supported in the future
