import json

from pandas import DataFrame

from processor.core.ir_system.ir_data_model import (
    AbstractDocument,
    convert_retrieval_results_to_str,
)
from processor.core.materializer_engine.operation.abstract_operation import (
    AbstractOperation,
)
from processor.core.materializer_engine.tool.abstract_tool import AbstractTool
from processor.model.llm_message import LLMMessage


class MEPromptFactory:
    def get_planning_prompt(
        self,
        target_schemas: dict[str, DataFrame],
        column_descriptions: dict[str, dict[str, str]],
        sqls,
        history: list[LLMMessage],
        tools: list[AbstractTool],
        operations: list[AbstractOperation],
        retrieved_documents: set[AbstractDocument],
        intermediate_tables: dict[str, DataFrame],
    ) -> str:
        return f"""
You are a smart data scientist planning to materialize the following schemas:

Target Schemas (these are the final tables you need to create):
{json.dumps({k: list(df.columns) for k, df in target_schemas.items()}, indent=2)}

Column Descriptions of Target Schemas:
{column_descriptions}

Current Progress:
- Available Intermediate Tables: {list(intermediate_tables.keys())}
- Retrieved Documents: {convert_retrieval_results_to_str(list(retrieved_documents))}

SQL Statements:
{sqls}

Available Tools and Operations:
{[tool.describe() for tool in tools]}
{[op.describe() for op in operations]}

Recent History:
{[msg['content'] for msg in history][-5:]}

Plan your next step using this format:
{{
  "step_type": "operation" | "tool",
  "name": "Operation or Tool name",
  "inputs": ["main_input"] | ["table1_id", "table2_id"],
  "parameters": {{ ... }},
  "assign_to": "result_table_name"  # Must match one of the target schema names if this is a final result
}}
"""

    def get_retrieval_prompt(self, target_schemas, sqls) -> str:
        return f"""
You are planning to fill the following table schemas using available documents:

Schemas: {json.dumps({k: list(df.columns) for k, df in target_schemas.items()}, indent=2)}
SQLs: {sqls}

Return the kind of data you expect to need to complete these schemas.
"""
