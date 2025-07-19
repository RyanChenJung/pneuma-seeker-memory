from abc import ABC, abstractmethod
from typing import Any


class AbstractOperation(ABC):
    @abstractmethod
    def execute(self, *operands: Any, **kwargs) -> Any:
        """
        Executes the operation on the arguments (operands), which DataFrames, text, etc.
        """
        pass

    @abstractmethod
    def describe(self) -> str:
        """
        Returns a string description of this operation for LLM prompt context.
        """
        pass
