from collections.abc import Generator
from logging import Logger

from numpy import ndarray
from sentence_transformers import SentenceTransformer

from pneuma_seeker.model.interface.abstract_model import AbstractModel
from pneuma_seeker.model.llm_message import LLMMessage
from pneuma_seeker.model.option import EmbeddingModelOption, LLMOption
from pneuma_seeker.utils.config import Config


class EmbeddingModel(AbstractModel):
    def __init__(self, model_name: str, config: Config, logger: Logger):
        """
        Designed with "BAAI/bge-base-en-v1.5" in mind, loaded using SentenceTransformers.
        """
        self.model_name = model_name
        self.model = None
        self.config = config
        self.logger = logger

    def load_model(self):
        if self.model is None:
            self.model = SentenceTransformer(self.model_name)

    def load_tokenizer(self):
        # No need to load tokenizer
        pass

    def chat(
        self, messages: list[LLMMessage], llm_option: LLMOption | None = None
    ) -> Generator[str, None, None]:
        raise NotImplementedError("Embedding model does not support chat.")

    def batch_chat(self, batch_messages, llm_option=None):
        raise NotImplementedError("Embedding model does not support batch chat.")

    def encode(
        self,
        texts: list[str],
        embed_model_option: EmbeddingModelOption = EmbeddingModelOption(),
    ) -> ndarray:
        """Embed texts."""
        self.load_model()
        if isinstance(texts, str):
            texts = [texts]
        return self.model.encode(  # type: ignore
            texts,
            batch_size=embed_model_option.batch_size,
            show_progress_bar=False,
            device="cuda",
        )
