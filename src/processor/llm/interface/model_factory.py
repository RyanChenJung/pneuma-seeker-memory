from typing import Type
from processor.llm.interface.impl.qwen import Qwen
from processor.llm.interface.impl.gpt import GPT
from processor.llm.interface.impl.gemma import Gemma
from processor.llm.interface.impl.llama import Llama
from processor.llm.interface.model import AbstractModel


def get_model(ckp: str) -> Type[AbstractModel]:
    """Factory function to return the correct model instance."""
    normalized_ckp = ckp.lower()
    if "qwen" in normalized_ckp:
        return Qwen
    elif "llama" in normalized_ckp:
        return Llama
    elif "gemma" in normalized_ckp:
        return Gemma
    elif "gpt" in normalized_ckp:
        return GPT
    else:
        raise ValueError(f"No interface implementation for this checkpoint: {ckp}")
