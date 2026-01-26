from logging import Logger

import numpy as np
import requests
from shared.config import Config
from shared.schemas.language_model.message import LLMMessage
from shared.schemas.language_model.option import EmbeddingModelOption, LLMOption


class LanguageModelAPI:
    """API client for interacting with the Language Model Service."""

    def __init__(self, config: Config, logger: Logger):
        self.config = config
        self.logger = logger

    def chat(
        self,
        messages: list[LLMMessage],
        llm_option: LLMOption | None = None,
    ):
        payload = {
            "model_name": self.config.LLM_PATH,
            "messages": [m.model_dump() for m in messages],
            "llm_option": llm_option.model_dump() if llm_option else None,
        }

        # streaming
        if llm_option and llm_option.stream:
            r = requests.post(
                f"{self.config.LM_SERVICE_URL}/chat",
                json=payload,
                stream=True,
                timeout=60,
            )
            r.raise_for_status()

            def generator():
                for chunk in r.iter_content(chunk_size=None):
                    if chunk:
                        yield chunk.decode("utf-8")

            return generator()

        # non-streaming
        r = requests.post(
            f"{self.config.LM_SERVICE_URL}/chat",
            json=payload,
            timeout=60,
        )
        r.raise_for_status()

        return r.json()["text"]

    def batch_chat(
        self,
        batch_messages: list[list[LLMMessage]],
        llm_option: LLMOption | None = None,
    ) -> tuple[list[str], int]:
        payload = {
            "model_name": self.config.LLM_PATH,
            "batch_messages": [
                [m.model_dump() for m in msgs] for msgs in batch_messages
            ],
            "llm_option": llm_option.model_dump() if llm_option else None,
        }

        r = requests.post(
            f"{self.config.LM_SERVICE_URL}/batch_chat",
            json=payload,
            timeout=120,
        )
        r.raise_for_status()

        data = r.json()
        return data["texts"], data["last_batch_size"]

    def encode(
        self,
        texts: str | list[str],
        embed_model_option: EmbeddingModelOption | None = None,
    ):
        if isinstance(texts, str):
            texts = [texts]
        payload = {
            "model_name": self.config.EMBED_MODEL_PATH,
            "texts": texts,
            "embed_model_option": (
                embed_model_option.model_dump() if embed_model_option else None
            ),
        }

        r = requests.post(
            f"{self.config.LM_SERVICE_URL}/encode",
            json=payload,
            timeout=60,
        )
        r.raise_for_status()

        return np.array(r.json()["embeddings"])

    def encode_tokenizer(
        self,
        texts: str | list[str],
        embed_model_option: EmbeddingModelOption | None = None,
    ) -> list[int]:
        if isinstance(texts, str):
            texts = [texts]
        payload = {
            "model_name": self.config.EMBED_MODEL_PATH,
            "texts": texts,
            "embed_model_option": (
                embed_model_option.model_dump() if embed_model_option else None
            ),
        }

        r = requests.post(
            f"{self.config.LM_SERVICE_URL}/encode_tiktoken",
            json=payload,
            timeout=60,
        )
        r.raise_for_status()

        return r.json()["token_counts"]
