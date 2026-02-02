import ast
import re
from typing import Any

import duckdb
import numpy as np
import pandas as pd
import scipy

from pneuma_seeker.services.core.actions.action_names import ActionNames
from pneuma_seeker.services.core.actions.interfaces.action import Action
from pneuma_seeker.services.core.actions.interfaces.executable import Executable


class PythonExecutor(Action, Executable):
    """
    Executes Python code snippets within a controlled environment,
    tracking used tables and integrating with the provenance graph.
    """

    def get_name(self) -> str:
        """Returns the name of the tool."""
        return ActionNames.PYTHON_EXECUTOR.value

    def get_description(self) -> str:
        """Returns the description of the tool."""
        return """Executes Python code snippets with access to pandas, numpy, duckdb, and scipy, returning results (DataFrame) and tracking used tables."""

    def get_input_schema(self) -> dict[str, str]:
        """Returns the input schema of the tool."""
        return {
            "tables": "A dictionary mapping table IDs to pandas DataFrames.",
            "code": "A string containing the Python code to execute. The code should use the 'tables' dictionary to access DataFrames and must set a variable 'result' as the output DataFrame.",
        }

    def get_notes(self) -> str:
        """Returns additional notes about the tool."""
        return "The executed code must define a variable 'result' containing the output DataFrame."

    def execute(
        self,
        input: dict[str, Any],
    ) -> pd.DataFrame:
        """Executes the tool with the given input and returns the output."""
        tables = input.get("tables", {})
        code = input.get("code")
        if not isinstance(tables, dict) or not all(
            isinstance(v, pd.DataFrame) for v in tables.values()
        ):
            raise ValueError("Input 'tables' must be a dictionary of DataFrames.")
        if not isinstance(code, str):
            raise ValueError("Input 'code' must be a string.")

        env = {
            "pd": pd,
            "np": np,
            "re": re,
            "tables": tables,
            "duckdb": duckdb,
            "scipy": scipy,
        }
        exec(code, env)

        if "result" not in env:
            raise ValueError("Executed code did not set a 'result' variable.")
        if not isinstance(env.get("result"), pd.DataFrame):
            raise ValueError("The 'result' variable must be a pandas DataFrame.")

        return env["result"]

    def extract_table_ids(self, code: str) -> list[str]:
        """Extracts table IDs accessed in the code by parsing 'tables[...]' subscripts."""
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
