from enum import Enum
from abc import ABC, abstractmethod
from typing import Any


class ToolType(Enum):
    PYTHON_INTERPRETER = "Python Interpreter"
    SQL_ENGINE = "SQL Engine"


class AbstractTool(ABC):
    @abstractmethod
    def execute(self, argument: Any):
        """
        Executes the argument using the tool.
        """
        pass
