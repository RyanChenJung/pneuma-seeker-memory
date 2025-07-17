from numpy import ndarray
from sentence_transformers import SentenceTransformer

from processor.model.option import EmbeddingModelOption, LLMOption
from processor.model.llm_message import LLMMessage
from processor.model.interface.abstract_model import AbstractModel


class EmbeddingModel(AbstractModel):
    def __init__(self, model_name: str = "BAAI/bge-base-en-v1.5"):
        self.model_name = model_name
        self.model = None

    def load_model(self):
        self.model = SentenceTransformer(self.model_name)

    def load_tokenizer(self):
        # No need to load tokenizer
        pass

    def chat(
        self, messages: list[LLMMessage], llm_option: LLMOption = LLMOption()
    ) -> str:
        """Chats with the model."""
        raise NotImplementedError("Embedding model does not support chat.")

    def embed(
        self,
        texts: str | list[str],
        embed_model_option: EmbeddingModelOption = EmbeddingModelOption(),
    ) -> ndarray:
        """Embed texts."""
        if self.model is None:
            self.load_model()
        if isinstance(texts, str):
            texts = [texts]
        return self.model.encode(texts)
