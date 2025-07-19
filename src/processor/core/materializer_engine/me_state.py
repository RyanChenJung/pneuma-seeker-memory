from pandas import DataFrame
from processor.core.ir_system.ir_data_model import AbstractDocument
from processor.model.llm_message import LLMMessage


class MaterializerState:
    def __init__(self) -> None:
        self.action_history: list[LLMMessage] = []
        self.current_retrieved_documents: set[AbstractDocument] = set()
        self.intermediate_tables: dict[str, DataFrame] = dict()  # For temporary results
        self.materialized_target_schemas: dict[str, DataFrame] = dict()  # Final schemas only
    
    def reset(self) -> None:
        self.action_history = []
        self.current_retrieved_documents = set()
        self.intermediate_tables = dict()
        self.materialized_target_schemas = dict()
