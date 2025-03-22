from ast import literal_eval
from processor.src.processor.llm.interface.model_interface import ModelInterface, get_model
from processor.src.processor.llm.prompts import schema_generator_system_prompt

class SchemaGenerator:
    def __init__(self, ckp: str):
        model_interface = get_model(ckp)
        self.model: ModelInterface = model_interface(ckp)
        self.model.load_model()
        self.model.load_tokenizer()

    def get_target_schema(self, question: str) -> list[str]:
        messages = [
            {"role": "system", "content": schema_generator_system_prompt},
            {"role": "user", "content": f"Question: {question}"}
        ]
        target_schema = self.model.chat(messages)
        try:
            target_schema = literal_eval(target_schema)
            return target_schema
        except:
            return []
