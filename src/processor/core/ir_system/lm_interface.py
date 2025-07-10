from processor.ir_system.ir_state import IRState
from processor.ir_system.prompts.ir_prompt_factory import IRPromptFactory
from processor.model.interface.abstract_model import AbstractModel


class LMInterface:
    def __init__(self, llm: AbstractModel):
        self.state = IRState()
        self.prompt_factory = IRPromptFactory()
        self.llm = llm
    
    def load_llm(self):
        self.llm.load_model()
        self.llm.load_tokenizer()

    def retrieve(self, prompt: str):
        """
        Retrieves documents from the retrievers in an intelligent manner.

        - prompt (str): First the initial query, subsequently feedback to improve
        the results by adjusting the initial query.
        """
        self.load_llm()
        # Step 1: Consider which retrievers to use.
        pass
        
        # Step 2: Call the retrievers, along with the corresponding prompt
        pass
