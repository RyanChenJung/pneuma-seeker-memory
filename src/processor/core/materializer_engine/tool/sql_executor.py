from logging import Logger

import duckdb
from pandas import DataFrame


def execute_sql(logger: Logger, sql_query: str, tables: dict[str, DataFrame]):
    db = duckdb.connect(database=":memory:")
    logger.info(f"Executing this SQL query: {sql_query} over these tables: {tables}")

    # Clear previous tables
    for table in db.execute("SHOW TABLES").fetchall():
        db.execute(f"DROP TABLE {table[0]}")

    # Register new tables
    for name, df in tables.items():
        db.register(name, df)

    try:
        return db.execute(sql_query).fetchdf()
    except Exception as e:
        raise RuntimeError(f"SQL execution failed: {e}")
