from logging import Logger
from typing import Optional

from numpy import ndarray

from pneuma_seeker.services.language_model.abstract_model import AbstractModel
from pneuma_seeker.shared.config import Config
from pneuma_seeker.shared.schemas.language_model.message import LLMMessage
from pneuma_seeker.shared.schemas.language_model.option import (
    EmbeddingModelOption,
    LLMOption,
)


class MockLLM(AbstractModel):
    """Simple deterministic LLM mock that returns queued JSON strings."""

    def __init__(self, config: Config, logger: Logger, responses=None):
        self._responses = list(responses or [])

    def chat(self, messages: list[LLMMessage], llm_option: Optional[LLMOption] = None):
        # return a list (chat API returns iterable); use last queued response or default
        if not self._responses:
            yield '{"step_type":"operation","name":"noop","args":{}}'
            return
        yield self._responses.pop(0)

    def load_model(self):
        """Loads the model's weight checkpoint."""
        pass

    def load_tokenizer(self):
        """Loads the model's tokenizer."""
        pass

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
        embed_model_option: EmbeddingModelOption | None = None,
    ) -> ndarray:
        """Embed texts."""
        return ndarray([])
