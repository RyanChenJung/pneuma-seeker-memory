import json

from pandas import DataFrame

from processor.core.ir_system.ir_data_model import (
    AbstractDocument,
    RetrieverType,
    convert_multi_retriever_results_to_str,
)


class MEPromptFactory:
    def get_planning_prompt(
        self,
        target_schemas: dict[str, DataFrame],
        column_descriptions: dict[str, dict[str, str]],
        sqls: list[str],
        tool_description: str,
        operation_description: str,
    ) -> str:
        return f"""You are a smart data scientist planning to materialize a set of table schemas that we refer to as Target Schemas:
```{json.dumps({k: list(df.columns) for k, df in target_schemas.items()}, indent=2)}```

This is the descriptions of the columns in Target Schemas:
```{column_descriptions}```

Also, just for reference (you will not need to execute this), these are the SQL queries that will be executed sequentially over the final target tables, which are materialized Target Schemas (observe the expected value format in the queries):
```{sqls}```

Again, your goal is to actually materialize the Target Schemas by manipulating tables/textual information in our database (retrieved from the Document Retriever tool).
You can select, integrate (join, union), transform values of, etc. these retrieved tables using the available tools and operations.

Available Tools:
```{tool_description}```

Available Operations:
```{operation_description}```

IMPORTANT: There are no other tools and operations, so use ONLY the above tools and operations."""

    def get_context_prompt(
        self,
        retrieved_documents: dict[RetrieverType, list[AbstractDocument]],
        intermediate_tables: dict[str, DataFrame],
        recent_actions: list[str],
        num_iterations: int,
    ) -> str:
        return f"""So far, we have reacted {num_iterations} times to the instructions. Below is our progress:

- Current intermediate tables (what we have formed so far, again we want to make sure to finally materialize Target Schemas into this list): ```{list(intermediate_tables.keys())}```

- Most recently taken actions: ```{recent_actions}```

- The documents we previously retrieved (tables and/or textual information): ```{convert_multi_retriever_results_to_str(retrieved_documents)}```

IMPORTANT: Before retrieving new documents, check if existing documents above contain the information we need. Only retrieve new documents if the current ones do not have what we are looking for.

Plan our next step using this format:
{{
  "step_type": "operation" | "tool" | "internal_reasoning",
  "message": null (if step_type is "operation" or "tool") | <"Reflect out loud (for ourselves only)">
  "name": null (if step_type is "internal_reasoning") | "Document Retriever" | "Python Executor" | "SQL Executor" | "Standard Inner Join" | "Union",
  "args": null (if step_type is "internal_reasoning") | {{"The argument to the function or tool that we call"}}
  "assign_to": null (if step_type is "internal_reasoning") | "result_table_id"  # Must match one of the target schema IDs if this is a final result (i.e., correspond to a target schema directly)
}}"""
