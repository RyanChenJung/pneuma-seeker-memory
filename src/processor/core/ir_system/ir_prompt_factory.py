class IRPromptFactory:
    def get_new_retrieve_prompt(self, requirements: str):
        return f"""Given these requirements: `{requirements}`, please craft a prompt to be given to information retrieval systems."""

    def get_refine_retrieval_prompt(self, prev_prompt: str, feedback: str):
        return f"""This is the previous prompt given to some information retrieval systems: `{prev_prompt}`, which is imperfect. This is the user feedback: `{feedback}`. Please adjust the prompt by incorporating the feedback to increase the change of getting more relevant results. Answer directly."""

    def get_retriever_classification_prompt(self, prompt: str, retriever_name: str, retriever_desc: str):
        return f"""Given this prompt: `{prompt}`, does the retriever `{retriever_name}` with the following description: `{retriever_desc}` relevant for answering the prompt? Begin your answer with yes/no, followed by brief reasoning."""