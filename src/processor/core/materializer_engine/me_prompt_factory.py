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
    
    def get_planning_prompt_with_feedback(
        self,
        target_schemas: dict[str, DataFrame],
        column_descriptions: dict[str, dict[str, str]],
        sqls: list[str],
        operation_description: str,
        feedback: str,
    ) -> str:
        return f"""You are a smart data scientist who previously materialized a set of table schemas that we refer to as Target Schemas:
```{json.dumps({k: list(df.columns) for k, df in target_schemas.items()}, indent=2)}```

This is the descriptions of the columns in Target Schemas:
```{column_descriptions}```

You materialized the Target Schemas by manipulating tables/textual information in our database (retrieved from the Document Retriever).
You can select, integrate (join, union), transform values of, etc. these retrieved tables using the available operations.

The user just executed these SQL queries sequentially on your output (final target tables, i.e., materialized target schemas; observe the expected value format in the queries):
```{sqls}```

However, the user has some feedback regarding your output: ```{feedback}```. They encountered some error when running the SQL queries.
This typically means the value formats of some column(s) may not conform to what are expected in the SQL queries.
For example, the queries expect column A to be YES/NO, but the values of A are actually 1/0. You can, for instance, use the Python Executor to transform the values in this case.

Available Operations:
```{operation_description}```

IMPORTANT: There are no other operations, so use ONLY choose among the above operations."""

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

Plan our next step using either of these formats (depending on the step_type):
{{
  "step_type": "internal_reasoning",
  "message": <"Reflect out loud (for ourselves only)">
}}

{{
  "step_type": "operation",
  "name": "Document Retriever" | "Python Executor" | "SQL Executor" | "Standard Inner Join" | "Union",
  "args": {{"The argument to the operation that we call"}}
  "assign_to": "result_table_id"  # Must match one of the target schema IDs if this is a final result (i.e., correspond to a target schema directly)
}}

VERY IMPORTANT: If you produce a Python code, NEVER use pd.read_csv. Use tables["<ID>"] in your code (tables is a dict[str, pd.DataFrame] variable), then you will get it directly in a Pandas DataFrame format."""
