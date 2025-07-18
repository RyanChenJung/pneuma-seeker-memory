from numpy import ndarray
from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed
from torch import cuda

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

    def chat(self, messages: list[LLMMessage], llm_option: LLMOption = None) -> str:
        if llm_option is None:
            llm_option = LLMOption()
        if self.model is None:
            self.load_model()
        if self.tokenizer is None:
            self.load_tokenizer()

        text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        model_inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)

        if llm_option.seed is not None:
            set_seed(llm_option.seed, True)

        generated_ids = self.model.generate(
            **model_inputs,
            max_new_tokens=llm_option if llm_option is not None else 10000,
            do_sample=llm_option.do_sample,
            temperature=llm_option.temperature,
            top_p=llm_option.top_p,
            top_k=llm_option.top_k
        )
        generated_ids = [
            output_ids[len(input_ids) :]
            for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]

        response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[
            0
        ]
        if llm_option.json_mode:
            fixing_iteration = 0
            while not self.is_valid_json(response) and fixing_iteration <= 5:
                appended_messages = messages + [LLMMessage(role=Role.USER.value, content="The JSON is invalid and hence cannot be parsed. Please fix it.")]
                response = self.chat(appended_messages)
                fixing_iteration += 1
        return response

    def batch_chat(
        self, batch_messages: list[list[LLMMessage]], llm_option: LLMOption = None
    ) -> list[list[str], int]:
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

        if llm_option.seed is not None:model
            set_seed(llm_option.seed, True)

        # Convert each conversation to a prompt
        prompts = [
            self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            for messages in batch_messages
        ]

        print(f"Prompts: {prompts}")

        # Define batch size
        batch_size = llm_option.batch_size or 1
        repeat_batch_size_1 = 0
        while True:model
            try:
                all_responses = []
                for i in range(0, len(prompts), batch_size):
                    sub_prompts = prompts[i:i + batch_size]
                    print(f"Sub prompts: {sub_prompts}")
                    model_inputs = self.tokenizer(
                        sub_prompts,
                        return_tensors="pt",
                        padding=True,
                        truncation=True
                    ).to(self.model.device)

                    generated_ids = self.model.generate(
                        **model_inputs,
                        max_new_tokens=llm_option.max_new_tokens if llm_option.max_new_tokens else 10000,
                        do_sample=llm_option.do_sample,
                        temperature=llm_option.temperature,
                        top_p=llm_option.top_p,
                        top_k=llm_option.top_k,
                    )

                    # Remove prompt tokens from the output to keep only the generation
                    cleaned_generated_ids = [
                        output_ids[len(input_ids):]
                        for input_ids, output_ids in zip(model_inputs["input_ids"], generated_ids)
                    ]

                    responses = self.tokenizer.batch_decode(cleaned_generated_ids, skip_special_tokens=True)
                    print(f"Responses: {responses}")
                    all_responses.extend(responses)

                return [all_responses, batch_size]
            except:
                batch_size = max(batch_size - 10, 1)
                if batch_size == 1:
                    repeat_batch_size_1 += 1
                if repeat_batch_size_1 == 5:
                    return [[], 1]
                cuda.empty_cache()
                print(f"Reducing batch size to {batch_size}")

    def encode(
        self,
        texts: str | list[str],
        embed_model_option: EmbeddingModelOption = EmbeddingModelOption(),
    ) -> ndarray:
        """Embed texts."""
        raise NotImplementedError("Qwen does not support embedding texts.")
