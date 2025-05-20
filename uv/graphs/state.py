from operator import add
from typing import Any, Dict, TypedDict, Annotated


class BasicState(TypedDict):
    condition: str
    response: Any
    question: str
    language: str
    llm: Any
    at: Any  # aralia tools
