import sqlite3
from typing import Any

import pandas as pd
from processor.computation_graph import Node
from processor.table.representation.abstract_table import AbstractTable
from sentence_transformers.util import cos_sim

from processor.model.prompts import base_table_producer_prompts
from processor.conductor_state import ConductorState
from processor.utils.json_processor import parse_json
from processor.model.message import LLMMessage
from processor.utils.string_processor import parse_code_string, parse_sql_string


class BaseTableProducer:
    """
    BaseTableProducer is a core service of Processor. It provides methods for
    producing a base table, which is a table that contains the table defined using
    the target schema produced by SchemaProcessor.
    """

    def select_relevant_table_ids(
        self,
        ctx: ConductorState,
        db_schema: str,
        target_schema: list[str],
        table_descriptions: dict[str, str],
        num_rows=3,
        input_computation_nodes: list[Node] = [],
    ):
        """
        Returns the IDs of relevant tables within the DB schema for the given
        target schema.

        Args:
            ctx (ConductorState): Conductor state object.
            db_schema (str): The DB schema to get the tables from.
            target_schema (list[str]): The target schema to choose the tables.
            table_descriptions (dict[str,str]): The descriptions of the tables.
            input_computation_nodes (Node): A list of input nodes to keep track of computation.
        Returns:
            Output (Node[list[str]]): Computation node consisting of list of strings as the IDs of the relevant tables.
        """
        relevant_table_ids: list[str] = []
        table_mapping = ctx.table_store.get_all_tables_in_db_schema(db_schema)

        for table_id, table in table_mapping.items():
            ctx.logger.info(f"Checking the relevance of table `{table_id}`")
            table_description = table_descriptions[table_id]
            msg: list[LLMMessage] = [
                {
                    "role": "system",
                    "content": base_table_producer_prompts["tables_selector"],
                },
                {
                    "role": "user",
                    "content": f"""- Table: ```{table.get_representation(num_rows, 42)}```
- Target schema: ```{target_schema}```
- Description: ```{table_description}```""",
                },
            ]
            table_relevancy_output = ctx.llm.chat(msg)
            ctx.logger.info(f"=> Table relevancy output: {table_relevancy_output}")
            table_relevance = (
                table_relevancy_output.split("Relevant: ")[-1].lower().strip()
            )
            if table_relevance.startswith("yes"):
                ctx.logger.info(f"==> Conclusion: The table is considered relevant!")
                relevant_table_ids.append(table_id)
        return ctx.computation_graph.create_node(
            computation_description="Selected relevant table IDs for the given target schema.",
            computation_output=relevant_table_ids,
            input_nodes=input_computation_nodes,
        )

    def produce_union_operations(
        self,
        ctx: ConductorState,
        db_schema: str,
        table_descriptions: dict[str, str],
        num_rows=3,
        input_computation_nodes: list[Node] = [],
    ) -> Node:
        """
        Returns a list of operations to union tables (if any) within the DB schema.

        Args:
            ctx (ConductorState): Conductor state object.
            db_schema (str): The DB schema to get the tables from.
            table_descriptions (dict[str,str]): The descriptions of the tables.
            num_rows (int): Number of rows to sample from each table.
            input_computation_nodes (Node): A list of input nodes to keep track of computation.
        Returns:
            Output (Node[Any]): Computation node consisting of the union operations.
        """
        available_tables_formatted = self.__format_available_tables(
            ctx,
            db_schema,
            num_rows,
            table_descriptions,
        )

        msg: list[LLMMessage] = [
            {
                "role": "system",
                "content": base_table_producer_prompts["row_extender_step_1"],
            },
            {"role": "user", "content": available_tables_formatted},
        ]
        reasoning = ctx.llm.chat(msg)
        ctx.logger.info(f"=> reasoning: {reasoning}")
        msg: list[LLMMessage] = [
            {
                "role": "system",
                "content": base_table_producer_prompts["row_extender_step_2"],
            },
            {
                "role": "user",
                "content": f"- Tables: {available_tables_formatted}\n\n- Reasoning: {reasoning}",
            },
        ]
        operations: list[dict[str, Any]] = parse_code_string(ctx.llm.chat(msg))
        ctx.logger.info(f"=> operations: {operations}")
        return ctx.computation_graph.create_node(
            computation_description="Produced union operations.",
            computation_output=operations,
            input_nodes=input_computation_nodes,
        )

    def run_union_operations(
        self,
        ctx: ConductorState,
        table_mappings: dict[str, AbstractTable],
        operations: list[dict[str, Any]],
        input_computation_nodes: list[Node] = [],
    ) -> Node:
        """
        Returns a list of operations to union tables (if any) within the DB schema.

        Args:
            ctx (ConductorState): Conductor state object.
            table_mappings (dict[str,AbstractTable]): The mapping between table IDs and table objects.
            operations (list[dict[str, Any]]): The union operations.
            input_computation_nodes (Node): A list of input nodes to keep track of computation.
        Returns:
            Output (Node[dict[str, AbstractTable]]): Computation node consisting of the table mappings after the operations have been applied.
        """

        # Ensure non-mutability of the original object
        table_mappings_copy = {k: v.copy() for k, v in table_mappings.items()}

        for operation in operations:
            normalized_tables: list[AbstractTable] = []
            union_table_id: str = operation["Output Table ID"]
            for table_name in operation["Tables"]:
                table = table_mappings_copy[table_name]
                mapping: dict[str, str] = operation["Mappings"][table_name]

                table.rename_schema(mapping)
                unified_schema: list[str] = operation["Unified Schema"]
                table.add_missing_columns(unified_schema, default_value=None)
                table = table.select_columns(unified_schema)

                normalized_tables.append(table)
                del table_mappings_copy[table_name]

            extended_table = type(normalized_tables[0]).concat(normalized_tables)
            table_mappings_copy[union_table_id] = extended_table
        return ctx.computation_graph.create_node(
            computation_description="Ran the union table operations",
            computation_output=table_mappings_copy,
            input_nodes=input_computation_nodes,
        )

    def produce_join_operations(
        self,
        ctx: ConductorState,
        db_schema: str,
        table_descriptions: dict[str, str],
        num_rows=3,
        input_computation_nodes: list[Node] = [],
    ) -> Node:
        """
        Returns a list of operations to union tables (if any) within the DB schema.

        Args:
            ctx (ConductorState): Conductor state object.
            db_schema (str): The DB schema to get the tables from.
            table_descriptions (dict[str,str]): The descriptions of the tables.
            num_rows (int): The number of rows to sample.
            input_computation_nodes (Node): A list of input nodes to keep track of computation.
        Returns:
            Output (Node[list[dict[str,str]]]): Computation node consisting of the join operations.
        """
        available_tables_formatted = self.__format_available_tables(
            ctx, db_schema, num_rows, table_descriptions
        )
        msg: list[LLMMessage] = [
            {"role": "system", "content": base_table_producer_prompts["join_planner"]},
            {"role": "user", "content": available_tables_formatted},
        ]
        join_operations: list[dict[str, str]] = parse_code_string(ctx.llm.chat(msg))
        ctx.logger.info(f"Join operations: {join_operations}")
        return ctx.computation_graph.create_node(
            computation_description="Produced join operations",
            computation_output=join_operations,
            input_nodes=input_computation_nodes,
        )

    def run_join_operations(
        self,
        ctx: ConductorState,
        table_mapping: dict[str, AbstractTable],
        operations: list[dict[str, str]],
        num_values=3,
        input_computation_nodes: list[Node] = [],
    ) -> Node:
        """
        Returns a list of operations to join tables (if any) within the DB schema.

        Args:
            ctx (ConductorState): Conductor state object.
            table_mappings (dict[str,AbstractTable]): The mapping between table IDs and table objects.
            operations (list[dict[str, Any]]): The join operations.
            num_values (int): Number of rows to sample for each table.
            input_computation_nodes (Node): A list of input nodes to keep track of computation.
        Returns:
            Output (Node[dict[str, AbstractTable]]): Computation node consisting of the table mappings after the operations have been applied.
        """

        # Ensure non-mutability of the original object
        table_mapping_copy = {k: v.copy() for k, v in table_mapping.items()}
        extra_input_nodes: list[Node] = []
        for operation in operations:
            join_table_id: str = operation["Join Result"]
            left_table_id: str = operation["Left Table"]
            right_table_id: str = operation["Right Table"]
            left_join_key: str = operation["Left Join Key"]
            right_join_key: str = operation["Right Join Key"]

            left_key_samples = table_mapping_copy[left_table_id].get_attribute_values(
                attr_name=left_join_key,
                num_values=num_values,
                random_seed=42,
            )
            right_key_samples = table_mapping_copy[right_table_id].get_attribute_values(
                attr_name=right_join_key,
                num_values=num_values,
                random_seed=42,
            )

            msg = [
                {
                    "role": "system",
                    "content": base_table_producer_prompts["classification_prompt"],
                },
                {
                    "role": "user",
                    "content": f"""- Samples of left join key ({left_join_key}): {left_key_samples}
- Samples of right join key ({right_join_key}): {right_key_samples}""",
                },
            ]
            classification_result = ctx.llm.chat(msg)
            ctx.logger.info(f"=> classification_result: {classification_result}")

            if (
                classification_result.lower()
                .split("classification: ")[-1]
                .startswith("semantic")
            ):
                join_node = self.__run_semantic_join_operation(
                    ctx,
                    table_mapping_copy[left_table_id],
                    table_mapping_copy[right_table_id],
                    left_join_key,
                    right_join_key,
                    input_computation_nodes,
                )
            else:
                join_node = self.__run_std_join_operation(
                    ctx,
                    left_table_id,
                    right_table_id,
                    table_mapping_copy[left_table_id],
                    table_mapping_copy[right_table_id],
                    left_join_key,
                    right_join_key,
                    input_computation_nodes,
                )
            extra_input_nodes.append(join_node)
            joined_table = join_node.computation_output
            table_mapping_copy[join_table_id] = joined_table
            del table_mapping_copy[left_table_id]
            del table_mapping_copy[right_table_id]
        return ctx.computation_graph.create_node(
            "Ran join operations over the tabless",
            table_mapping_copy,
            input_computation_nodes + extra_input_nodes,
        )

    def __run_semantic_join_operation(
        self,
        ctx: ConductorState,
        A: AbstractTable,
        B: AbstractTable,
        keyA: str,
        keyB: str,
        input_nodes: list[Node] = [],
        alpha=0.9,
    ) -> Node:
        # Store best matches for A -> B
        best_match_from_A = dict()
        for idx_a, val_a in A[keyA].items():
            best_score = -1
            best_idx_b = None
            for idx_b, val_b in B[keyB].items():
                score = self.__check_similarity(ctx, val_a, val_b)
                if score > best_score:
                    best_score = score
                    best_idx_b = idx_b
            if best_score >= alpha:
                best_match_from_A[idx_a] = (best_idx_b, best_score)

        # Store best matches for B -> A
        best_match_from_B = {}
        for idx_b, val_b in B[keyB].items():
            best_score = -1
            best_idx_a = None
            for idx_a, val_a in A[keyA].items():
                score = self.__check_similarity(ctx, val_b, val_a)
                if score > best_score:
                    best_score = score
                    best_idx_a = idx_a
            if best_score >= alpha:
                best_match_from_B[idx_b] = (best_idx_a, best_score)

        # Keep mutual best matches only
        matches: list[Any] = []
        for idx_a, (idx_b, score_ab) in best_match_from_A.items():
            if idx_b in best_match_from_B and best_match_from_B[idx_b][0] == idx_a:
                row_a = A.get_row(idx_a)
                row_b = B.get_row(idx_b)
                merged_row = pd.concat([row_a, row_b], axis=0)
                merged_row["similarity_score"] = score_ab
                matches.append(merged_row)
        merged_table = type(A).merge_rows(matches)
        return ctx.computation_graph.create_node(
            "Ran semantic join operation.",
            merged_table,
            input_nodes,
        )

    def __check_similarity(ctx: ConductorState, a: str, b: str) -> float:
        a_embed = ctx.embedding_model.embed(a)
        b_embed = ctx.embedding_model.embed(b)
        return cos_sim(a_embed, b_embed).item()

    def __run_std_join_operation(
        self,
        ctx: ConductorState,
        left_table_id: str,
        right_table_id: str,
        left_table: AbstractTable,
        right_table: AbstractTable,
        left_join_key: str,
        right_join_key: str,
        input_nodes: list[Node] = [],
    ):
        """Runs a single standard join operation."""
        msg = [
            {
                "role": "system",
                "content": base_table_producer_prompts["std_join"],
            },
            {
                "role": "user",
                "content": f"""- Left table (ID: {left_table_id}; join key: {left_join_key}): {left_table.get_representation(3, 42)}
- Right table (ID: {right_table_id}; join key: {right_join_key}): {right_table.get_representation(3, 42)}""",
            },
        ]
        sql_script = parse_sql_string(ctx.llm.chat(msg))

        ctx.logger.info(f"=> Executing SQL: {sql_script}")
        joined_table = ctx.table_store.execute_sql_query(
            sql_query=sql_script,
            tables_involved={
                left_table_id: left_table,
                right_table_id: right_table,
            },
        )
        return ctx.computation_graph.create_node(
            f"Executing this SQL script for a standard join operation:\n{sql_script}",
            joined_table,
            input_nodes,
        )

    def __format_available_tables(
        self,
        ctx: ConductorState,
        db_schema: str,
        num_rows: int,
        table_descriptions: dict[str, str],
    ):
        available_tables_formatted = ""
        table_mappings = ctx.table_store.get_all_tables_in_db_schema(db_schema)
        for table_id, table in table_mappings.items():
            table_description = table_descriptions[table_id]
            available_tables_formatted += f"""- {table_id} ({table_description}):
```{table.get_representation(num_rows, 42)}```\n"""

        available_tables_formatted = available_tables_formatted.strip()
        ctx.logger.info(f"=> available_tables_formatted: {available_tables_formatted}")
        return available_tables_formatted
