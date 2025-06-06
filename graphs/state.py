from typing import Any, TypedDict


class BasicState(TypedDict):
    condition: str
    response: Any
    question: str
    language: str
    llm: Any
    at: Any  # aralia tools
