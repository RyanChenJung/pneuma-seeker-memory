from typing import Any
from processor.table_store.metadata import TableMetadata
from processor.utils.json_processor import parse_json
from processor.utils.message import Message
from processor.llm.prompts import base_table_producer_prompts
import json
import pandas as pd

from processor.utils.system_context import SystemContext


class BaseTableProducer:
    def select_relevant_tables(
        self,
        ctx: SystemContext,
        db_schema: str,
        target_schema: list[str],
        num_rows=3,
    ):
        """Returns the IDs of relevant tables within the DB schema for the given
        target schema"""
        relevant_table_ids: list[str] = []
        table_mapping = ctx.table_store.get_all_tables_in_schema(db_schema)

        for table_id, table in table_mapping.items():
            table_description = ctx.table_store.retrieve_table_metadata(
                schema=db_schema,
                table_id=table_id,
                metadata_id=TableMetadata.TABLE_DESCRIPTION,
            )
            msg: list[Message] = [
                {
                    "role": "system",
                    "content": base_table_producer_prompts["tables_selector"],
                },
                {
                    "role": "user",
                    "content": f"""- Table: {ctx.table_formatter.format_table(table, num_rows, 42)}
                    
- Target schema: {target_schema}
- Description: {table_description}""",
                },
            ]
            table_relevancy_output = ctx.llm.chat(msg)
            ctx.logger.info(f"=> table_relevancy_output: {table_relevancy_output}")
            table_relevance = (
                table_relevancy_output.split("Relevant: ")[-1].lower().strip()
            )
            if table_relevance.startswith("yes"):
                ctx.logger.info(f"==> Yes, this table is relevant!")
                relevant_table_ids.append(table_id)
        return relevant_table_ids

    def union_tables(
        self,
        ctx: SystemContext,
        db_schema: str,
        num_rows=3,
    ):
        """
        Unions tables within the DB schema.
        """
        operations = self.__produce_union_tables_operations(
            ctx=ctx,
            db_schema=db_schema,
            num_rows=num_rows,
        )
        mapping_results = self.__run_union_tables_operations(
            table_mappings=ctx.table_store.get_all_tables_in_schema(db_schema),
            operations_json=operations,
        )
        return mapping_results

    def __produce_union_tables_operations(
        self,
        ctx: SystemContext,
        db_schema: str,
        num_rows=3,
    ):
        """
        Returns a list of operations to extend tables within
        """
        available_tables_formatted = ""
        table_mapping = ctx.table_store.get_all_tables_in_schema(db_schema)
        for table_id, table in table_mapping.items():
            table_description = ctx.table_store.retrieve_table_metadata(
                schema=db_schema,
                table_id=table_id,
                metadata_id=TableMetadata.TABLE_DESCRIPTION,
            )
            available_tables_formatted += f"- {table_id} ({table_description}):\n```{ctx.table_formatter.format_table(table, num_rows, 42)}```\n\n"
        available_tables_formatted = available_tables_formatted.strip()
        ctx.logger.info(f"=> available_tables_formatted: {available_tables_formatted}")

        msg: list[Message] = [
            {
                "role": "system",
                "content": base_table_producer_prompts["row_extender_step_1"],
            },
            {"role": "user", "content": available_tables_formatted},
        ]
        reasoning = ctx.llm.chat(msg)
        ctx.logger.info(f"=> reasoning: {reasoning}")
        msg: list[Message] = [
            {
                "role": "system",
                "content": base_table_producer_prompts["row_extender_step_2"],
            },
            {
                "role": "user",
                "content": f"- Tables: {available_tables_formatted}\n\n- Reasoning: {reasoning}",
            },
        ]
        operations = ctx.llm.chat(msg)
        ctx.logger.info(f"=> operations: {operations}")
        return operations

    def __run_union_tables_operations(
        self,
        table_mappings: dict[str, Any],
        operations_json: str,
    ):
        # Ensure non-mutability of the original object
        table_mappings_copy = {k: v.copy() for k, v in table_mappings.items()}

        # Parse the operations
        operations: list[dict[str, str]] = parse_json(operations_json)
        
        if operations_json.startswith("```"):
            operations_json = operations_json[3:]
        if operations_json.endswith("```"):
            operations_json = operations_json[:-3]
        if operations_json.startswith("json"):
            operations_json = operations_json[4:]

        # Execute the operations
        extended_dfs = []
        last_table_mappings_idx = 1
        for operation in operations:
            normalized_tables = []
            for table_name in operation["Tables"]:
                df = table_mappings_copy[table_name]
                mapping = operation["Mappings"][table_name]

                renamed_df = df.rename(columns=mapping)
                schema = operation["Unified Schema"]
                for col in schema:
                    if col not in renamed_df.columns:
                        renamed_df[col] = None

                renamed_df = renamed_df[schema]
                normalized_tables.append(renamed_df)
            extended_df = pd.concat(normalized_tables, ignore_index=True)
            extended_dfs.append(extended_df)
        for extended_df in extended_dfs:
            table_mappings_copy[f"Table_{last_table_mappings_idx+1}"] = extended_df
            last_table_mappings_idx += 1
        return extended_dfs

    def semantic_join(self, ctx: SystemContext, db_schema: str, num_rows=3):
        ctx.logger.info('Step 1: Produce join operations')
        join_operations = self.__produce_semantic_join_operations(
            ctx, db_schema=db_schema, num_rows=num_rows
        )
        join_operations: list[dict[str, str]] = parse_json(join_operations)

        ctx.logger.info('Step 2: Execute join operations')
        for op in join_operations:
            join_result: str = op['Join Result']
            left_table: str = op['Left Table']
            right_table: str = op['Right Table']
            left_join_key: str = op['Left Join Key']
            right_join_key: str = op['Right Join Key']

            

            left_key_samples = tables[left_table][left_join_key].sample(5, random_state=42)    
            right_key_samples = tables[right_table][right_join_key].sample(5, random_state=42)
            msg = [
                {'role': 'system', 'content': classification_prompt},
                {'role': 'user', 'content': f'- Samples of left join key ({left_join_key}): {left_key_samples}\n\n- Samples of right join key ({right_join_key}): {right_key_samples}'},
            ]
            classification_result = model.chat(msg)
            print(f"=> classification_result: {classification_result}")


    def __produce_semantic_join_operations(
        self, ctx: SystemContext, db_schema: str, num_rows=3
    ):
        available_tables_formatted = ""
        table_mappings = ctx.table_store.get_all_tables_in_schema(db_schema)
        for table_id, table in table_mappings.items():
            table_description = ctx.table_store.retrieve_table_metadata(
                schema=db_schema,
                table_id=table_id,
                metadata_id=TableMetadata.TABLE_DESCRIPTION,
            )
            available_tables_formatted += f"""- {table_id} ({table_description}):
```{ctx.table_formatter.format_table(table, num_rows, 42)}```\n"""

        available_tables_formatted = available_tables_formatted.strip()
        ctx.logger.info(f"=> available_tables_formatted: {available_tables_formatted}")

        msg: list[Message] = [
            {"role": "system", "content": base_table_producer_prompts["join_planner"]},
            {"role": "user", "content": available_tables_formatted},
        ]
        plan = ctx.llm.chat(msg)
        ctx.logger.info(f"=> plan: {plan}")
        return plan
