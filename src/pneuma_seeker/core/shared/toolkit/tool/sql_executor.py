import re

import duckdb
from pandas import DataFrame

from pneuma_seeker.core.shared.toolkit.data_model import ExecutorOutput


class SQLExecutor:
    def execute_sql(
        self, sql_query: str, tables: dict[str, DataFrame]
    ) -> ExecutorOutput:
        db = duckdb.connect(database=":memory:")

        # Clear previous tables
        for table in db.execute("SHOW TABLES").fetchall():
            db.execute(f"DROP TABLE {table[0]}")

        # Register new tables
        for name, df in tables.items():
            db.register(name, df)

        try:
            fixed_sql = sql_query
            return {
                "exec_res": db.execute(fixed_sql).fetchdf(),
                "used_table_ids": self.__extract_table_ids(fixed_sql, db),
            }
        except Exception as e:
            raise RuntimeError(f"SQL execution failed: {e}")

    def __extract_table_ids(
        self, sql: str, duckdb_con=None, prefer_explain: bool = True
    ) -> list[str]:
        """
        Extract table identifiers from a SQL string.

        Strategy:
        - If a DuckDB connection is provided (or available via import) and prefer_explain=True,
        attempt to run EXPLAIN <sql> and parse table=... from the plan.
        - If EXPLAIN fails or DuckDB isn't available, fall back to a conservative regex
        that looks for names after FROM and JOIN.

        Returns:
            list[str]: unique table names in the order they appear.
        """
        if prefer_explain:
            try:
                if duckdb_con is None:
                    import duckdb

                    duckdb_con = duckdb.connect()
                rows = duckdb_con.execute(f"EXPLAIN {sql}").fetchall()
                parsed = self.__tables_from_explain_rows(rows)
                if parsed:
                    return parsed
            except Exception:
                pass

        return self.__tables_from_sql_regex(sql)

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
            r'\b(?:FROM|JOIN)\s+(?P<table>"[^"]+"|\'[^\']+\'|[A-Za-z0-9_\.]+)(?:\s+(?:AS\s+)?[A-Za-z0-9_"]|\s+ON|\s*,|\s*$)',
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
