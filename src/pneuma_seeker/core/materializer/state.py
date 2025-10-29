# src/pneuma_seeker/core/materializer/state.py
from pneuma_seeker.core.ir_system.data_model import AbstractDocument


class MaterializerState:
    def __init__(self) -> None:
        self.retrieved_tables: list[AbstractDocument] = []
        self.intermediate_tables: set[AbstractDocument] = set()
        self.web_search_result: AbstractDocument | None = None

    def add_intermediate_table(self, table: AbstractDocument):
        if table in self.intermediate_tables:
            self.intermediate_tables.remove(table)
        self.intermediate_tables.add(table)

    def reset(self) -> None:
        self.retrieved_tables = []
        self.intermediate_tables = set()
        self.web_search_result = None
