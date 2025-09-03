import os

from collections.abc import Generator
from typing import Optional

from numpy import ndarray
from openai import NOT_GIVEN, OpenAI

from pneuma_seeker.model.option import EmbeddingModelOption, LLMOption
from pneuma_seeker.model.llm_message import LLMMessage
from pneuma_seeker.model.interface.abstract_model import AbstractModel


class O(AbstractModel):
    def __init__(
        self,
        model_name: str = "o4-mini",
        env_name="OPENAI_API_KEY",
        base_url: Optional[str] = None,
    ):
        self.client = OpenAI(api_key=os.getenv(env_name), base_url=base_url)
        self.model_name = model_name

    def load_model(self):
        # OpenAI API does not require model loading
        pass

    def load_tokenizer(self):
        # Tokenizer is handled internally by the API
        pass

    def chat(
        self, messages: list[LLMMessage], llm_option: Optional[LLMOption] = None
    ) -> Generator[str, None, None]:
        max_completion_tokens = None
        json_mode = False
        stream = False
        if llm_option:
            max_completion_tokens = llm_option.max_new_tokens
            json_mode = llm_option.json_mode
            stream = llm_option.stream

        if stream:
            # Stream response as generator of chunks
            response_stream = self.client.chat.completions.create(
                messages=messages,  # type: ignore
                model=self.model_name,
                seed=42,
                temperature=1,
                max_completion_tokens=max_completion_tokens,
                response_format={"type": "json_object"} if json_mode else NOT_GIVEN,
                stream=stream,
            )  # type: ignore

            for event in response_stream:
                if event.choices[0].delta.content:
                    chunk = event.choices[0].delta.content
                    print(chunk, end="", flush=True)  # Optional live print
                    yield chunk

        else:
            # Non-streaming version (current behavior)
            gpt_output = (
                self.client.chat.completions.create(
                    messages=messages,  # type: ignore
                    model=self.model_name,
                    seed=42,
                    temperature=1,
                    max_completion_tokens=max_completion_tokens,
                    response_format={"type": "json_object"} if json_mode else NOT_GIVEN,
                )
                .choices[0]
                .message.content
            )

            response = gpt_output or ""
            print(f"O model output: {response}")
            yield response

    def batch_chat(
        self,
        batch_messages: list[list[LLMMessage]],
        llm_option: Optional[LLMOption] = None,
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
