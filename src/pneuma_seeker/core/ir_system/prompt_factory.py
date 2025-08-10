class PromptFactory:
    def get_new_retrieve_prompt(self, requirements: str):
        return f"""Given these requirements: `{requirements}`, please craft a prompt to be given to information retrieval systems."""

    def get_refine_retrieval_prompt(self, prev_prompt: str, prev_docs_repr: str, feedback: str):
        return f"""This is the previous prompt given to an information retrieval system: `{prev_prompt}`, which is imperfect, as it results in the following documents being retrieved: `{prev_docs_repr}`. This is the user feedback: `{feedback}`. Please adjust the prompt by incorporating the feedback to increase the chance of getting more relevant results. Answer directly."""

    def get_ir_sanity_check_prompt(self, prompt: str, results: str):
        return f"""You are checking if any documents retrieved from an IR (information retrieval) system are clearly irrelevant to the prompt.

Prompt:
`{prompt}`

Retrieved document sample contents:
`{results}`

IMPORTANT:
- The documents may contain TABLES, but only SAMPLE ROWS are shown.
- These rows are not exhaustive. Just because a specific value (e.g., date) is not shown does NOT mean it doesn’t exist in the full document.
- Therefore, unless a document is **clearly** irrelevant based on title, schema, or visible values, **assume it could still be relevant**.

Your task:
Return a JSON object, **with no extra explanation**, in this format:
```
- "irrelevant_doc_ids": [list of clearly irrelevant document IDs if any, else empty list],
- "feedback": "Explain why these documents are irrelevant, if any; otherwise, leave this as an empty string."
```

Be conservative in marking documents irrelevant. If there's uncertainty, do not flag the document."""



#     def get_ir_sanity_check_prompt(self, prompt: str, results: str):
#         return f"""Given this prompt: `{prompt}`, do any of these documents retrieved from an IR system not make sense: `{results}`? Please note that if you observe tables, you ONLY see their sample rows, and not the whole data. Thus, it is possible that a certain value (e.g., date) exists in a table but not included in its sample rows.

# Output a JSON object directly (without any extra explanations) of the following format:
# ```
# "irrelevant_doc_ids": [list of irrelevant document IDs if any, else empty list.]
# "feedback": "Explain what is wrong with the irrelevant documents if any, else empty string."
# ```"""

    def get_retriever_classification_prompt(
        self, prompt: str, retriever_name: str, retriever_desc: str
    ):
        return f"""Given this prompt: `{prompt}`, does the retriever `{retriever_name}` with the following description: `{retriever_desc}` relevant for answering the prompt? Begin your answer with yes/no, followed by brief reasoning."""
