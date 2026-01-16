from collections.abc import Generator
from logging import Logger
from typing import Optional

from numpy import ndarray
from openai import AzureOpenAI

from pneuma_seeker.model.interface.abstract_model import AbstractModel
from pneuma_seeker.model.llm_message import LLMMessage
from pneuma_seeker.model.option import EmbeddingModelOption, LLMOption
from pneuma_seeker.utils.config import Config


class AzureOpenAILLM(AbstractModel):
    def __init__(
        self,
        model_name: str,
        config: Config,
        logger: Logger,
    ):
        self.client = AzureOpenAI(
            api_version=config.AZURE_API_VERSION,
            azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
            api_key=config.AZURE_OPENAI_API_KEY,
        )
        self.model_name = model_name
        self.logger = logger

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
        temperature = 1
        if llm_option:
            max_completion_tokens = llm_option.max_new_tokens
            json_mode = llm_option.json_mode
            stream = llm_option.stream
            if llm_option.temperature:
                temperature = llm_option.temperature

        if stream:
            # Stream response as generator of chunks
            if json_mode:
                response_stream = self.client.chat.completions.create(
                    messages=messages,  # type: ignore
                    model=self.model_name,
                    seed=42,
                    temperature=temperature,
                    max_completion_tokens=max_completion_tokens,
                    response_format={"type": "json_object"},
                    stream=stream,
                )  # type: ignore
            else:
                response_stream = self.client.chat.completions.create(
                    messages=messages,  # type: ignore
                    model=self.model_name,
                    seed=42,
                    temperature=temperature,
                    max_completion_tokens=max_completion_tokens,
                    stream=stream,
                )  # type: ignore

            for event in response_stream:
                if not event.choices:  # skip keep-alives or DONE packets
                    continue
                delta = event.choices[0].delta
                if hasattr(delta, "content") and delta.content:
                    chunk = delta.content
                    yield chunk

        else:
            # Non-streaming version (current behavior)
            if json_mode:
                gpt_output = (
                    self.client.chat.completions.create(
                        messages=messages,  # type: ignore
                        model=self.model_name,
                        seed=42,
                        temperature=temperature,
                        max_completion_tokens=max_completion_tokens,
                        response_format={"type": "json_object"},
                    )
                    .choices[0]
                    .message.content
                )
            else:
                gpt_output = (
                    self.client.chat.completions.create(
                        messages=messages,  # type: ignore
                        model=self.model_name,
                        seed=42,
                        temperature=temperature,
                        max_completion_tokens=max_completion_tokens,
                    )
                    .choices[0]
                    .message.content
                )

            response = gpt_output or ""
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
        texts: list[str],
        embed_model_option: EmbeddingModelOption = EmbeddingModelOption(),
    ) -> ndarray:
        """Embed texts."""
        raise NotImplementedError("GPT does not support embedding texts.")
