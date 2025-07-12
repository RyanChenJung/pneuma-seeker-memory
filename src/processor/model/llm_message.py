from enum import Enum
from typing import TypedDict


class Role(Enum):
    USER = "user"
    ASSISTANT = "assistant"


class LLMMessage(TypedDict):
    role: Role
    content: str
