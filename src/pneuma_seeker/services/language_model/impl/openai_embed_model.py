from collections.abc import Generator
from logging import Logger
from typing import Optional

import numpy as np
from openai import OpenAI
from pneuma_seeker.services.language_model.abstract_model import AbstractModel
from pneuma_seeker.shared.schemas.language_model.message import LLMMessage
from pneuma_seeker.shared.schemas.language_model.option import EmbeddingModelOption, LLMOption
from pneuma_seeker.shared.config import Config


class OpenAIEmbedModel(AbstractModel):
    def __init__(
        self,
        config: Config,
        logger: Logger,
    ):
        self.config = config
        self.logger = logger
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)

    def load_model(self):
        # OpenAI API does not require model loading
        pass

    def load_tokenizer(self):
        # Tokenizer is handled internally by the API
        pass

    def chat(
        self, messages: list[LLMMessage], llm_option: Optional[LLMOption] = None
    ) -> Generator[str, None, None]:
        raise NotImplementedError(
            "OpenAI embedding model does not support chat functionality."
        )

    def batch_chat(
        self,
        batch_messages: list[list[LLMMessage]],
        llm_option: Optional[LLMOption] = None,
    ) -> tuple[list[str], int]:
        """
        Chats (in batch) with the model.
        """
        raise NotImplementedError(
            "OpenAI embedding model does not support batch chat functionality."
        )

    def encode(
        self,
        texts: list[str],
        embed_model_option: EmbeddingModelOption | None = None,
    ) -> np.ndarray:
        if not texts:
            return np.empty((0, 0))
        
        if embed_model_option is None:
            embed_model_option = EmbeddingModelOption()

        embeddings: list[list[float]] = []
        for i in range(0, len(texts), embed_model_option.batch_size):
            batch = texts[i : i + embed_model_option.batch_size]

            response = self.client.embeddings.create(
                input=batch,
                model=self.config.EMBED_MODEL_PATH,
            )

            for item in response.data:
                embeddings.append(item.embedding)

        return np.asarray(embeddings, dtype=np.float32)
