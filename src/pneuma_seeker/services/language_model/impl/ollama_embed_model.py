from collections.abc import Generator
from logging import Logger
from typing import Optional

import numpy as np
import requests

from pneuma_seeker.services.language_model.abstract_model import AbstractModel
from pneuma_seeker.shared.config import Config
from pneuma_seeker.shared.schemas.language_model.message import LLMMessage
from pneuma_seeker.shared.schemas.language_model.option import (
    EmbeddingModelOption,
    LLMOption,
)


class OllamaEmbedModel(AbstractModel):
    def __init__(
        self,
        config: Config,
        logger: Logger,
    ):
        self.config = config
        self.logger = logger
        self.base_url = "http://localhost:11434"

    def load_model(self):
        # Ollama lazily loads models on request
        pass

    def load_tokenizer(self):
        # Tokenizer is handled internally by the model
        pass

    def chat(
        self, messages: list[LLMMessage], llm_option: Optional[LLMOption] = None
    ) -> Generator[str, None, None]:
        raise NotImplementedError(
            "Ollama embedding model does not support chat functionality."
        )

    def batch_chat(
        self,
        batch_messages: list[list[LLMMessage]],
        llm_option: Optional[LLMOption] = None,
    ) -> tuple[list[str], int]:
        raise NotImplementedError(
            "Ollama embedding model does not support batch chat functionality."
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

            response = requests.post(
                f"{self.base_url}/api/embed",
                json={
                    "model": "qwen3-embedding",
                    "input": batch,
                },
            )

            if response.status_code != 200:
                raise RuntimeError(
                    f"Ollama embedding request failed: {response.status_code} {response.text}"
                )

            data = response.json()

            # Expected: {"embeddings": [[...], [...]]}
            batch_embeddings = data.get("embeddings", [])
            embeddings.extend(batch_embeddings)

        return np.asarray(embeddings, dtype=np.float32)
