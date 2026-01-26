from collections.abc import Generator
from logging import Logger
from typing import Optional

import numpy as np
from openai import AzureOpenAI
from pneuma_seeker.model.interface.abstract_model import AbstractModel
from pneuma_seeker.shared.schemas.language_model.message import LLMMessage
from pneuma_seeker.shared.schemas.language_model.option import EmbeddingModelOption, LLMOption
from pneuma_seeker.shared.config import Config


class AzureOpenAIEmbedModel(AbstractModel):
    def __init__(
        self,
        model_name: str,
        config: Config,
        logger: Logger,
    ):
        self.client = AzureOpenAI(
            api_version=config.AZURE_API_VERSION,
            azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
            api_key=config.AZURE_OPENAI_API_KEY,
        )
        self.model_name = model_name
        self.logger = logger

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
        embed_model_option: EmbeddingModelOption = EmbeddingModelOption(),
    ) -> np.ndarray:
        if not texts:
            return np.empty((0, 0))

        embeddings: list[list[float]] = []
        for i in range(0, len(texts), embed_model_option.batch_size):
            batch = texts[i : i + embed_model_option.batch_size]

            response = self.client.embeddings.create(
                input=batch,
                model=self.model_name,
            )

            for item in response.data:
                embeddings.append(item.embedding)

        return np.asarray(embeddings, dtype=np.float32)
