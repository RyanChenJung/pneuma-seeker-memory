# core/api/language_model.py
from logging import Logger

from tiktoken import encoding_for_model

from pneuma_seeker.services.language_model.model_factory import get_embed_model, get_llm
from pneuma_seeker.shared.config import Config
from pneuma_seeker.shared.schemas.language_model.message import LLMMessage
from pneuma_seeker.shared.schemas.language_model.option import (
    EmbeddingModelOption,
    LLMOption,
)


class LanguageModelAPI:
    """API client for interacting with the Language Model Service."""

    def __init__(self, config: Config, logger: Logger):
        self.config = config
        self.logger = logger
        self.llm = get_llm(self.config)(self.config, self.logger)
        self.embed_model = get_embed_model(self.config)(self.config, self.logger)

    def chat(
        self,
        messages: list[LLMMessage],
        llm_option: LLMOption | None = None,
    ):
        return self.llm.chat(messages, llm_option)

    def batch_chat(
        self,
        batch_messages: list[list[LLMMessage]],
        llm_option: LLMOption | None = None,
    ) -> tuple[list[str], int]:
        return self.llm.batch_chat(batch_messages, llm_option)

    def encode(
        self,
        texts: str | list[str],
        embed_model_option: EmbeddingModelOption | None = None,
    ):
        if isinstance(texts, str):
            texts = [texts]
        return self.embed_model.encode(texts, embed_model_option)

    def encode_tokenizer(
        self,
        texts: str | list[str],
    ) -> list[int]:
        if len(texts) == 0:
            return [0]
        enc = encoding_for_model("o4-mini")
        return [len(enc.encode(text)) for text in texts]
