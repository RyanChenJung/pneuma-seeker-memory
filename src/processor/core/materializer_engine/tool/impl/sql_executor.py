# tools/sql_engine.py
import duckdb
import pandas as pd

from processor.core.materializer_engine.tool.abstract_tool import AbstractTool

class SQLExecutor(AbstractTool):
    def __init__(self):
        self.db = duckdb.connect(database=":memory:")

    def execute(self, argument: str, **kwargs) -> pd.DataFrame:
        """
        Executes a SQL query. Can optionally register new tables via kwargs["tables"].
        """
        if "tables" in kwargs:
            for name, df in kwargs["tables"].items():
                self.db.register(name, df)

        try:
            return self.db.execute(argument).fetchdf()
        except Exception as e:
            raise RuntimeError(f"SQL execution failed: {e}")

    def describe(self) -> str:
        return "Executes SQL queries over in-memory tables using DuckDB. Accepts a 'tables' argument for registering tables."
