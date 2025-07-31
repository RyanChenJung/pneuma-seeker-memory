import os
from typing import Optional
from numpy import ndarray
from openai import OpenAI
from processor.model.option import EmbeddingModelOption, LLMOption
from processor.model.llm_message import LLMMessage
from processor.model.interface.abstract_model import AbstractModel


class GPT(AbstractModel):
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model_name = model_name

    def load_model(self):
        # OpenAI API does not require model loading
        pass

    def load_tokenizer(self):
        # Tokenizer is handled internally by the API
        pass

    def chat(
        self, messages: list[LLMMessage], llm_option: Optional[LLMOption] = None
    ) -> str:
        top_p = None
        temperature = None
        max_completion_tokens = None

        if llm_option:
            top_p = llm_option.top_p
            temperature = llm_option.temperature
            max_completion_tokens = llm_option.max_new_tokens

        gpt_output = self.client.chat.completions.create(
            messages=messages,
            model=self.model_name,
            seed=42,
            top_p=top_p,
            temperature=temperature,
            max_completion_tokens=max_completion_tokens,
        ).choices[0].message.content
        response = ""
        if gpt_output:
            response = gpt_output
        return response

    def batch_chat(
        self, batch_messages: list[list[LLMMessage]], llm_option: Optional[LLMOption] = None
    ) -> tuple[list[str], int]:
        """
        Chats (in batch) with the model.
        """
        raise NotImplementedError("GPT does not support batch chat functionality.")

    def encode(
        self,
        texts: str | list[str],
        embed_model_option: EmbeddingModelOption = EmbeddingModelOption(),
    ) -> ndarray:
        """Embed texts."""
        raise NotImplementedError("GPT does not support embedding texts.")
