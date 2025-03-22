from transformers import AutoModelForCausalLM, AutoTokenizer
from processor.src.processor.llm.interface.model_interface import ModelInterface


class Qwen(ModelInterface):
    def __init__(self, ckp: str):
        self.ckp = ckp
        self.model = None
        self.tokenizer = None

    def load_model(self):
        self.model = AutoModelForCausalLM.from_pretrained(
            self.ckp, torch_dtype="auto", device_map="auto"
        )

    def load_tokenizer(self):
        self.tokenizer = AutoTokenizer.from_pretrained(self.ckp)

    def chat(self, messages):
        if self.model is None:
            self.load_model()
        if self.tokenizer is None:
            self.load_tokenizer()

        text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        model_inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)

        generated_ids = self.model.generate(
            **model_inputs,
            max_new_tokens=512,
            do_sample=False,
            temperature=None,
            top_p=None,
            top_k=None
        )
        generated_ids = [
            output_ids[len(input_ids) :]
            for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]

        response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[
            0
        ]
        return response
