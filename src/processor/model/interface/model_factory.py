from typing import Type
from processor.model.interface.impl.embed import EmbeddingModel
from processor.model.interface.impl.o import O
from processor.model.interface.impl.qwen import Qwen
from processor.model.interface.impl.gpt import GPT
from processor.model.interface.impl.gemma import Gemma
from processor.model.interface.impl.llama import Llama
from processor.model.interface.abstract_model import AbstractModel


def get_llm(model_path: str) -> Type[AbstractModel]:
    """Factory function to return the correct LLM instance."""
    normalized_model_path = model_path.lower()
    if "qwen" in normalized_model_path:
        return Qwen
    elif "llama" in normalized_model_path:
        return Llama
    elif "gemma" in normalized_model_path:
        return Gemma
    elif "gpt" in normalized_model_path:
        return GPT
    elif "o3" in normalized_model_path or "o4" in normalized_model_path:
        return O
    else:
        raise ValueError(f"No interface implementation for this model path: {model_path}")

def get_embed_model() -> Type[AbstractModel]:
    """Factory function to return the correct embedding model class."""
    return EmbeddingModel
