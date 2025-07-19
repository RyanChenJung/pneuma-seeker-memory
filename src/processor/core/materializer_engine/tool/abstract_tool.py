from abc import ABC, abstractmethod
from typing import Any


class AbstractTool(ABC):
    @abstractmethod
    def execute(self, argument: Any, **kwargs) -> Any:
        """
        Executes the argument (e.g., Python code, SQL query) using the tool.
        Additional keyword arguments can provide runtime context, such as:
        - tables: dict[str, DataFrame]
        - config: dict
        - doc_context: list[AbstractDocument]
        etc.
        """
        pass

    @abstractmethod
    def describe(self) -> str:
        """
        Returns a string description of this tool for LLM prompt context.
        """
        pass
