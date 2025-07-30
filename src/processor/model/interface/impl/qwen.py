from typing import Optional
from numpy import ndarray
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
)
from transformers.trainer_utils import set_seed
from torch import cuda, manual_seed

from processor.model.interface.abstract_model import AbstractModel
from processor.model.llm_message import LLMMessage, Role
from processor.model.option import EmbeddingModelOption, LLMOption


class Qwen(AbstractModel):
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model = None
        self.tokenizer = None

    def load_model(self):
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name, torch_dtype="auto", device_map="auto"
        )

    def load_tokenizer(self):
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)

    def chat(
        self, messages: list[LLMMessage], llm_option: Optional[LLMOption] = None
    ) -> str:
        if llm_option is None:
            llm_option = LLMOption()
        if self.model is None:
            self.load_model()
        if self.tokenizer is None:
            self.load_tokenizer()

        text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
        )
        model_inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)

        if llm_option.seed is not None:
            set_seed(llm_option.seed, True)
            manual_seed(llm_option.seed)
            if cuda.is_available():
                cuda.manual_seed_all(llm_option.seed)
        else:
            set_seed(42, True)
            manual_seed(42)
            if cuda.is_available():
                cuda.manual_seed_all(42)

        generated_ids = self.model.generate(
            **model_inputs,
            max_new_tokens=(
                llm_option.max_new_tokens
                if llm_option.max_new_tokens is not None
                else 1000000
            ),
            do_sample=llm_option.do_sample,
            temperature=llm_option.temperature,
            top_p=llm_option.top_p,
            top_k=llm_option.top_k,
        )
        generated_ids = [
            output_ids[len(input_ids) :]
            for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]

        response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[
            0
        ]
        print(f"QWEN: response: {response}")
        # if llm_option.json_mode:
        #     fixing_iteration = 0
        #     while not self.is_valid_json(response) and fixing_iteration <= 5:
        #         appended_messages = messages + [
        #             LLMMessage(role=Role.ASSISTANT.value, content=response),
        #             LLMMessage(
        #                 role=Role.USER.value,
        #                 content="The JSON is invalid and hence cannot be parsed. Please fix it.",
        #             ),
        #         ]
        #         response = self.chat(appended_messages)
        #         fixing_iteration += 1
        return response

    # def batch_chat(
    #     self, batch_messages: list[list[LLMMessage]], llm_option: Optional[LLMOption] = None
    # ):
    #     pipeline = self.__get_text_gen_pipeline()
    #     if llm_option is None:
    #         llm_option = LLMOption()
    #     batch_size = 1
    #     if llm_option.batch_size:
    #         batch_size = llm_option.batch_size

    #     repeat_batch_size_1 = 0
    #     while True:
    #         try:
    #             set_seed(42, deterministic=True)
    #             answers = pipeline(
    #                 batch_messages, truncation=True, batch_size=batch_size
    #             )
    #             print(answers)
    #             results: list[list[dict[str,str]]] = []
    #             if isinstance(answers[0], dict):
    #                 answers = [answers]
    #             for answer in answers:
    #                 results.append(answer[0]["generated_text"])
    #             return (results, batch_size)
    #         except:
    #             prev_batch_size = batch_size
    #             batch_size = max(batch_size - 10, 1)
    #             if prev_batch_size == batch_size and batch_size == 1:
    #                 repeat_batch_size_1 += 1
    #             if repeat_batch_size_1 == 5:
    #                 raise RuntimeError("Batch size has repeatedly been 1; the GPU is not capable enough.")
    #             cuda.empty_cache()
    #             print(f"Reducing batch size to {batch_size}")

    def batch_chat(
        self,
        batch_messages: list[list[LLMMessage]],
        llm_option: Optional[LLMOption] = None,
    ) -> tuple[list[str], int]:
        """
        Chats (in batch) with the model.

        Args:
            batch_messages: A list of message sequences (each is a list of LLMMessage objects).
            llm_option: LLMOption specifying generation parameters like batch_size, temperature, etc.

        Returns:
            A list of generated response strings (one per conversation).
        """
        print(f"batch_messages: {batch_messages}")
        if llm_option is None:
            llm_option = LLMOption()
        if self.model is None:
            self.load_model()
        if self.tokenizer is None:
            self.load_tokenizer()

        if llm_option.seed is not None:
            set_seed(llm_option.seed, True)

        # Convert each conversation to a prompt
        prompts = [
            self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
            for messages in batch_messages
        ]

        # Define batch size
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
                        **model_inputs,
                        max_new_tokens=(
                            llm_option.max_new_tokens
                            if llm_option.max_new_tokens
                            else 10000
                        ),
                        do_sample=llm_option.do_sample,
                        temperature=llm_option.temperature,
                        top_p=llm_option.top_p,
                        top_k=llm_option.top_k,
                    )

                    # Remove prompt tokens from the output to keep only the generation
                    cleaned_generated_ids = [
                        output_ids[len(input_ids) :]
                        for input_ids, output_ids in zip(
                            model_inputs["input_ids"], generated_ids
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
        texts: str | list[str],
        embed_model_option: EmbeddingModelOption = EmbeddingModelOption(),
    ) -> ndarray:
        """Embed texts."""
        raise NotImplementedError("Qwen does not support embedding texts.")
