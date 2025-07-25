from enum import Enum
from logging import Logger
from processor.core.materializer_engine.tool.abstract_tool import AbstractTool
from processor.core.materializer_engine.tool.impl.document_retriever import (
    DocumentRetriever,
)
from processor.core.materializer_engine.tool.impl.python_executor import PythonExecutor
from processor.core.materializer_engine.tool.impl.sql_executor import SQLExecutor
from processor.model.interface.abstract_model import AbstractModel


class ToolType(Enum):
    PYTHON_EXECUTOR = "Python Executor"
    SQL_EXECUTOR = "SQL Executor"
    DOCUMENT_RETRIEVER = "Document Retriever"


class ToolFactory:
    def __init__(self, llm: AbstractModel, embed_model: AbstractModel, logger: Logger):
        self.python_executor = PythonExecutor(logger)
        self.sql_executor = SQLExecutor(logger)
        self.document_retriever = DocumentRetriever(llm, embed_model, logger)

    def available_tools(self):
        return [
            self.python_executor,
            self.sql_executor,
            self.document_retriever,
        ]

    def get_tool(self, tool_type: str) -> AbstractTool:
        if tool_type == ToolType.PYTHON_EXECUTOR.value:
            return self.python_executor
        elif tool_type == ToolType.SQL_EXECUTOR:
            return self.sql_executor
        else:
            return self.document_retriever
