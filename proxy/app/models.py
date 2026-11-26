from typing import Any
from pydantic import BaseModel


class Message(BaseModel):
    role: str
    content: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    name: str | None = None


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[Message]
    tools: list[dict[str, Any]] | None = None
    tool_choice: Any | None = None
    stream: bool | None = False
    max_tokens: int | None = None
    temperature: float | None = None
    n: int | None = 1

    model_config = {"extra": "allow"}
