from collections.abc import Generator
from logging import Logger
from typing import Optional

from numpy import ndarray
from pneuma_seeker.services.language_model.abstract_model import AbstractModel
from pneuma_seeker.shared.schemas.language_model.message import LLMMessage
from pneuma_seeker.shared.schemas.language_model.option import EmbeddingModelOption, LLMOption
from pneuma_seeker.shared.config import Config


class MockEmbedModel(AbstractModel):
    def load_model(self):
        """Loads the model's weight checkpoint."""
        pass

    def load_tokenizer(self):
        """Loads the model's tokenizer."""
        pass

    def chat(
        self, messages: list[LLMMessage], llm_option: Optional[LLMOption] = None
    ) -> Generator[str, None, None]:
        """Chats with the model."""
        yield ""

    def batch_chat(
        self,
        batch_messages: list[list[LLMMessage]],
        llm_option: Optional[LLMOption] = None,
    ) -> tuple[list[str], int]:
        """
        Chats (in batch) with the model.
        """
        return ([], -1)

    def encode(
        self,
        texts: list[str],
        embed_model_option: EmbeddingModelOption = EmbeddingModelOption(),
    ) -> ndarray:
        return ndarray(0)

    def __init__(self):
        pass
