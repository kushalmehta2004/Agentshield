"""Deterministic fake LLM for unit tests.

Usage:
    monkeypatch.setattr("app.upstream.call_upstream", make_fake(responses))
"""
import json
from typing import Any


def make_response(
    content: str | None = None,
    tool_calls: list[dict] | None = None,
    finish_reason: str = "stop",
) -> dict:
    msg: dict[str, Any] = {"role": "assistant", "content": content}
    if tool_calls:
        msg["tool_calls"] = tool_calls
        finish_reason = "tool_calls"
    return {
        "id": "fake-id",
        "object": "chat.completion",
        "model": "fake-model",
        "choices": [
            {
                "index": 0,
                "message": msg,
                "finish_reason": finish_reason,
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


def make_tool_call(name: str, args: dict, call_id: str = "call_1") -> dict:
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(args)},
    }


def make_fake(response: dict):
    """Return an async callable that always returns `response`."""
    async def _fake(**kwargs):
        return response
    return _fake


def make_fake_sequence(responses: list[dict]):
    """Return an async callable that returns responses in sequence."""
    it = iter(responses)
    async def _fake(**kwargs):
        return next(it)
    return _fake
