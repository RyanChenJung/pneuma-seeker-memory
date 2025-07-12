class ICPromptEngineer:
    def get_general_prompt():
        """
        Returns prompt for general chat.
        """

    def get_ir_prompt():
        """
        Returns prompt for the IR system.
        """

    def get_ir_sanity_check_prompt(self, prompt: str, results: str):
        return f"Given this prompt: `{prompt}`, does these results from an IR system make sense: `{results}`? If not, provide some feedback. Begin your answer with yes/no, followed by the feedback if the result doesn't make sense."

    def get_materializer_prompt():
        """
        Returns prompt for the materializer engine.
        """
