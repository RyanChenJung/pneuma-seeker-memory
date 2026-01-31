from abc import ABC, abstractmethod
from logging import Logger
from typing import Any

from pandas import DataFrame

from pneuma_seeker.shared.config import Config


class AbstractTool(ABC):
    @abstractmethod
    def __init__(self, config: Config, logger: Logger, **kwargs):
        pass

    @abstractmethod
    def get_tool_name(self) -> str:
        """Returns the name of the tool."""
        pass

    @abstractmethod
    def get_tool_description(self) -> str:
        """Returns the description of the tool."""
        pass

    @abstractmethod
    def execute(self, tool_input: dict[str, Any]) -> DataFrame:
        """Executes the tool with the given input and returns the output."""
        pass
