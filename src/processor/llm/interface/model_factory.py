from processor.llm.interface.qwen import Qwen
from processor.llm.interface.gemma import Gemma
from processor.llm.interface.llama import Llama
from processor.llm.interface.model_interface import ModelInterface

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