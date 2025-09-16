from typing import Type

from pneuma_seeker.model.interface.abstract_model import AbstractModel
from pneuma_seeker.model.interface.impl.azure_openai_llm import AzureOpenAILLM
from pneuma_seeker.model.interface.impl.embed_model import EmbeddingModel
from pneuma_seeker.model.interface.impl.openai_llm import OpenAILLM
from pneuma_seeker.model.interface.impl.qwen_llm import Qwen
from pneuma_seeker.utils.config import Config


def get_llm(model_path: str, config: Config) -> Type[AbstractModel]:
    """Factory function to return the correct LLM instance."""
    normalized_model_path = model_path.lower()
    if "qwen" in normalized_model_path:
        return Qwen
    elif (
        "gpt" in normalized_model_path
        or "o3" in normalized_model_path
        or "o4" in normalized_model_path
    ):
        if config.USE_AZURE:
            return AzureOpenAILLM
        return OpenAILLM
    else:
        raise ValueError(
            f"No interface implementation for this model path: {model_path}"
        )


def get_embed_model() -> Type[AbstractModel]:
    """Factory function to return the correct embedding model class."""
    return EmbeddingModel
