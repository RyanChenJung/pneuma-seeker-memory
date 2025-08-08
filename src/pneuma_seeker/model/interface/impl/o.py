import os
from typing import Optional
from numpy import ndarray
from openai import OpenAI
from pneuma_seeker.model.option import EmbeddingModelOption, LLMOption
from pneuma_seeker.model.llm_message import LLMMessage
from pneuma_seeker.model.interface.abstract_model import AbstractModel


class O(AbstractModel):
    def __init__(self, model_name: str = "o4-mini"):
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
        max_completion_tokens = None
        json_mode = False
        if llm_option:
            max_completion_tokens = llm_option.max_new_tokens
            json_mode = llm_option.json_mode

        if json_mode:
            gpt_output = self.client.chat.completions.create(
                messages=messages,
                model=self.model_name,
                seed=42,
                temperature=1,
                max_completion_tokens=max_completion_tokens,
                response_format={"type": "json_object"},
            ).choices[0].message.content
        else:
            gpt_output = self.client.chat.completions.create(
                messages=messages,
                model=self.model_name,
                seed=42,
                temperature=1,
                max_completion_tokens=max_completion_tokens,
            ).choices[0].message.content
        response = ""
        if gpt_output:
            response = gpt_output
            print(f"O model output: {response}")
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
