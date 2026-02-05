class UserConductorInteraction:
    """
    Keeps track of pairs of user input-Conductor (final) response for the input
    """

    def __init__(self, user_input: str, llm_response: str) -> None:
        self.user_input = user_input
        self.llm_response = llm_response

    def __str__(self) -> str:
        return f"""{{"user input": {self.user_input}, "llm response": {self.llm_response}}}"""
