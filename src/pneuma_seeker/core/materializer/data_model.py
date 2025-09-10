from typing import Any, TypedDict


class ExecutorOutput(TypedDict):
    exec_res: Any
    used_table_ids: list[str]
