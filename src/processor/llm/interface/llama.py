from torch import bfloat16
from transformers import pipeline

from processor.llm.interface.model_interface import ModelInterface


class Llama(ModelInterface):
    def __init__(self, ckp: str):
        self.ckp = ckp
        self.model = None
        self.tokenizer = None

    def load_model(self):
        self.model = pipeline(
            "text-generation",
            model=self.ckp,
            torch_dtype=bfloat16,
            device_map="auto",
        )

    def load_tokenizer(self):
        pass

    def chat(self, messages, max_new_tokens=256):
        if self.model is None:
            self.load_model()

        outputs = self.model(
            messages,
            max_new_tokens=max_new_tokens,
            do_sample=False,
        )
        return outputs[0]["generated_text"][-1]
