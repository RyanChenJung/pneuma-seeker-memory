import json

from pandas import DataFrame

from pneuma_seeker.core.ir_system.data_model import (
    AbstractDocument,
    RetrieverType,
    convert_multi_retriever_results_to_str,
    convert_retrieval_results_to_str,
)


class MaterializerPromptFactory:
    def get_planning_prompt(
    self,
    T: dict[str, DataFrame],
    column_descriptions: dict[str, dict[str, str]],
    sqls: list[str],
    operation_description: str,
) -> str:
        return f"""
You are the Materializer. Your task is to fill all rows for the target schemas using:
1. Retrieved internal data
2. User-uploaded external tables (if any)
3. Allowed operations described below

Treat external tables just like internal data, except it is fixed and will never be replaced by calling Document Retriever again.

TARGET SCHEMAS:
{json.dumps({k: list(df.columns) for k, df in T.items()}, indent=2)}

COLUMN DESCRIPTIONS:
{column_descriptions}

REFERENCE SQLs (for value format guidance only — not to execute directly):
{sqls}

AVAILABLE OPERATIONS:
{operation_description}

CORE RULES:
1. Only use listed operations — no custom methods.
2. Use external tables if available and internal data; call Document Retriever to retrieve or re-retrieve internal data (if necessary).
3. Internal data is reset each time Document Retriever is used; external tables persist.
4. Use `tables["<ID>"]` to access both internal and external tables. Never use pd.read_csv.
5. Always assign results to the correct target schema IDs, matching column names **exactly (case-sensitive)**.
6. Perform value format conversions if needed (e.g., YES/NO instead of 0/1, YYYY-MM-DD instead of Month Day, Year).
7. Note: You may already see some internal data provided at the start (pre-fetched by the caller). Treat it the same as if you had retrieved it yourself — use it if useful, or call Document Retriever again if needed. This pre-fetched data is not guaranteed to be complete or sufficient.

COLUMN HANDLING:
- (semantically_derived) and user notes are hints, not guarantees.
- If reliable data exists for a column (tagged or untagged), fill it normally using Python Executor or SQL Executor — no semantic generation needed.
- If no reliable data exists to fill a column, use the Semantic Column Generator as a fallback — whether or not the column is tagged.

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
    intermediate_tables: list[AbstractDocument],
    recent_actions: list[str],
    num_iterations: int,
    user_side_note: str,
    user_provided_external_data: list[AbstractDocument],
) -> str:
        return f"""
This is iteration {num_iterations} of materializing the Target Schemas.

CURRENT PROGRESS:
- Intermediate tables so far: {convert_retrieval_results_to_str(intermediate_tables)}
- Recent actions: {recent_actions}
- Retrieved internal data: {convert_multi_retriever_results_to_str(retrieved_documents)}
- User-uploaded external tables: {convert_retrieval_results_to_str(user_provided_external_data)}
- User note: {user_side_note}

CORE RULES:
1. Use external tables if available and internal data; call Document Retriever to retrieve or re-retrieve internal data (if necessary).
2. Internal data is reset each time Document Retriever is used; external tables persist.
3. Use `tables["<ID>"]` to access both internal and external tables. Never use pd.read_csv.
4. Always match target schema column names exactly (case-sensitive).
5. Assign completed tables only to their correct target schema IDs.
6. Note: You may already see some internal data provided at the start (pre-fetched by the caller). Treat it the same as if you had retrieved it yourself — use it if useful, or call Document Retriever again if needed. This pre-fetched data is not guaranteed to be complete or sufficient.

COLUMN HANDLING:
- Treat (semantically_derived) and user notes as hints only.
- If reliable data exists, compute normally using Python Executor or SQL Executor.
- Use Semantic Column Generator only when no reliable direct computation is available.

TOOL USAGE:
- If you retrieve tables from Document Retriever and suspect other related ones (e.g., topic_2019, topic_2020) might exist but are not yet retrieved, use Table Enumerator to list all matching table IDs.
- Use Semantic Column Generator only when no reliable direct computation is available.

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
