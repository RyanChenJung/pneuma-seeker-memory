from torch import bfloat16
from transformers import pipeline

from processor.llm.interface.model import AbstractModel


class Llama(AbstractModel):
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model = None

    def load_model(self):
        self.model = pipeline(
            "text-generation",
            model=self.model_name,
            torch_dtype=bfloat16,
            device_map="auto",
        )

    def load_tokenizer(self):
        # This model uses pipeline interface; no need to separately handle tokenizer
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
