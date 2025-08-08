from numpy import ndarray
from typing import Optional
from sentence_transformers import SentenceTransformer

from pneuma_seeker.model.option import EmbeddingModelOption, LLMOption
from pneuma_seeker.model.llm_message import LLMMessage
from pneuma_seeker.model.interface.abstract_model import AbstractModel


class EmbeddingModel(AbstractModel):
    def __init__(self, model_name: str = "BAAI/bge-base-en-v1.5"):
        self.model_name = model_name
        self.model = None

    def load_model(self):
        if self.model is None:
            self.model = SentenceTransformer(self.model_name)

    def load_tokenizer(self):
        # No need to load tokenizer
        pass

    def chat(
        self, messages: list[LLMMessage], llm_option: Optional[LLMOption] = None
    ) -> str:
        """Chats with the model."""
        raise NotImplementedError("Embedding model does not support chat.")
    
    def batch_chat(self, batch_messages, llm_option = None):
        raise NotImplementedError("Embedding model does not support batch chat.")

    def encode(
        self,
        texts: str | list[str],
        embed_model_option: EmbeddingModelOption = EmbeddingModelOption(),
    ) -> ndarray:
        """Embed texts."""
        self.load_model()
        if isinstance(texts, str):
            texts = [texts]
        return self.model.encode(
            texts,
            batch_size=embed_model_option.batch_size,
            show_progress_bar=False,
            device="cuda",
        )
