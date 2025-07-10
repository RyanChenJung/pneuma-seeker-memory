from enum import Enum
from typing import Type
from processor.materializer.engine.tool.abstract_tool import AbstractTool
from processor.materializer.engine.tool.impl.python_interpreter import PythonInterpreter
from processor.materializer.engine.tool.impl.sql_engine import SQLEngine


class ToolType(Enum):
    PYTHON_INTERPRETER = "Python"
    SQL_ENGINE = "SQL"


def get_tool(self, tool_type: ToolType) -> Type[AbstractTool]:
    if tool_type == ToolType.PYTHON_INTERPRETER:
        return PythonInterpreter
    elif tool_type == ToolType.SQL_ENGINE:
        return SQLEngine
