from pandas import DataFrame
from processor.core.ir_system.ir_data_model import AbstractDocument, RetrieverType


class MaterializerState:
    def __init__(self) -> None:
        self.current_retrieved_documents: dict[RetrieverType, list[AbstractDocument]] = dict()
        self.intermediate_tables: dict[str, DataFrame] = dict()  # For temporary results
    
    def reset(self) -> None:
        self.current_retrieved_documents = dict()
        self.intermediate_tables = dict()
