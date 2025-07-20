from enum import Enum
from typing import Any, Optional, TypedDict, get_type_hints

from pandas import DataFrame


class ToolType(Enum):
    IR_SYSTEM = "IR System"
    MATERIALIZER_ENGINE = "Materializer Engine"
    STATE_MANIPULATION = "State Manipulation"
    SQL_ENGINE = "SQL Engine"


class LLMConductorOutputType(TypedDict):
    is_direct_response: bool  # Either direct response or tool calling
    tool: Optional[str]
    response: str | dict[str, Any]


def typed_dict_to_str(typed_dict_cls: type) -> str:
    hints = get_type_hints(typed_dict_cls)
    lines = [f"{typed_dict_cls.__name__}:"]
    for key, hint in hints.items():
        lines.append(f"    {key}: {hint}")
    return "\n".join(lines)


def convert_target_schemas_to_str(target_schemas: dict[str, DataFrame]):
    representation = ""
    for table_id, table in target_schemas.items():
        representation += f"- Table {table_id}: \n```col: {" | ".join(table.columns)}"
        if len(table) > 0:
            # Sample 5 rows to represent the table
            sample_rows = table.sample(min(5, len(table)), random_state=42)
            sample_row_idx = 1
            for _, data in sample_rows.iterrows():
                str_data = [str(i) for i in data]
                representation += (
                    f"\n- Sample Row {sample_row_idx}: {" | ".join(str_data)}"
                )
                sample_row_idx += 1
        representation += "```\n"
    representation = representation.strip()
    return representation
