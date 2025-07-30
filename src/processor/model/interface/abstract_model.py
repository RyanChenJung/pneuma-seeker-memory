from abc import ABC, abstractmethod
import json
from typing import Optional
from processor.model.option import EmbeddingModelOption, LLMOption
from processor.model.llm_message import LLMMessage
from numpy import ndarray


class AbstractModel(ABC):
    @abstractmethod
    def __init__(self, model_name: str):
        """All implementors must accept a model_name in the constructor."""
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
    ) -> str:
        """Chats with the model."""
        pass

    @abstractmethod
    def batch_chat(
        self, batch_messages: list[list[LLMMessage]], llm_option: Optional[LLMOption] = None
    ) -> tuple[list[str], int]:
        """
        Chats (in batch) with the model.
        """
        pass

    @abstractmethod
    def encode(
        self,
        texts: str | list[str],
        embed_model_option: EmbeddingModelOption = EmbeddingModelOption(),
    ) -> ndarray:
        """Embed texts."""
        pass

    def is_valid_json(self, text: str):
        try:
            json.loads(text)
            return (True, '')
        except json.JSONDecodeError as j:
            return (False, j)
