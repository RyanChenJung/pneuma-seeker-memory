from typing import Any
from processor.core.materializer_engine.tool.abstract_tool import AbstractTool


class PythonExecutor(AbstractTool):
    def execute(self, argument: str, **kwargs) -> Any:
        # Argument is the code
        local_env = {}
        exec(argument, {}, local_env)
        return local_env.get("result", None)

    def describe(self) -> str:
        return "Executes Python code string. The code must assign final output to variable named `result`."
