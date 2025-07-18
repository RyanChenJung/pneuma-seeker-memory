from enum import Enum
from typing import TypedDict


class Role(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class LLMMessage(TypedDict):
    role: str
    content: str
