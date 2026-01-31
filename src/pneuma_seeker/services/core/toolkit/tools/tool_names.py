from enum import Enum


class ToolNames(Enum):
    PYTHON_EXECUTOR = "python_executor"
    SEMANTIC_OPERATOR = "semantic_operator"


class ToolExecutionStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"
