import json

from pandas import DataFrame

from pneuma_seeker.core.ir_system.data_model import (
    AbstractDocument,
    RetrieverType,
    convert_multi_retriever_results_to_str,
)


class PromptFactory:
    def get_planning_prompt(
    self,
    target_schemas: dict[str, DataFrame],
    column_descriptions: dict[str, dict[str, str]],
    sqls: list[str],
    operation_description: str,
) -> str:
        return f"""
You are the Materializer. Your task is to fill all rows for the target schemas below using retrieved tables and allowed operations.

TARGET SCHEMAS:
{json.dumps({k: list(df.columns) for k, df in target_schemas.items()}, indent=2)}

COLUMN DESCRIPTIONS:
{column_descriptions}

REFERENCE SQLs (for value format guidance only — not to execute directly):
{sqls}

AVAILABLE OPERATIONS:
{operation_description}

CORE RULES:
1. Only use listed operations — no custom methods.
2. Prefer using already retrieved tables before calling Document Retriever again (retrieved data is reset each time Document Retriever is used).
3. Always assign results to the correct target schema IDs, matching column names **exactly (case-sensitive)**.
4. Perform value format conversions if needed (e.g., YES/NO instead of 0/1, YYYY-MM-DD instead of Month Day, Year).

COLUMN HANDLING:
- Column annotations like (semantically_derived) and user notes are **hints, not guarantees**.
- If reliable data exists for a column (tagged or untagged), compute it normally using Python Executor or SQL Executor — no semantic generation needed.
- If no reliable data exists to fill a column, use the Semantic Column Generator as a fallback — whether or not the column is tagged.
- If a user note suggests semantic computation, consider it as context — but still verify whether data is available before deciding.

OUTPUT FORMAT:
Produce exactly ONE JSON object:
{{
  "step_type": "internal_reasoning" | "operation",
  "message": "...",        # if step_type == internal_reasoning
  "name": "<operation>",   # if step_type == operation
  "args": {{...}},         # arguments for the operation
  "assign_to": "<target_schema_id or intermediate_table_id>"
}}
""".strip()
    
    def get_context_prompt(
    self,
    retrieved_documents: dict[RetrieverType, list[AbstractDocument]],
    intermediate_tables: dict[str, DataFrame],
    recent_actions: list[str],
    num_iterations: int,
    user_side_note: str,
) -> str:
        return f"""
This is iteration {num_iterations} of materializing the Target Schemas.

CURRENT PROGRESS:
- Intermediate tables so far: {list(intermediate_tables.keys())}
- Recent actions: {recent_actions}
- Retrieved documents (tables/text): {convert_multi_retriever_results_to_str(retrieved_documents)}
- User note: {user_side_note}

RULES:
CORE:
1. Use currently retrieved documents before calling Document Retriever again.
2. Always match target schema column names exactly (case-sensitive).
3. Assign completed tables only to their correct target schema IDs.

COLUMN HANDLING:
- Treat column annotations (e.g., (semantically_derived)) as **hints, not absolute truth**. 
- If data exists for a tagged column, compute normally using Python or SQL. 
- If no data exists for an untagged column, use the Semantic Column Generator as fallback.
- In other words: **don't let your user's mistakes block you — use whichever method best populates the column accurately.**

TOOL USAGE:
1. Never use `pd.read_csv` — use `tables["<ID>"]` (dict[str, pd.DataFrame]) to access retrieved data.
2. If you retrieve tables and suspect other related ones (e.g., topic_2019, topic_2020) might exist but are not yet retrieved, use Table Enumerator to list all matching table IDs.
3. Use Semantic Column Generator only when no reliable direct computation is available.

OUTPUT FORMAT:
Return exactly ONE JSON object per iteration:
{{
  "step_type": "internal_reasoning",
  "message": "<your private reasoning>"
}}

OR

{{
  "step_type": "operation",
  "name": "Document Retriever" | "Table Enumerator" | "Table Select",
  "args": {{...}},
}}

OR

{{
  "step_type": "operation",
  "name": "Python Executor" | "SQL Executor",
  "args": {{...}},
  "assign_to": "<target_schema_id_or_intermediate_id>"
}}
""".strip()

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
