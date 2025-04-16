from processor.types.message import Message
from processor.llm.prompts import base_table_producer_prompts
from processor.llm.interface.model_interface import ModelInterface
from processor.utils import format_schema_with_samples
from pandas import DataFrame
import json
import pandas as pd


class BaseTableProducer:
    def __init__(self, model: ModelInterface):
        self.model = model

    def select_tables(
        self,
        available_tables: list[DataFrame],
        tables_descs: list[str],
        target_schema: list[str],
    ):
        """Returns the relevant tables among a set of available tables for the given
        target schema"""
        relevant_tables: list[DataFrame] = []
        for table_idx, table in enumerate(available_tables):
            msg: list[Message] = [
                {
                    "role": "system",
                    "content": base_table_producer_prompts["tables_selector"],
                },
                {
                    "role": "user",
                    "content": f"- Table: {format_schema_with_samples(table)}\n\n- Target schema: {target_schema}\n\n- Description: {tables_descs[table_idx]}",
                },
            ]
            table_relevancy_output = self.model.chat(msg)
            print(f"=> table_relevancy_output: {table_relevancy_output}")
            table_relevance = (
                table_relevancy_output.split("Relevant: ")[-1].lower().strip()
            )
            if table_relevance.startswith("yes"):
                print(f"==> Yes, this table is relevant!")
                relevant_tables.append(True)
            else:
                relevant_tables.append(False)
        return relevant_tables

    def extend_tables(self, table_mappings: list[DataFrame], tables_descs: list[str]):
        table_mappings
        pass

    def __produce_extend_tables_operations(
        self, available_tables: list[DataFrame], tables_descs: list[str]
    ):
        """
        Returns a list of operations to extend tables within
        """
        available_tables_formatted = ""
        for table_idx, table in enumerate(available_tables):
            available_tables_formatted += f"- Table {table_idx} ({tables_descs[table_idx]}):\n```{format_schema_with_samples(table)}```\n\n"
        available_tables_formatted = available_tables_formatted.strip()
        print(f"=> available_tables_formatted: {available_tables_formatted}")

        msg: list[Message] = [
            {
                "role": "system",
                "content": base_table_producer_prompts["row_extender_step_1"],
            },
            {"role": "user", "content": available_tables_formatted},
        ]
        reasoning = self.model.chat(msg)
        print(f"=> reasoning: {reasoning}")
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
        operations = self.model.chat(msg)
        print(f"=> operations: {operations}")
        return operations

    def __run_extend_tables_operations(
        self,
        operations: str,
        table_mappings: dict[str, DataFrame],
        last_table_mappings_idx: int,
    ):
        # Ensure non-mutability of the original object
        table_mappings_copy = {k: v.copy() for k, v in table_mappings.items()}

        # Parse the operations
        if operations.startswith("```"):
            operations = operations[3:]
        if operations.endswith("```"):
            operations = operations[:-3]
        if operations.startswith("json"):
            operations = operations[4:]
        operations = json.loads(operations)

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
