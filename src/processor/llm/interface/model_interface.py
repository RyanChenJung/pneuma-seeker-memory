from abc import ABC, abstractmethod
from processor.src.processor.llm.interface.qwen import Qwen
from processor.src.processor.llm.interface.gemma import Gemma
from processor.src.processor.llm.interface.llama import Llama
from src.processor.types.message import Message


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
    def chat(self, messages: list[Message]) -> str:
        """Chats with the model."""
        pass


def get_model(ckp: str) -> ModelInterface:
    """Factory function to return the correct model instance."""
    normalized_ckp = ckp.lower()
    if "qwen" in normalized_ckp:
        return Qwen
    elif "llama" in normalized_ckp:
        return Llama
    elif "gemma" in normalized_ckp:
        return Gemma
    else:
        raise ValueError(f"No interface implementation for this checkpoint: {ckp}")
