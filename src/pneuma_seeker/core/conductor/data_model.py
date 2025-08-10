class HumanConductorInteraction:
    """
    Keeps track of pairs of human input-Conductor (final) response for the input
    """

    def __init__(self, human_input: str, llm_response: str) -> None:
        self.human_input = human_input
        self.llm_response = llm_response

    def __str__(self) -> str:
        return f"""{{"human input": {self.human_input}, "llm response": {self.llm_response}}}"""
