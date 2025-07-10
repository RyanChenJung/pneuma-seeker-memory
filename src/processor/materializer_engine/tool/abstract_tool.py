from enum import Enum
from abc import ABC, abstractmethod

class ToolType(Enum):
    PYTHON_INTERPRETER = 'Python Interpreter'
    SQL_ENGINE = 'SQL Engine'

class AbstractTool(ABC):
    def __init__(self, tool_type: ToolType):
        self.tool_type = tool_type
    
    @abstractmethod
    def execute(self, argument: Any):
        """
        Executes the argument using the tool.
        """
        pass
