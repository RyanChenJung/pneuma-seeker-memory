from typing import TypedDict


class LLMMessage(TypedDict):
    role: str
    content: str
