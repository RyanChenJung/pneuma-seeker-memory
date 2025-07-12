from enum import Enum
from typing import Optional, TypedDict, get_type_hints


class ToolType(Enum):
    IR_SYSTEM = "IR System"
    MATERIALIZER_ENGINE = "Materializer Engine"
    STATE_MANIPULATION = "State Manipulation"


class LLMConductorOutputType(TypedDict):
    is_direct_response: bool  # Either direct response or tool calling
    direct_response: Optional[str]
    tool: Optional[ToolType]


class IRSystemToolCallingType(LLMConductorOutputType):
    prompt: str


class StateManipulationToolCallingType(LLMConductorOutputType):
    new_sqls: list[str]
    new_target_schemas: list[str]


def typed_dict_to_str(typed_dict_cls: type) -> str:
    hints = get_type_hints(typed_dict_cls)
    lines = [f"{typed_dict_cls.__name__}:"]
    for key, hint in hints.items():
        lines.append(f"    {key}: {hint}")
    return "\n".join(lines)
