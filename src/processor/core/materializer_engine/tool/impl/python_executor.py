from typing import Any
from processor.core.materializer_engine.tool.abstract_tool import AbstractTool


class PythonExecutor(AbstractTool):
    def execute(self, argument: str, **kwargs) -> Any:
        # Argument is the code
        local_env = {}
        exec(argument, {}, local_env)
        return local_env.get("result", None)

    def describe(self) -> str:
        return """{"name": "Python Executor", "Description": "Executes Python code to transform data", "Parameters": {"inputs": "Python code string that assigns result to 'result' variable"}}"""
