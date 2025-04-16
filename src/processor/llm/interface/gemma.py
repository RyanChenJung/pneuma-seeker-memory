from processor.llm.interface.model_interface import ModelProtocol
from torch import bfloat16
from transformers import AutoTokenizer, Gemma3ForCausalLM


class Gemma(ModelProtocol):
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model = None
        self.tokenizer = None

    def load_model(self):
        self.model = Gemma3ForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype=bfloat16,
        )
        self.model.to("cuda")

    def load_tokenizer(self):
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)

    def chat(self, messages):
        if self.model is None:
            self.load_model()
        if self.tokenizer is None:
            self.load_tokenizer()

        inputs = self.tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to(self.model.device)
        input_len = inputs["input_ids"].shape[-1]
        generation = self.model.generate(**inputs, max_new_tokens=100, do_sample=False)
        generation = generation[0][input_len:]

        decoded = self.tokenizer.decode(generation, skip_special_tokens=True)
        return decoded
