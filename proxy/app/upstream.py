import os
import json
from typing import Any

import httpx
from openai import AsyncOpenAI


def _is_claude(model: str) -> bool:
    return "claude" in model.lower() or "anthropic" in os.getenv("UPSTREAM_BASE_URL", "").lower()


def _build_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url=os.getenv("UPSTREAM_BASE_URL", "https://api.anthropic.com/v1/"),
        api_key=os.getenv("UPSTREAM_API_KEY", ""),
    )


async def call_upstream(
    messages: list[dict],
    tools: list[dict] | None,
    model: str | None = None,
    extra_headers: dict | None = None,
) -> dict[str, Any]:
    client = _build_client()
    model = model or os.getenv("UPSTREAM_MODEL", "claude-haiku-5-5")

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": int(os.getenv("MAX_TOKENS", "1024")),
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    # Claude rejects temperature < 1 and seed — only send temperature to non-Claude models
    if not _is_claude(model):
        kwargs["temperature"] = 0

    # Claude requires n=1
    kwargs["n"] = 1

    headers = extra_headers or {}
    # Anthropic OpenAI-compat endpoint requires this header
    if _is_claude(model):
        headers.setdefault("anthropic-version", "2023-06-01")

    response = await client.chat.completions.create(
        **kwargs,
        extra_headers=headers if headers else None,
    )
    return response.model_dump()
