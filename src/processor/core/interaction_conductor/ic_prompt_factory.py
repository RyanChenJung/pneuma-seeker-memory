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
        return f"""Given this prompt: `{prompt}`, do any of these documents retrieved from an IR system not make sense: `{results}`? Output a JSON object directly (without any extra explanations) of the following format:
```
"irrelevant_doc_ids": [list of irrelevant document IDs if any, else empty list.]
"feedback": "Explain what is wrong with the irrelevant documents if any, else empty string."
```"""

    def get_materializer_prompt():
        """
        Returns prompt for the materializer engine.
        """
