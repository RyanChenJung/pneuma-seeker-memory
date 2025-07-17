from pandas import DataFrame
from processor.core.materializer_engine.tool.tool_factory import ToolFactory
from processor.core.materializer_engine.operation.operation_factory import OperationFactory
from processor.model.interface.abstract_model import AbstractModel


class LLMPlanner:
    def __init__(self, llm: AbstractModel):
        self.llm: AbstractModel = llm
        self.thought_history = []
        self.operation_factory = OperationFactory()
        self.tool_factory = ToolFactory()
    
    def materialize_target_schemas(self, target_schemas: list[DataFrame], sqls: list[str]) -> list[DataFrame]:
        """
        Materializes the given Target Schemas subject to SQLs over them.
        """
        pass
