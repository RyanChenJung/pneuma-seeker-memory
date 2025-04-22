from typing import Any

from tqdm import tqdm
from processor.computation_graph import Node
from processor.model.message import LLMMessage
from processor.conductor_state import ConductorState
from processor.model.prompts import base_table_reducer_prompts
from processor.table.representation.abstract_table import AbstractTable
from processor.utils.string_processor import parse_code_string, parse_sql_string


class BaseTableReducer:
    def compute_target_table(
        self,
        ctx: ConductorState,
        base_table: AbstractTable,
        target_schema: list[str],
        num_rows=3,
        input_nodes: list[Node] = [],
    ) -> Node:
        """
        Projects `base_table`, specifically its schema, to the `target_schema`,
        resulting in `target_table`.
        """
        target_table_cols: dict[str, list[Any]] = dict()
        extra_input_nodes: list[Node] = []
        for col in target_schema:
            msg = [
                {
                    "role": "system",
                    "content": base_table_reducer_prompts["column_projection"],
                },
                {
                    "role": "user",
                    "content": f"Source table: ```{base_table.get_representation(num_rows, 42)}```\nTarget Schema: {target_schema}\nTarget Column: `{col}`",
                },
            ]
            operation: dict[str, str] = parse_code_string(ctx.llm.chat(msg))
            if operation["operation"] == "select_column":
                operation_node = ctx.computation_graph.create_node(
                    "Mapped a column directly.",
                    list(base_table[operation["columns_involved"][0]]),
                    input_nodes,
                )
            else:
                operation_node = self.__extract_column(
                    ctx,
                    base_table,
                    operation["columns_involved"],
                    col,
                    10,
                    input_nodes,
                )
            extra_input_nodes.append(operation_node)
            target_table_cols[col] = operation_node.computation_output
        target_table = type(base_table).merge_columns(target_table_cols)
        return ctx.computation_graph.create_node(
            "Projected columns from base table to target table.",
            target_table,
            input_nodes + extra_input_nodes,
        )

    def __extract_column(
        self,
        ctx: ConductorState,
        base_table: AbstractTable,
        columns_involved: list[str],
        target_column: str,
        row_batch=10,
        input_nodes: list[Node] = [],
    ) -> Node:
        sql_script = "SELECT "
        for col in columns_involved:
            sql_script += f'"{col}", '
        sql_script = sql_script[:-2] + "FROM base table;"

        columns_involved_table = ctx.table_store.execute_sql_query(
            sql_script,
            {
                "base_table": base_table,
            },
        )
        unique_columns_involved_table = columns_involved_table.drop_duplicates()

        # Ask LLM whether to use row-wise extraction or Python code
        msg = [
            {
                "role": "system",
                "content": base_table_reducer_prompts["extract_mode"],
            },
            {
                "role": "user",
                "content": f"Table ({min(5, len(unique_columns_involved_table))} rows): ```{unique_columns_involved_table.get_representation(5)}```\nOverall Schema: {list(base_table.get_schema())}\nNew Column: `{target_column}`",
            },
        ]
        extraction_mode = ctx.llm.chat(msg).strip()
        actual_values: list[str] = []
        if extraction_mode == "python_code":
            # Generate code from the LLM
            code_gen_msg = [
                {
                    "role": "system",
                    "content": "You are a data scientist. Given a table and a new column name, write a Python function called generate_column that takes a pandas DataFrame and returns a list representing the new column. Only use columns present in the table.",
                },
                {
                    "role": "user",
                    "content": f"Schema: {list(base_table.get_schema())}\nTarget column: {target_column}\nSample rows:\n{unique_columns_involved_table.get_representation(5)}",
                },
            ]
            code_str = parse_code_string(ctx.llm.chat(code_gen_msg))
            ctx.logger.info(f"Python code to extract: {code_str}")
            exec_globals = {}
            exec(code_str, exec_globals)

            ctx.logger.info(f"exec_globals: {exec_globals}")
            generated_func = exec_globals.get("generate_column")

            if not generated_func:
                raise ValueError("LLM did not return a valid 'generate_column' function.")

            actual_values = generated_func(columns_involved_table.get_data())
        else:
            # Keep track of how many rows to process at once
            rows: list[tuple[int, int]] = []
            for i in range(0, len(unique_columns_involved_table), row_batch):
                rows.append((i, i + row_batch))
            rows[-1] = (rows[-1][0], len(unique_columns_involved_table))

            new_col_values: list[str] = []
            for row in tqdm(rows, desc="Processing column extraction"):
                msg = [
                    {
                        "role": "system",
                        "content": base_table_reducer_prompts["extract_col"],
                    },
                    {
                        "role": "user",
                        "content": f"Table ({row[1]-row[0]} rows): ```{unique_columns_involved_table.get_representation(row[1]-row[0], None, True, row)}```\nOverall Schema: {list(base_table.get_schema())}\nNew Column: `{target_column}`",
                    },
                ]
                extracted_values = ctx.llm.chat(msg)
                new_col_values.extend(parse_code_string(extracted_values))

            results_cache: dict[str, str] = dict()
            columns = unique_columns_involved_table.get_schema()
            for idx, row in unique_columns_involved_table.iterrows():
                vals = []
                for col in columns:
                    vals.append(row[col])
                key = "_SEP_".join(vals)
                results_cache[key] = new_col_values[idx]

            for idx, row in columns_involved_table.iterrows():
                vals = []
                for col in columns:
                    vals.append(row[col])
                key = "_SEP_".join(vals)
                actual_values.append(results_cache[key])

        return ctx.computation_graph.create_node(
            "Extraced column values from existing columns in the base table.",
            actual_values,
            input_nodes,
        )

    def apply_predicate_to_target_table(
        self,
        ctx: ConductorState,
        target_table: AbstractTable,
        question: str,
        num_rows=3,
        input_nodes: list[Node] = [],
    ) -> Node:
        """
        Applies a natural-language predicate to target table.
        """
        msg: list[LLMMessage] = [
            {"role": "system", "content": base_table_reducer_prompts["reduce_row"]},
            {
                "role": "user",
                "content": f"""- Table: ```{target_table.get_representation(num_rows, 42)}```
- Question: {question}""",
            },
        ]
        llm_output = ctx.llm.chat(msg)
        sql_query = parse_sql_string(llm_output)
        ctx.logger.info(f"SQL Query: {sql_query}")
        final_table = ctx.table_store.execute_sql_query(
            sql_query, {"target_table": target_table}
        )
        return ctx.computation_graph.create_node(
            f"Applied this predicate to the rows of target table: {sql_query}",
            final_table,
            input_nodes,
        )
