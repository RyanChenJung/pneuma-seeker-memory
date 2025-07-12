class IRPromptFactory:
    def get_new_retrieve_prompt(self, requirements: str):
        return f"""Given this requirements: ``, please create a prompt to be given to an IR system."""

    def get_refine_retrieval_prompt(self, prev_prompt: str, feedback: str):
        return f"""This is the previous prompt: `{prev_prompt}`, which is imperfect. The feedback is this: `{feedback}`. Please re-create the prompt by incorporating the feedback."""

    def get_retriever_classification_prompt(self, prompt: str, retriever_name: str, retriever_desc: str):
        return f"""Given this prompt: `{prompt}`, does the retriever `{retriever_name}` with the following description: `{retriever_desc}` relevant for answering the prompt? Begin your answer with yes/no."""