class ChatInterface:
    def __init__(self, llm_conductor):
        """
        Initializes the Chat Interface with access to the LLM Conductor.
        """
        self.llm_conductor = llm_conductor

    def receive_user_input(self, user_input: str) -> str:
        """
        Accepts user prompt and forwards it to the LLM conductor for processing.
        """
        response = self.llm_conductor.process_input(user_input.message)
        return response
