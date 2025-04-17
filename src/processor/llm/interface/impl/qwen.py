from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed

from processor.llm.interface.model import AbstractModel
from processor.utils.llm_option import LLMOption


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

    def chat(self, messages, llm_option: LLMOption = LLMOption()):
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
            max_new_tokens=512,
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
        return response
