from abc import ABC, abstractmethod
from processor.llm.option import LLMOption
from processor.llm.message import LLMMessage
from numpy import ndarray


class AbstractModel(ABC):
    @abstractmethod
    def __init__(self, model_name: str):
        """All implementors must accept a model_name in the constructor."""
        pass

    @abstractmethod
    def load_model(self):
        """Loads the model's weight checkpoint."""
        pass

    @abstractmethod
    def load_tokenizer(self):
        """Loads the model's tokenizer."""
        pass

    @abstractmethod
    def chat(self, messages: list[LLMMessage], llm_option: LLMOption = LLMOption()) -> str:
        """Chats with the model."""
        pass

    def embed(self, text: str) -> ndarray:
        """Embed texts."""
        pass
