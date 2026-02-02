import re
from typing import Any

import duckdb
from pandas import DataFrame

from pneuma_seeker.services.core.actions.action_names import ActionNames
from pneuma_seeker.services.core.actions.interfaces.action import Action
from pneuma_seeker.services.core.actions.interfaces.executable import Executable


class SQLExecutor(Action, Executable):
    def get_name(self) -> str:
        return ActionNames.SQL_EXECUTOR.value

    def get_description(self) -> str:
        """Returns the description of the tool."""
        return "Executes SQL queries on provided pandas DataFrames using DuckDB, returning results and tracking used tables."

    def get_input_schema(self) -> dict[str, str]:
        return {
            "sql_query": "A string containing the SQL query to execute.",
            "tables": "A dictionary mapping table names to pandas DataFrames to be used in the SQL query.",
        }

    def get_notes(self) -> str:
        return "The SQL query will be executed using DuckDB in an in-memory database."

    def execute(self, input: dict[str, Any]) -> DataFrame:
        sql_query = input.get("sql_query")
        tables = input.get("tables", {})

        if not isinstance(sql_query, str):
            raise ValueError("Input 'sql_query' must be a string.")
        if not isinstance(tables, dict) or not all(
            isinstance(v, DataFrame) for v in tables.values()
        ):
            raise ValueError("Input 'tables' must be a dictionary of DataFrames.")

        with duckdb.connect(database=":memory:") as con:
            for table_name, df in tables.items():
                con.register(table_name, df)
            result_df = con.execute(sql_query).fetchdf()
        return result_df

    def extract_table_ids(
        self, sql: str, prefer_explain: bool = False
    ) -> list[str]:
        """
        Extract table identifiers from a SQL string.

        Strategy:
        - Use regex to parse table names from FROM and JOIN clauses.
        - If prefer_explain=True, also attempt to run EXPLAIN <sql> and merge results.

        Returns:
            list[str]: unique table names in the order they appear.
        """
        # Always get regex results as the baseline
        regex_tables = self.__tables_from_sql_regex(sql)
        
        if prefer_explain:
            try:
                rows = duckdb.connect().execute(f"EXPLAIN {sql}").fetchall()
                explain_tables = self.__tables_from_explain_rows(rows)
                # Merge both results, preserving order and uniqueness
                if explain_tables:
                    seen = set()
                    merged = []
                    for t in regex_tables + explain_tables:
                        if t not in seen:
                            seen.add(t)
                            merged.append(t)
                    return merged
            except Exception:
                pass

        return regex_tables

    def __tables_from_explain_rows(self, rows: list[tuple]) -> list[str]:
        """Parses common DuckDB plan lines to extract table names."""
        tables = []
        pattern = re.compile(
            r'table\s*=\s*(?P<table>"[^"]+"|\'[^\']+\'|[^,)\s]+)', re.IGNORECASE
        )
        for row in rows:
            if not row:
                continue
            text = row[0] if isinstance(row, (list, tuple)) else str(row)
            for m in pattern.finditer(text):
                name = self.__clean_table_name(m.group("table"))
                if name and name.lower() not in ("<none>",):
                    tables.append(name)
        seen = set()
        return [t for t in tables if not (t in seen or seen.add(t))]

    def __tables_from_sql_regex(self, sql: str) -> list[str]:
        """Conservative regex to pull names after FROM / JOIN (handles schema.table and quoted IDs)."""
        pattern = re.compile(
            r'\b(?:FROM|JOIN|LEFT\s+JOIN|RIGHT\s+JOIN|INNER\s+JOIN|OUTER\s+JOIN|CROSS\s+JOIN|FULL\s+JOIN)\s+(?P<table>"[^"]+"|\'[^\']+\'|[A-Za-z0-9_\.]+)',
            re.IGNORECASE,
        )
        tables = []
        for m in pattern.finditer(sql):
            name = self.__clean_table_name(m.group("table"))
            if name:
                tables.append(name)
        seen = set()
        return [t for t in tables if not (t in seen or seen.add(t))]

    def __clean_table_name(self, raw: str) -> str:
        """Removes surrounding quotes and whitespace."""
        raw = raw.strip()
        if (raw.startswith('"') and raw.endswith('"')) or (
            raw.startswith("'") and raw.endswith("'")
        ):
            raw = raw[1:-1]
        return raw
