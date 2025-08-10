import json

from pandas import DataFrame

from pneuma_seeker.core.ir_system.ir_data_model import (
    AbstractDocument,
    RetrieverType,
    convert_multi_retriever_results_to_str,
)


class PromptFactory:
    def get_planning_prompt_brief(
    self,
    target_schemas: dict[str, DataFrame],
    column_descriptions: dict[str, dict[str, str]],
    sqls: list[str],
    operation_description: str,
) -> str:
        return f"""You are the Materializer Engine (ME).  
Your goal is to fill all rows for the target schemas below using retrieved tables and allowed operations.

TARGET SCHEMAS:
{json.dumps({k: list(df.columns) for k, df in target_schemas.items()}, indent=2)}

COLUMN DESCRIPTIONS:
{column_descriptions}

REFERENCE SQLs (for value format guidance only):
{sqls}

AVAILABLE OPERATIONS:
{operation_description}

Rules:
- Only use listed operations — no custom methods.
- Use retrieved tables before calling Document Retriever again (retriever resets previously retrieved data).
- Assign results to the correct target schema IDs.
- Always check column names match exactly (case-sensitive) with the schema definition.
- Handle value format conversions if needed (e.g., YES/NO instead of 0/1, YYYY-MM-DD instead of Month Day, Year).
- Avoid producing empty tables — if result is empty, revise your approach.

Each iteration, output exactly one JSON object:
{{
  "step_type": "internal_reasoning" | "operation",
  "message": "...",        # if internal_reasoning
  "name": "<operation>",   # if operation
  "args": {{...}},         # args for the operation
  "assign_to": "<target_schema_id or intermediate_table_id>"
}}
"""

    def get_planning_prompt(
        self,
        target_schemas: dict[str, DataFrame],
        column_descriptions: dict[str, dict[str, str]],
        sqls: list[str],
        operation_description: str,
    ) -> str:
        return f"""You are a smart data scientist planning to materialize a set of table schemas that we refer to as Target Schemas:
```{json.dumps({k: list(df.columns) for k, df in target_schemas.items()}, indent=2)}```

This is the descriptions of the columns in Target Schemas:
```{column_descriptions}```

Also, just for reference (you will not need to execute this), these are the SQL queries that will be executed sequentially over the final target tables, which are materialized Target Schemas (observe the expected value format in the queries):
```{sqls}```

Again, your goal is to actually materialize the Target Schemas by manipulating tables/textual information in our database (retrieved from the Document Retriever).
You can select, integrate (join, union), transform values of, etc. these retrieved tables using the available operations.

Available Operations:
```{operation_description}```

IMPORTANT: There are no other operations, so use ONLY choose among the above operations."""
    
    def get_fix_python_prompt(self, code: str, available_tables: dict[str, DataFrame], error: Exception):
        return f"""You are an expert in Python programming.

This code:
```{code}```

It manipulates tables from the following list (note that table IDs may look like path):
```{self.__format_available_tables(available_tables)}```

Resulting in this error: {error}.

Please provide direct feedback about what is wrong with the code, so the implementor can fix it.
"""
    
    def __format_available_tables(self, tables: dict[str, DataFrame]):
        tables_repr = ""
        for table_id, table in tables.items():
            tables_repr += (
                f"\n- Table {table_id}:\ncol: {" | ".join(list(table.columns))}"
            )
            if len(table) > 0:
                # Sample 5 rows to represent the table
                sample_rows = table.sample(min(5, len(table)), random_state=42)
                sample_row_idx = 1
                for _, data in sample_rows.iterrows():
                    str_data = [str(i) for i in data]
                    tables_repr += (
                        f"\nsample row {sample_row_idx}: {" | ".join(str_data)}"
                    )
                    sample_row_idx += 1
        return tables_repr.strip()

    def get_context_prompt_brief(
    self,
    retrieved_documents: dict[RetrieverType, list[AbstractDocument]],
    intermediate_tables: dict[str, DataFrame],
    recent_actions: list[str],
    num_iterations: int,
    user_side_note: str,
) -> str:
        return f"""This is iteration {num_iterations} of materializing the Target Schemas.

CURRENT PROGRESS:
- Intermediate tables so far: {list(intermediate_tables.keys())}
- Recent actions: {recent_actions}
- Retrieved documents (tables/text): {convert_multi_retriever_results_to_str(retrieved_documents)}
- User note: {user_side_note}

RULES:
1. Before calling Document Retriever, check if current retrieved docs already contain the needed info.
2. If user note requires filtering, formatting, or transformation → use Python Executor, NOT Table Select.
3. Always match target schema column names exactly (case-sensitive).
4. Never use `pd.read_csv` — use `tables["<ID>"]` (dict[str, pd.DataFrame]) to access data.
5. Assign final materialized tables to the correct target schema IDs.
6. If you retrieve tables and suspect there are other related tables (that were not retrieved) with similar naming patterns (e.g., topic_2019, topic_2020, etc.), but the user has not specified which one(s) they need, use the table_enumerator tool to list all matching table IDs for a better understanding.

Respond with exactly ONE JSON object:

Internal reasoning:
{{
  "step_type": "internal_reasoning",
  "message": "<your private reasoning>"
}}

Operation:
{{
  "step_type": "operation",
  "name": "Document Retriever" | "Table Enumerator" | "Table Select" | "Python Executor" | "SQL Executor" | "Standard Inner Join" | "Union",
  "args": {{...}},
  "assign_to": "<target_schema_id_or_intermediate_id>"
}}"""

    def get_context_prompt(
        self,
        retrieved_documents: dict[RetrieverType, list[AbstractDocument]],
        intermediate_tables: dict[str, DataFrame],
        recent_actions: list[str],
        num_iterations: int,
        user_side_note: str,
    ) -> str:
        return f"""So far, we have reacted {num_iterations} times to the instructions. Below is our progress:

- Current intermediate tables (what we have formed so far, again we want to make sure to finally materialize Target Schemas into this list): ```{list(intermediate_tables.keys())}```

- Most recently taken actions: ```{recent_actions}```

- The documents we previously retrieved (tables and/or textual information): ```{convert_multi_retriever_results_to_str(retrieved_documents)}```

IMPORTANT:
- Before retrieving new documents, check if existing documents above contain the information we need. Only retrieve new documents if the current ones do not have what we are looking for.
- Carefully observe user's note: `{user_side_note}` It may indicate filtering condition (e.g., only get between year x and y), column formatting, etc. If this is the case, you CANNOT use Table Select; use Python code to implement the specified conditions!

Plan our next step using either of these formats (depending on the step_type):
{{
  "step_type": "internal_reasoning",
  "message": <"Reflect out loud (for ourselves only)">
}}

{{
  "step_type": "operation",
  "name": "Document Retriever" | "Table Select",
  "args": {{"The argument to the operation that we call"}}
}}

{{
  "step_type": "operation",
  "name": "Python Executor"| "SQL Executor" | "Standard Inner Join" | "Union",
  "args": {{"The argument to the operation that we call"}}
  "assign_to": <"result_table_id">  # Must match one of the target schema IDs if this is a final result (i.e., correspond to a target schema directly); don't set the value to literal "result_table_id", adjust with the appropriate id.
}}

VERY IMPORTANT: If you produce a Python code, NEVER use pd.read_csv. Use tables["<ID>"] in your code (tables is a dict[str, pd.DataFrame] variable), then you will get it directly in a Pandas DataFrame format."""
