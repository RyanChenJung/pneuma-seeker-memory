import json
from abc import ABC, abstractmethod
from collections.abc import Generator
from logging import Logger
from typing import Optional

from numpy import ndarray

from pneuma_seeker.shared.config import Config
from pneuma_seeker.shared.parser import parse_json
from pneuma_seeker.shared.schemas.language_model.message import LLMMessage
from pneuma_seeker.shared.schemas.language_model.option import (
    EmbeddingModelOption,
    LLMOption,
)


class AbstractModel(ABC):
    @abstractmethod
    def __init__(self, config: Config, logger: Logger, **kwargs):
        pass

    @abstractmethod
    def load_model(self):
        """Loads the model's weight checkpoint."""
        pass

    @abstractmethod
    def load_tokenizer(self):
        """Loads the model's tokenizer."""
        pass

    @abstractmethod
    def chat(
        self, messages: list[LLMMessage], llm_option: Optional[LLMOption] = None
    ) -> Generator[str, None, None]:
        """Chats with the model."""
        pass

    @abstractmethod
    def batch_chat(
        self,
        batch_messages: list[list[LLMMessage]],
        llm_option: Optional[LLMOption] = None,
    ) -> tuple[list[str], int]:
        """
        Chats (in batch) with the model.
        """
        pass

    @abstractmethod
    def encode(
        self,
        texts: list[str],
        embed_model_option: EmbeddingModelOption | None = None,
    ) -> ndarray:
        """Embed texts."""
        pass

    def is_valid_json(self, text: str):
        try:
            parse_json(text)
            return (True, "")
        except json.JSONDecodeError as j:
            return (False, j)
