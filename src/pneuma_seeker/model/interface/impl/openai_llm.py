from logging import Logger

from collections.abc import Generator
from typing import Optional

from numpy import ndarray
from openai import Omit, OpenAI

from pneuma_seeker.shared.schemas.language_model.option import EmbeddingModelOption, LLMOption
from pneuma_seeker.shared.schemas.language_model.message import LLMMessage
from pneuma_seeker.model.interface.abstract_model import AbstractModel
from pneuma_seeker.shared.config import Config


class OpenAILLM(AbstractModel):
    def __init__(
        self,
        model_name: str,
        config: Config,
        logger: Logger,
    ):
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
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
        temperature = 0
        if llm_option:
            max_completion_tokens = llm_option.max_new_tokens
            json_mode = llm_option.json_mode
            stream = llm_option.stream
            if llm_option.temperature:
                temperature = llm_option.temperature

        if stream:
            # Stream response as generator of chunks
            response_stream = self.client.chat.completions.create(
                messages=messages,  # type: ignore
                model=self.model_name,
                seed=42,
                temperature=temperature,
                max_completion_tokens=max_completion_tokens,
                response_format={"type": "json_object"} if json_mode else Omit(),
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
                    temperature=temperature,
                    max_completion_tokens=max_completion_tokens,
                    response_format={"type": "json_object"} if json_mode else Omit(),
                )
                .choices[0]
                .message.content
            )

            response = gpt_output or ""
            self.logger.info(f"[OPENAI] Model output: {response}")
            yield response

    def batch_chat(
        self,
        batch_messages: list[list[LLMMessage]],
        llm_option: Optional[LLMOption] = None,
    ) -> tuple[list[str], int]:
        """
        Chats (in batch) with the model.
        """
        responses: list[str] = []

        for messages in batch_messages:
            response = "".join(self.chat(messages, llm_option))
            responses.append(response)

        batch_size = (
            llm_option.batch_size if llm_option and llm_option.batch_size else 1
        )
        return responses, batch_size

    def encode(
        self,
        texts: list[str],
        embed_model_option: EmbeddingModelOption = EmbeddingModelOption(),
    ) -> ndarray:
        """Embed texts."""
        raise NotImplementedError("GPT does not support embedding texts.")
