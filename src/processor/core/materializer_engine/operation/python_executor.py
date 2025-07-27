from typing import Optional
import numpy as np
import pandas as pd

from logging import Logger


def execute_python_code(
    python_code: str,
    tables: dict[str, pd.DataFrame],
    logger: Optional[Logger] = None,
):
    if logger is not None:
        logger.info(f"Executing this Python code: {python_code}")
    env = dict()
    env['tables'] = tables
    exec(python_code, {"pd": pd, "np": np}, env)
    return env.get("result", None)


if __name__ == "__main__":
    tables = {
        "table_1": pd.DataFrame(columns=["col_1", "col_2"])
    }
    python_code = """result = tables["table_1"].describe()"""
    result = execute_python_code(python_code, tables)
    print(result)
