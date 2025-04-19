import sqlite3
from typing import Any

import pandas as pd
from processor.table.representation.abstract_table import AbstractTable
from sentence_transformers import util

from processor.models.prompts import base_table_producer_prompts
from processor.table.representation.metadata import TableMetadataType
from processor.conductor_state import ConductorState
from processor.utils.json_processor import parse_json
from processor.models.message import LLMMessage
from processor.utils.string_processor import parse_code_string


class BaseTableProducer:
    def select_relevant_tables(
        self,
        ctx: ConductorState,
        db_schema: str,
        target_schema: list[str],
        num_rows=3,
    ):
        """Returns the IDs of relevant tables within the DB schema for the given
        target schema"""
        relevant_table_ids: list[str] = []
        table_mapping = ctx.table_store.get_all_tables_in_db_schema(db_schema)

        for table_id, table in table_mapping.items():
            table_description = ctx.table_store.get_table_metadata(
                schema=db_schema,
                table_id=table_id,
                metadata_id=TableMetadataType.TABLE_DESCRIPTION,
            )
            msg: list[LLMMessage] = [
                {
                    "role": "system",
                    "content": base_table_producer_prompts["tables_selector"],
                },
                {
                    "role": "user",
                    "content": f"""- Table: ```{table.get_representation(table, num_rows, 42)}```
- Target schema: ```{target_schema}```
- Description: ```{table_description}```""",
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
        ctx: ConductorState,
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
            table_mappings=ctx.table_store.get_all_tables_in_db_schema(db_schema),
            operations_json=operations,
        )
        return mapping_results

    def __produce_union_tables_operations(
        self,
        ctx: ConductorState,
        db_schema: str,
        num_rows=3,
    ):
        """
        Returns a list of operations to extend tables within
        """
        available_tables_formatted = self.__format_available_tables(
            ctx, db_schema, num_rows
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

    def join_tables(
        self,
        ctx: ConductorState,
        db_schema: str,
        num_rows=3,
        num_values=5,
    ):
        """
        Returns a list of tables in the schema, some of which may have been merged.
        """
        ctx.logger.info("Step 1: Produce join operations")
        join_operations = self.__produce_join_operations(
            ctx, db_schema=db_schema, num_rows=num_rows
        )
        join_operations: list[dict[str, str]] = parse_json(join_operations)

        ctx.logger.info("Step 2: Execute join operations")
        table_mapping = ctx.table_store.get_all_tables_in_db_schema(db_schema=db_schema)
        for op in join_operations:
            join_table_id: str = op["Join Result"]
            left_table_id: str = op["Left Table"]
            right_table_id: str = op["Right Table"]
            left_join_key: str = op["Left Join Key"]
            right_join_key: str = op["Right Join Key"]

            left_key_samples = table_mapping[left_table_id].get_attribute_values(
                attr_name=left_join_key,
                num_values=num_values,
                random_seed=42,
            )
            right_key_samples = table_mapping[right_table_id].get_attribute_values(
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
                # joined_table = self.__run_semantic_join_operation()
                joined_table = self.__run_semantic_join_operation(
                    ctx,
                    table_mapping[left_table_id],
                    table_mapping[right_table_id],
                    left_join_key,
                    right_join_key,
                )
            else:
                joined_table = self.__run_std_join_operation(
                    ctx,
                    left_table_id,
                    right_table_id,
                    table_mapping[left_table_id],
                    table_mapping[right_table_id],
                    left_join_key,
                    right_join_key,
                )

            table_mapping[join_table_id] = joined_table
            del table_mapping[left_table_id]
            del table_mapping[right_table_id]

    def __produce_join_operations(
        self, ctx: ConductorState, db_schema: str, num_rows=3
    ):
        available_tables_formatted = self.__format_available_tables(
            ctx, db_schema, num_rows
        )
        msg: list[LLMMessage] = [
            {"role": "system", "content": base_table_producer_prompts["join_planner"]},
            {"role": "user", "content": available_tables_formatted},
        ]
        join_operations = ctx.llm.chat(msg)
        ctx.logger.info(f"=> join_operations: {join_operations}")
        return join_operations

    def __run_semantic_join_operation(
        self,
        ctx: ConductorState,
        A: pd.DataFrame,
        B: pd.DataFrame,
        keyA: str,
        keyB: str,
        alpha=0.9,
    ):
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
        matches = []
        for idx_a, (idx_b, score_ab) in best_match_from_A.items():
            if idx_b in best_match_from_B and best_match_from_B[idx_b][0] == idx_a:
                row_a = A.loc[idx_a]
                row_b = B.loc[idx_b]
                merged_row = pd.concat([row_a, row_b], axis=0)
                merged_row["similarity_score"] = score_ab
                matches.append(merged_row)

        return pd.DataFrame(matches)

    def __check_similarity(ctx: ConductorState, a: str, b: str) -> float:
        a_embed = ctx.embedding_model.embed(a)
        b_embed = ctx.embedding_model.embed(b)
        cos_sim = util.cos_sim(a_embed, b_embed)
        return cos_sim[0].item()

    def __run_std_join_operation(
        self,
        ctx: ConductorState,
        left_table_id: str,
        right_table_id: str,
        left_table: AbstractTable,
        right_table: AbstractTable,
        left_join_key: str,
        right_join_key: str,
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
        sql_script = parse_code_string(ctx.llm.chat(msg))

        ctx.logger.info("=> Executing SQL")
        conn = sqlite3.connect(":memory:")
        left_table.to_sql(left_table_id, conn, index=False, if_exists="replace")
        right_table.to_sql(right_table_id, conn, index=False, if_exists="replace")

        joined_table = pd.read_sql_query(sql_script, conn)
        return joined_table

    def __format_available_tables(
        self, ctx: ConductorState, db_schema: str, num_rows: int
    ):
        available_tables_formatted = ""
        table_mappings = ctx.table_store.get_all_tables_in_db_schema(db_schema)
        for table_id, table in table_mappings.items():
            table_description = ctx.table_store.get_table_metadata(
                schema=db_schema,
                table_id=table_id,
                metadata_id=TableMetadataType.TABLE_DESCRIPTION,
            )
            available_tables_formatted += f"""- {table_id} ({table_description}):
```{table.get_representation(table, num_rows, 42)}```\n"""

        available_tables_formatted = available_tables_formatted.strip()
        ctx.logger.info(f"=> available_tables_formatted: {available_tables_formatted}")
        return available_tables_formatted
