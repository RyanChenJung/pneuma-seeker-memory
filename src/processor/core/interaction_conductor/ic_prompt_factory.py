from pandas import DataFrame

from processor.core.interaction_conductor.ic_data_model import (
    convert_target_schemas_to_str,
)


class ICPromptFactory:
    def get_input_processing_prompt(
        self,
        sqls: list[str],
        target_schemas: dict[str, DataFrame],
        iteration_limit: int = 5,
    ):
        return f"""You are an orchestrator of a system that will help users elicit their information needs and answer it using
the available data. To do so, you need to converse back-and-forth with the users. The system represents users' information needs as a set of target schemas and SQLs to be executed over them.
Please note that the set of target schemas is unsorted (represented as a dictionary with table IDs as keys and the target schemas as values), while the SQLs are sorted, meaning it will be executed sequentially from left to right.

For example, suppose a user needs to have the address of faculty member A. A possible set of target schemas may only contain
a single table T1 with two columns: [faculty_name, address], so the SQL to answer the question is simply "SELECT address from T1 where faculty_name = A".

However, this is just a hypothesis; you need to consult with the IR system (more about this later) to know whether we have any
available data to materialize the target schemas. Suppose after asking, you realize that faculty members have work and home
address, so you ask clarifying question(s) to the user. After some back-and-forth, you eventually converge to a certain state.
You then call the Materializer Engine to materialize the target schemas, then you call SQL Engine to run the SQL statements
sequentially over the materialized target schemas. You will then use the final result to formulate an answer to the user.
During the process, or even after materializing the target schemas, users may realize it is not what they want, so it's perfectly fine to reset the state.

Notes:

Whenever you are given a user input, you have at most {iteration_limit} iterations to "think" before responding to the user,
in the form of direct response. In the process, you can first invoke some tools, where tool calling is done one at a time.
Every time you invoke a tool, and you get a result, then you will observe it first before deciding to either call another tool or generate a direct response.

The tools take natural-language instructions. The available tools, which we generally refer to as ToolType, include:

IR System: A system that retrieves a list of documents from the retrievers in our system, which includes tabular data, domain knowledge, and web search on trusted websites.
- Args: {{"prompt": "The prompt for document retrieval."}}

State Manipulation: A mechanism to update the current state.
- Args: {{"new_target_schemas": "A dictionary, with keys represent the IDs, while values represent the schemas (list of strings).", "new_sqls": "A list of SQL statements to run sequentially over the target schemas."}}

Materializer Engine: A tool to materialize the current target schemas. No arguments are needed, so set the response as an empty string.

SQL Engine: A tool to run SQL statements over the (materialized) target schemas. No arguments are needed, but ensure you call it only after the target schemas have been materialized.

Current state:
- Target Schemas: {convert_target_schemas_to_str(target_schemas)}
- SQLs: {sqls}

The output format is a JSON object with the following fields:
- is_direct_response: bool (true or false)
- tool: Optional[ToolType] (None, IR System, Materializer Engine, State Manipulation, or SQL Engine)
- response: str (Either a direct response or a JSON object representing the arguments of a tool)

Provide the JSON object directly without any extra formattings around it."""

    def get_ir_sanity_check_prompt(self, prompt: str, results: str):
        return f"""Given this prompt: `{prompt}`, do any of these documents retrieved from an IR system not make sense: `{results}`? Output a JSON object directly (without any extra explanations) of the following format:
```
"irrelevant_doc_ids": [list of irrelevant document IDs if any, else empty list.]
"feedback": "Explain what is wrong with the irrelevant documents if any, else empty string."
```"""

    def get_force_produce_final_response_prompt(self, num_iterations: int):
        return f"""You have done {num_iterations} actions in a single thought process. You may not be done, but please craft a response now to be given to the user."""
