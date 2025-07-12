from pandas import DataFrame
from processor.model.interface.model_factory import get_llm
from processor.core.materializer_engine.operation.operation_factory import OperationFactory
from processor.model.interface.abstract_model import AbstractModel
from processor.model.interface.model_factory import get_llm

class LLMPlanner:
    def __init__(self, llm_path: str):
        self.llm: AbstractModel = None  # Not yet initialized (loaded)
        self.llm_path = llm_path
        self.thought_history = []
        self.operation_factory = OperationFactory()
        self.tool_factory = ToolFactory()
    
    def load_llm(self):
        """
        Loads the LLM if not yet done.
        """
        if self.llm is None:
            self.llm = get_llm(self.llm_path)()
    
    def materialize_target_schemas(self, target_schemas: list[DataFrame], sqls: list[str]) -> list[DataFrame]:
        """
        Materializes the given Target Schemas subject to SQLs over them.
        """
        pass
