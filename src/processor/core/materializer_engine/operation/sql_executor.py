from logging import Logger

import duckdb
from pandas import DataFrame

from processor.model.interface.abstract_model import AbstractModel
from processor.model.llm_message import LLMMessage, Role
from processor.utils.json_processor import parse_sql


def format_available_tables(tables: dict[str, DataFrame]):
        tables_repr = ""
        for table_id, table in tables.items():
            tables_repr += (
                f"\n- Table {table_id}:\ncol: {" | ".join(list(table.columns))}"
            )
            if len(table) > 0:
                # Sample 5 rows to represent the table
                sample_rows = table.sample(min(5, len(table)), random_state=42)
                sample_row_idx = 1
                for _, data in sample_rows.iterrows():
                    str_data = [str(i) for i in data]
                    tables_repr += (
                        f"\nsample row {sample_row_idx}: {" | ".join(str_data)}"
                    )
                    sample_row_idx += 1
        return tables_repr.strip()


def execute_sql(logger: Logger, sql_query: str, tables: dict[str, DataFrame], llm: AbstractModel):
    db = duckdb.connect(database=":memory:")
    logger.info(f"Executing this SQL query: {sql_query} over these tables: {tables}")

    # Clear previous tables
    for table in db.execute("SHOW TABLES").fetchall():
        db.execute(f"DROP TABLE {table[0]}")

    # Register new tables
    for name, df in tables.items():
        db.register(name, df)

    try:
        print(f"Sanity checking the SQL query {sql_query}")
        fixed_sql = parse_sql(
            llm.chat(
                [
                    LLMMessage(
                        role=Role.SYSTEM.value,
                        content="""You are a SQL query fixer. Given an input SQL query, check if it contains any syntactic or semantic errors (e.g., case sensitivity, unescaped identifiers, invalid field names, type mismatches, or non-standard functions for the target SQL engine: DuckDB). Fix the query as needed to ensure it runs correctly in the specified engine. Use double quotes for identifiers (e.g., "Beach Name" instead of Beach Name), and handle case sensitivity appropriately for string comparisons. Also, we use DuckDB, so you may need to adjust the functions (e.g., change the function substring_index to substring). Output the updated/fixed/same-if-no-issue SQL query directly without any explanation or formatting.""",
                    ),
                    LLMMessage(
                        role=Role.USER.value,
                        content=f"SQL Query: {sql_query}\n\nAvailable Tables: {format_available_tables(tables)}",
                    ),
                ]
            )
        )
        print(f"Executing Fixed SQL: {fixed_sql}")
        return db.execute(fixed_sql).fetchdf()
    except Exception as e:
        raise RuntimeError(f"SQL execution failed: {e}")
