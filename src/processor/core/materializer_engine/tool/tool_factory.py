from enum import Enum
from typing import Type
from processor.core.materializer_engine.tool.abstract_tool import AbstractTool
from processor.core.materializer_engine.tool.impl.python_interpreter import (
    PythonInterpreter,
)
from processor.core.materializer_engine.tool.impl.sql_engine import SQLEngine


class ToolType(Enum):
    PYTHON_INTERPRETER = "Python"
    SQL_ENGINE = "SQL"


class ToolFactory:
    def __init__(self):
        self.python_interpreter = PythonInterpreter()
        self.sql_engine = SQLEngine()

    def get_tool(self, tool_type: ToolType) -> Type[AbstractTool]:
        if tool_type == ToolType.PYTHON_INTERPRETER:
            return self.python_interpreter
        elif tool_type == ToolType.SQL_ENGINE:
            return self.sql_engine
