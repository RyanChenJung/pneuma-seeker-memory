import ast
import re
import numpy as np
import pandas as pd

from logging import Logger

from pneuma_seeker.core.ir_system.data_model import AbstractDocument
from pneuma_seeker.core.materializer.data_model import ExecutorOutput
from pneuma_seeker.provenance.graph import ProvenanceGraph


class PythonExecutor:
    def __init__(self, logger: Logger, prov_graph: ProvenanceGraph) -> None:
        self.logger = logger
        self.prov_graph = prov_graph

    def execute_code(
        self,
        tables: dict[str, pd.DataFrame],
        code: str,
    ) -> ExecutorOutput:
        self.logger.info(f"Executing this Python code: {code}")
        try:
            env = dict()
            env["tables"] = tables
            exec(code, {"pd": pd, "np": np, "re": re}, env)
        except Exception as e:
            return {"exec_res": e, "used_table_ids": []}
        return {
            "exec_res": env.get("result", None),
            "used_table_ids": self.__extract_table_ids(code),
        }

    def __extract_table_ids(self, code: str):
        tree = ast.parse(code)
        ids = []

        class TableVisitor(ast.NodeVisitor):
            def visit_Subscript(self, node):
                # Check if it's "tables[...]"
                if isinstance(node.value, ast.Name) and node.value.id == "tables":
                    # Extract key inside tables["..."]
                    if isinstance(node.slice, ast.Constant) and isinstance(
                        node.slice.value, str
                    ):
                        ids.append(node.slice.value)
                self.generic_visit(node)

        TableVisitor().visit(tree)
        return ids

    def generate_pandas_read_code(self, doc: AbstractDocument):
        doc_var_name = re.sub(r"\W|^(?=\d)", "_", doc.doc_id or "var")
        doc_path = doc.path or "<no_path_provided>"
        return f"""import pandas as pd
{doc_var_name} = pd.read_csv(r"{doc_path}")"""

    def generate_view_textual_document_code(self, doc: AbstractDocument):
        doc_var_name = re.sub(r"\W|^(?=\d)", "_", doc.doc_id or "var")
        return f"""{doc_var_name} = "{doc.content}" """.strip()

    def generate_pandas_read_multi_doc_code(self, docs: list[AbstractDocument]):
        python_code_lines = ["import pandas as pd"]
        for doc in docs:
            doc_var_name = re.sub(r"\W|^(?=\d)", "_", doc.doc_id or "var")
            doc_path = doc.path or "<no_path_provided>"
            python_code_lines.append(f"""{doc_var_name} = pd.read_csv(r"{doc_path}")""")
        return "\n".join(python_code_lines)

    def generate_table_select_code(
        self, target_var_name: str, source_id: str, relevant_cols: list[str]
    ):
        # source_var_name represents a DataFrame object
        source_var_name = re.sub(r"\W|^(?=\d)", "_", source_id or "var")
        return f"""{target_var_name} = {source_var_name}[{repr(relevant_cols)}]"""

    def generate_semantic_col_generator_code(
        self, conditioned_cols: list[str], doc: AbstractDocument, new_col_name: str, path: str
    ):
        doc_var_name = re.sub(r"\W|^(?=\d)", "_", doc.doc_id or "var")
        return f"""# Semantically generate new column `{new_col_name}` for the table {doc_var_name}, conditioned on these columns: {conditioned_cols}
# => Table path: {path}
"""

    def generate_semantic_join_generator_code(
        self,
        doc_1: AbstractDocument,
        doc_2: AbstractDocument,
        relevant_left_cols: list[str],
        relevant_right_cols: list[str],
        top_k: int,
        path: str,
    ):
        left_doc_var_name = re.sub(r"\W|^(?=\d)", "_", doc_1.doc_id or "var")
        right_doc_var_name = re.sub(r"\W|^(?=\d)", "_", doc_2.doc_id or "var")

        return f"""# Semantically join two tables, A ({left_doc_var_name}) and B ({right_doc_var_name}), and keep the top-{top_k} join candidates for each row in the smaller table
# => Relevant columns in A: {relevant_left_cols}
# => Relevant columns in B: {relevant_right_cols}
# => Resulting table path: {path}
"""
    
    def generate_sql_executor_code(
        self,
        sql_query: str,
        id_dfs: dict[str, pd.DataFrame],
        path: str,
    ):
        dict_entries = []
        for key in id_dfs:
            dict_entries.append(f'"{key}": {key}')
        dict_code = "{\n    " + ",\n    ".join(dict_entries) + "\n}"

        return f"""from typing import Any, TypedDict
import re

import duckdb
from pandas import DataFrame


class ExecutorOutput(TypedDict):
    exec_res: Any
    used_table_ids: list[str]


class SQLExecutor:
    def execute_sql(
        self, sql_query: str, tables: dict[str, DataFrame]
    ) -> ExecutorOutput:
        db = duckdb.connect(database=":memory:")

        # Clear previous tables
        for table in db.execute("SHOW TABLES").fetchall():
            db.execute(f"DROP TABLE {{table[0]}}")

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
            raise RuntimeError(f"SQL execution failed: {{e}}")

    def __extract_table_ids(
        self, sql: str, duckdb_con=None, prefer_explain: bool = True
    ) -> list[str]:
        \"""
        Extract table identifiers from a SQL string.

        Strategy:
        - If a DuckDB connection is provided (or available via import) and prefer_explain=True,
        attempt to run EXPLAIN <sql> and parse table=... from the plan.
        - If EXPLAIN fails or DuckDB isn't available, fall back to a conservative regex
        that looks for names after FROM and JOIN.

        Returns:
            list[str]: unique table names in the order they appear.
        \"""
        if prefer_explain:
            try:
                if duckdb_con is None:
                    import duckdb

                    duckdb_con = duckdb.connect()
                rows = duckdb_con.execute(f"EXPLAIN {{sql}}").fetchall()
                parsed = self.__tables_from_explain_rows(rows)
                if parsed:
                    return parsed
            except Exception:
                pass

        return self.__tables_from_sql_regex(sql)

    def __tables_from_explain_rows(self, rows: list[tuple]) -> list[str]:
        \"""Parses common DuckDB plan lines to extract table names.\"""
        tables = []
        pattern = re.compile(
            r'table\\s*=\\s*(?P<table>"[^"]+"|\'[^\']+\'|[^,)\\s]+)', re.IGNORECASE
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
        \"""Conservative regex to pull names after FROM / JOIN (handles schema.table and quoted IDs).\"""
        pattern = re.compile(
            r'\b(?:FROM|JOIN)\\s+(?P<table>"[^"]+"|\'[^\']+\'|[A-Za-z0-9_\\.]+)(?:\\s+(?:AS\\s+)?[A-Za-z0-9_"]|\\s+ON|\\s*,|\\s*$)',
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
        \"""Removes surrounding quotes and whitespace.\"""
        raw = raw.strip()
        if (raw.startswith('"') and raw.endswith('"')) or (
            raw.startswith("'") and raw.endswith("'")
        ):
            raw = raw[1:-1]
        return raw

sql_executor = SQLExecutor()
sql_executor.execute_sql(
    {sql_query}, {dict_code}
)  # Path: {path}
"""
    
    def append_comment_to_existing_code(self, code: str, comment: str):
        return f"{comment}\n{code}"
