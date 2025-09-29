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
