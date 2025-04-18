from dataclasses import dataclass
from logging import Logger

from processor.llm.interface.model import AbstractModel
from processor.table_store.table_store import AbstractTableStore
from processor.utils.table_reader.table_reader import AbstractTableReader


@dataclass
class ConductorState:
    table_store: AbstractTableStore
    table_reader: AbstractTableReader
    logger: Logger
    llm: AbstractModel
    embed_model: AbstractModel
