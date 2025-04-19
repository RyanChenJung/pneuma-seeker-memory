import sqlite3
import pandas as pd
from typing import Any

from pandas import DataFrame
from tqdm import tqdm
from processor.models.message import LLMMessage
from processor.conductor_state import ConductorState
from processor.models.prompts import base_table_reducer_prompts
from processor.utils.string_processor import parse_code_string


class BaseTableReducer:
    def project_columns(
        self,
        ctx: ConductorState,
        base_table: DataFrame,
        target_schema: list[str],
        num_rows=3,
    ):
        target_table = DataFrame()
        for col in target_schema:
            msg = [
                {
                    "role": "system",
                    "content": base_table_reducer_prompts["column_projection"],
                },
                {
                    "role": "user",
                    "content": f"Source table: ```{ctx.table_reader.format_table(base_table, num_rows, 42)}```\nTarget Schema: {target_schema}\nTarget Column: `{col}`",
                },
            ]
            operation: dict[str, str] = parse_code_string(ctx.llm.chat(msg))
            if operation["operation"] == "select_column":
                target_table[col] = base_table[operation["columns_involved"]]
            else:
                target_table[col] = self.__extract_column(
                    ctx, base_table, operation["columns_involved"], col
                )
        return target_table

    def __extract_column(
        self,
        ctx: ConductorState,
        base_table: DataFrame,
        columns_involved: list[str],
        target_column: str,
        row_batch=10,
    ) -> list[str]:
        conn = sqlite3.connect(":memory:")
        base_table.to_sql("base_table", conn, if_exists="replace", index=False)

        sql_script = "SELECT "
        for col in columns_involved:
            sql_script += f'"{col}", '
        sql_script = sql_script[:-2] + "FROM base table;"

        columns_involved_table = pd.read_sql(sql_script, conn)
        unique_columns_involved_table = (
            columns_involved_table.drop_duplicates().reset_index(drop=True)
        )

        # Keep track of how many rows to process at once
        rows = []
        for i in range(0, len(unique_columns_involved_table), row_batch):
            rows.append((i, i + row_batch))
        rows[-1] = (rows[-1][0], len(unique_columns_involved_table))

        new_col_values = []
        for row in tqdm(rows, desc="Processing column extraction"):
            msg = [
                {"role": "system", "content": base_table_reducer_prompts['extract_col']},
                {
                    "role": "user",
                    "content": f"Table ({row[1]-row[0]} rows): ```{ctx.table_reader.format_table(unique_columns_involved_table, row[1]-row[0], None, True, row)}```\nOverall Schema: {list(base_table.columns)}\nNew Column: `{target_column}`",
                },
            ]
            extracted_values = ctx.llm.chat(msg)
            new_col_values.extend(parse_code_string(extracted_values))

        results_cache = dict()
        columns = unique_columns_involved_table.columns
        for idx, row in unique_columns_involved_table.iterrows():
            vals = []
            for col in columns:
                vals.append(row[col])
            key = "_SEP_".join(vals)
            results_cache[key] = new_col_values[idx]

        actual_values = []
        for idx, row in columns_involved_table.iterrows():
            vals = []
            for col in columns:
                vals.append(row[col])
            key = "_SEP_".join(vals)
            actual_values.append(results_cache[key])
        return actual_values

    def apply_predicate_to_rows(
        self,
        ctx: ConductorState,
        target_table: pd.DataFrame,
        question: str,
        num_rows = 3,
    ) -> pd.DataFrame:
        msg: list[LLMMessage] = [
            {'role': 'system', 'content': base_table_reducer_prompts['reduce_row']},
            {'role': 'user', 'content': f"""- Table: ```{ctx.table_reader.format_table(target_table, num_rows, 42)}```
- Question: {question}"""}
        ]
        llm_output = ctx.llm.chat(msg)
        sql_query = parse_code_string(llm_output)

        ctx.logger.info(f"SQL Query: {sql_query}")
        conn = sqlite3.connect(":memory:")
        target_table.to_sql('target_table', conn, index=False, if_exists="replace")
        final_table = pd.read_sql(sql_query, conn)
        return final_table
