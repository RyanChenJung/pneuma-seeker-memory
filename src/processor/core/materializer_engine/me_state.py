from pandas import DataFrame
from processor.core.ir_system.ir_data_model import AbstractDocument, RetrieverType


class MaterializerState:
    def __init__(self) -> None:
        self.current_retrieved_documents: dict[RetrieverType, list[AbstractDocument]] = dict()
        self.intermediate_tables: dict[str, DataFrame] = dict()  # For temporary results
        self.materialized_target_schemas: dict[str, DataFrame] = dict()  # Final schemas only
    
    def reset(self) -> None:
        self.current_retrieved_documents = dict()
        self.intermediate_tables = dict()
        self.materialized_target_schemas = dict()
