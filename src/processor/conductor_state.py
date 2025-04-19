from dataclasses import dataclass
from logging import Logger

from processor.computation_graph import ComputationGraph
from processor.models.interface.abstract_model import AbstractModel
from processor.table.store.abstract_table_store import AbstractTableStore


@dataclass
class ConductorState:
    table_store: AbstractTableStore
    logger: Logger
    llm: AbstractModel
    embedding_model: AbstractModel
    computation_graph: ComputationGraph
