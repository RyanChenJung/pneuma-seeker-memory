from abc import ABC, abstractmethod
from processor.types.llm_option import LLMOption
from processor.types.message import Message


class ModelInterface(ABC):
    @abstractmethod
    def load_model(self):
        """Loads the model's weight checkpoint."""
        pass

    @abstractmethod
    def load_tokenizer(self):
        """Loads the model's tokenizer."""
        pass

    @abstractmethod
    def chat(self, messages: list[Message], llm_option: LLMOption = LLMOption()) -> str:
        """Chats with the model."""
        pass
