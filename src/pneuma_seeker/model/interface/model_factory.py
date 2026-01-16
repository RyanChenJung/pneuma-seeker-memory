from typing import Type

from pneuma_seeker.model.interface.abstract_model import AbstractModel
from pneuma_seeker.model.interface.impl.azure_openai_embed_model import (
    AzureOpenAIEmbedModel,
)
from pneuma_seeker.model.interface.impl.azure_openai_llm import AzureOpenAILLM
from pneuma_seeker.model.interface.impl.embed_model import EmbeddingModel
from pneuma_seeker.model.interface.impl.openai_llm import OpenAILLM
from pneuma_seeker.utils.config import Config


def get_llm(model_path: str, config: Config) -> Type[AbstractModel]:
    """Factory function to return the correct LLM instance."""
    normalized_model_path = model_path.lower()
    if (
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


def get_embed_model(model_path: str) -> Type[AbstractModel]:
    """Factory function to return the correct embedding model class."""
    normalized_model_path = model_path.lower()
    if "text-embedding-3-small" in normalized_model_path:
        return AzureOpenAIEmbedModel
    return EmbeddingModel
