import json

from pandas import DataFrame

from pneuma_seeker.core.ir_system.data_model import (
    AbstractDocument,
    convert_retrieval_results_to_str,
)
from pneuma_seeker.core.toolkit.operation_description import (
    get_operation_description,
)
from pneuma_seeker.shared.config import Config


class MaterializerPromptFactory:
    """Generates prompts for the Materializer LLM agent."""

    def __init__(self, config: Config) -> None:
        self.config = config

    def get_planning_prompt(
        self,
        T: dict[str, DataFrame],
        column_descriptions: dict[str, dict[str, str]],
        S: str,
    ) -> str:
        """Generates the initial planning prompt for the Materializer."""
        return f"""
You are the Materializer. Your task is to fill all rows for the target tables using:
1. Retrieved internal tables
2. User-uploaded external tables (if any)
3. Allowed operations described below

Treat external tables just like internal tables, except it is fixed and will never be replaced by calling pneuma_retriever again.

TARGET TABLES:
{json.dumps({k: list(df.columns) for k, df in T.items()}, indent=2)}

COLUMN DESCRIPTIONS:
{column_descriptions}

REFERENCE SCRIPT (for value format guidance only — not to execute directly):
{S}

AVAILABLE OPERATIONS:
{get_operation_description(self.config.ENABLE_WEB_SEARCH, self.config.ENABLE_WEB_CRAWL)}

CORE RULES:
1. Only use listed operations — no custom methods.
2. Use external tables if available and internal tables; call pneuma_retriever to retrieve or re-retrieve internal tables (if necessary).
3. Internal tables are reset each time pneuma_retriever is used; external tables persist.
4. Use `tables["<ID>"]` to access both internal and external tables. Never use pd.read_csv.
5. Always assign results to the correct target table IDs, matching column names **exactly (case-sensitive)**.
6. Perform value format conversions if needed (e.g., YES/NO instead of 0/1, YYYY-MM-DD instead of Month Day, Year).
7. Note:
- You may already see some internal tables provided at the start (pre-fetched by the caller). Treat it the same as if you had retrieved it yourself — use it if useful, or call pneuma_retriever again if needed. These pre-fetched tables are not guaranteed to be complete or sufficient.
{f"- You may already see a web search result provided at the start (pre-fetched by the caller). Treat it the same as if you had performed the web search yourself — use it if useful. This pre-fetched web search result is not guaranteed to be complete or sufficient.\n" if self.config.ENABLE_WEB_SEARCH else ""}
{f"- You may already see a web crawl result provided at the start (pre-fetched by the caller). Treat it the same as if you had performed the web crawl yourself — use it if useful. This pre-fetched web crawl result is not guaranteed to be complete or sufficient.\n" if self.config.ENABLE_WEB_CRAWL else ""}

COLUMN HANDLING:
- (semantically_derived) and user notes are hints, not guarantees.
- If reliable data exists for a column (tagged or untagged), fill it normally using python_executor or sql_executor — no semantic generation needed.
- If no reliable data exists to fill a column, use the semantic_column_generator as a fallback — whether or not the column is tagged.

OUTPUT FORMAT:
Produce exactly ONE JSON object:
{{
    "action_type": "internal_reasoning" | "operation",
    "message": "...",        # if action_type == internal_reasoning
    "name": "<operation>",   # if action_type == operation
    "args": {{...}},         # arguments for the operation
    "assign_to": "<target_table_id or intermediate_table_id>"
}}
""".strip()

    def get_context_prompt(
        self,
        retrieved_tables: list[AbstractDocument],
        intermediate_tables: list[AbstractDocument],
        recent_actions: list[str],
        num_iterations: int,
        user_side_note: str,
        user_uploaded_external_tables: list[AbstractDocument],
        web_search_result: AbstractDocument | None,
        web_crawl_result: AbstractDocument | None,
    ) -> str:
        """Generates the context prompt for each iteration of the Materializer."""
        return f"""
This is iteration {num_iterations} of materializing the target tables.

CURRENT PROGRESS:
- Intermediate tables so far: {convert_retrieval_results_to_str(intermediate_tables)}
- Recent actions: {recent_actions}
- Retrieved internal tables: {convert_retrieval_results_to_str(retrieved_tables)}
- User-uploaded external tables: {convert_retrieval_results_to_str(user_uploaded_external_tables)}
- User note: {user_side_note}
{f"- Web search result (if any): {web_search_result}\n" if self.config.ENABLE_WEB_SEARCH and web_search_result else ""}
{f"- Web crawl result (if any): {web_crawl_result}\n" if self.config.ENABLE_WEB_CRAWL and web_crawl_result else ""}
CORE RULES:
1. Use external tables if available and internal tables; call pneuma_retriever to retrieve or re-retrieve internal tables (if necessary).
2. Internal tables are reset each time pneuma_retriever is used; external tables persist.
3. Use `tables["<ID>"]` to access both internal and external tables. Never use pd.read_csv.
4. Always match target table column names exactly (case-sensitive).
5. Assign completed tables only to their correct target table IDs.
6. Note:
- You may already see some internal tables provided at the start (pre-fetched by the caller). Treat it the same as if you had retrieved it yourself — use it if useful, or call pneuma_retriever again if needed. These pre-fetched tables are not guaranteed to be complete or sufficient.
{f"- You may already see a web search result provided at the start (pre-fetched by the caller). Treat it the same as if you had performed the web search yourself — use it if useful. This pre-fetched web search result is not guaranteed to be complete or sufficient.\n" if self.config.ENABLE_WEB_SEARCH else ""}
{f"- You may already see a web crawl result provided at the start (pre-fetched by the caller). Treat it the same as if you had performed the web crawl yourself — use it if useful. This pre-fetched web crawl result is not guaranteed to be complete or sufficient.\n" if self.config.ENABLE_WEB_CRAWL else ""}

COLUMN HANDLING:
- Treat (semantically_derived) and user notes as hints only.
- If reliable data exists, compute normally using python_executor or sql_executor.
- Use semantic_column_generator only when no reliable direct computation is available.

TOOL USAGE:
- If you retrieve tables from pneuma_retriever and suspect other related ones (e.g., topic_2019, topic_2020) might exist but are not yet retrieved, use table_enumerator to list all matching table IDs.
- Use semantic_column_generator only when no reliable direct computation is available.

OUTPUT FORMAT:
Return exactly ONE JSON object per iteration:
{{
  "action_type": "internal_reasoning",
  "message": "<your private reasoning>"
}}

OR

{{
  "action_type": "operation",
  "name": "pneuma_retriever" | "table_enumerator" | "table_select",
  "args": {{...}},
}}

OR

{{
  "action_type": "operation",
  "name": "python_executor" | "sql_executor",
  "args": {{...}},
  "assign_to": "<target_table_id_or_intermediate_id>"
}}
""".strip()

    def get_fix_python_prompt(
        self, code: str, available_tables: dict[str, DataFrame], error: Exception
    ):
        """Generates a prompt to fix Python code that resulted in an error."""
        return f"""You are an expert in Python programming.

This code:
```{code}```

It manipulates tables from the following list (note that table IDs may look like path):
```{self.__format_available_tables(available_tables)}```

Resulting in this error: {error}.

Please provide direct feedback about what is wrong with the code, so the implementor can fix it.
"""

    def __format_available_tables(self, tables: dict[str, DataFrame]):
        """Formats available tables for inclusion in prompts."""
        tables_repr = ""
        for table_id, table in tables.items():
            tables_repr += (
                f"\n- Table {table_id}:\ncol: {' | '.join(list(table.columns))}"
            )
            if len(table) > 0:
                # Sample 5 rows to represent the table
                sample_rows = table.sample(min(5, len(table)), random_state=42)
                sample_row_idx = 1
                for _, data in sample_rows.iterrows():
                    str_data = [str(i) for i in data]
                    tables_repr += (
                        f"\nsample row {sample_row_idx}: {' | '.join(str_data)}"
                    )
                    sample_row_idx += 1
        return tables_repr.strip()
