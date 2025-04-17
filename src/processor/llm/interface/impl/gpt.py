import os
from openai import OpenAI
from processor.utils.llm_option import LLMOption
from processor.utils.message import Message
from processor.llm.interface.model import AbstractModel
from dotenv import load_dotenv

class GPT(AbstractModel):
    def __init__(self, model_name: str = "gpt-4o-mini"):
        load_dotenv()
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model_name = model_name

    def load_model(self):
        # OpenAI API does not require model loading
        pass

    def load_tokenizer(self):
        # Tokenizer is handled internally by the API
        pass

    def chat(self, messages: list[Message], llm_option: LLMOption = LLMOption()) -> str:
        response = self.client.chat.completions.create(
            messages=messages,
            model=self.model_name,
            seed=42,
            top_p=llm_option.top_p,
            temperature=llm_option.temperature,
            max_completion_tokens=llm_option.max_new_tokens,
        )
        return response.choices[0].message.content
