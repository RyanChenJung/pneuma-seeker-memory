class IRPromptFactory:
    def get_retriever_classification_prompt(self, prompt: str, retriever_name: str, retriever_desc: str):
        return f"""Given this prompt: `{prompt}`, does the retriever `{retriever_name}` with the following description: `{retriever_desc}` relevant for answering the prompt? Begin your answer with yes/no."""