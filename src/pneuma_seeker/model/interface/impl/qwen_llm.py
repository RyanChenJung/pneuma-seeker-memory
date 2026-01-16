import json
import re
from typing import Generator, List, Optional

from numpy import ndarray
from torch import cuda, manual_seed
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    Qwen2TokenizerFast,
    Qwen3ForCausalLM,
)
from transformers.trainer_utils import set_seed

from pneuma_seeker.model.interface.abstract_model import AbstractModel
from pneuma_seeker.model.llm_message import LLMMessage, Role
from pneuma_seeker.model.option import EmbeddingModelOption, LLMOption


class Qwen(AbstractModel):
    def __init__(self, model_name: str, config=None, logger=None, **kwargs):
        self.model_name = model_name
        self.model: Qwen3ForCausalLM | None = None
        self.tokenizer: Qwen2TokenizerFast | None = None
        self.config = config
        self.logger = logger

    def load_model(self):
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name, dtype="auto", device_map="auto"
        )

    def load_tokenizer(self):
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.tokenizer.padding_side = "left"
        self.tokenizer.truncation_side = "left"

    def chat(
        self, messages: List[LLMMessage], llm_option: Optional[LLMOption] = None
    ) -> Generator[str, None, None]:
        if llm_option is None:
            llm_option = LLMOption()
        if self.model is None:
            self.load_model()
        if self.tokenizer is None:
            self.load_tokenizer()

        if self.model is None:
            raise RuntimeError("Model failed to be loaded.")
        if self.tokenizer is None:
            raise RuntimeError("Tokenizer failed to be loaded.")

        text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True, enable_thinking=False  # type: ignore
        )
        model_inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)  # type: ignore

        seed = llm_option.seed if llm_option.seed is not None else 42
        set_seed(seed, True)
        manual_seed(seed)
        if cuda.is_available():
            cuda.manual_seed_all(seed)

        generated_ids = self.model.generate(
            **model_inputs,  # type: ignore
            max_new_tokens=(llm_option.max_new_tokens or 1000),
            do_sample=llm_option.do_sample,
            temperature=llm_option.temperature,
            top_p=llm_option.top_p,
            top_k=llm_option.top_k,
        )

        # Remove input tokens
        generated_seq = [
            output_ids[len(input_ids) :]
            for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]

        response = self.tokenizer.batch_decode(generated_seq, skip_special_tokens=True)[
            0
        ]

        if llm_option.json_mode:
            response = self.__sanitize_json_output(response)
            fixing_iteration = 0
            while not self.is_valid_json(response)[0] and fixing_iteration <= 5:
                appended_messages = messages + [
                    LLMMessage(role=Role.ASSISTANT.value, content=response),
                    LLMMessage(
                        role=Role.USER.value,
                        content=f"The JSON is invalid and cannot be parsed. Error: {self.is_valid_json(response)[1]}. Please fix it.",
                    ),
                ]
                # Recursive call accumulates internally and returns final response
                response = next(self.chat(appended_messages, llm_option))
                fixing_iteration += 1

        yield response

    def batch_chat(
        self,
        batch_messages: List[List[LLMMessage]],
        llm_option: Optional[LLMOption] = None,
    ) -> tuple[List[str], int]:
        if llm_option is None:
            llm_option = LLMOption()
        if self.model is None:
            self.load_model()
        if self.tokenizer is None:
            self.load_tokenizer()

        if self.model is None:
            raise RuntimeError("Model failed to be loaded.")
        if self.tokenizer is None:
            raise RuntimeError("Tokenizer failed to be loaded.")

        seed = llm_option.seed if llm_option.seed is not None else 42
        set_seed(seed, True)

        prompts = [
            self.tokenizer.apply_chat_template(
                messages,  # type: ignore
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
            for messages in batch_messages
        ]

        batch_size = llm_option.batch_size or 1
        repeat_batch_size_1 = 0
        while True:
            try:
                all_responses = []
                for i in range(0, len(prompts), batch_size):
                    sub_prompts = prompts[i : i + batch_size]
                    model_inputs = self.tokenizer(
                        sub_prompts, return_tensors="pt", padding=True, truncation=True
                    ).to(self.model.device)

                    generated_ids = self.model.generate(
                        **model_inputs,  # type: ignore
                        max_new_tokens=(llm_option.max_new_tokens or 1000),
                        do_sample=llm_option.do_sample,
                        temperature=llm_option.temperature,
                        top_p=llm_option.top_p,
                        top_k=llm_option.top_k,
                    )

                    cleaned_generated_ids = [
                        output_ids[len(input_ids) :]
                        for input_ids, output_ids in zip(
                            model_inputs.input_ids, generated_ids
                        )
                    ]

                    responses = self.tokenizer.batch_decode(
                        cleaned_generated_ids, skip_special_tokens=True
                    )
                    all_responses.extend(responses)

                return all_responses, batch_size
            except:
                batch_size = max(batch_size - 10, 1)
                if batch_size == 1:
                    repeat_batch_size_1 += 1
                if repeat_batch_size_1 == 5:
                    return [], 1
                cuda.empty_cache()
                print(f"Reducing batch size to {batch_size}")

    def encode(
        self,
        texts: list[str],
        embed_model_option: EmbeddingModelOption = EmbeddingModelOption(),
    ) -> ndarray:
        raise NotImplementedError("Qwen does not support embedding texts.")

    def __sanitize_json_output(self, response: str) -> str:
        response = re.sub(r"^```(?:json)?\s*", "", response)
        response = re.sub(r"\s*```$", "", response)
        response = response.strip()
        if "{" in response:
            response = response[response.index("{") :]

        def escape_newlines_in_strings(match):
            return match.group(0).replace("\n", "\\n")

        response = re.sub(r'"(.*?)"', escape_newlines_in_strings, response, flags=re.S)
        if not response.endswith("}"):
            response += "}"
        json.loads(response)
        return response
