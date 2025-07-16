from processor.core.interaction_conductor.llm_conductor import LLMConductor


class ChatInterface:
    def __init__(self):
        """
        Initializes the Chat Interface with access to the LLM Conductor.
        """
        self.llm_conductor = LLMConductor("../../model/qwen25-7b")

    def process_user_input(self, user_input: str) -> str:
        """
        Accepts user prompt and forwards it to the LLM conductor for processing.
        """
        response = self.llm_conductor.process_input(user_input)
        return response
