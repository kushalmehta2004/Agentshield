import os
from typing import Any

from openai import AsyncOpenAI


def _is_claude(model: str) -> bool:
    return "claude" in model.lower() or "anthropic" in os.getenv("UPSTREAM_BASE_URL", "").lower()


def _get_route(model: str) -> tuple[str, str]:
    """Return (base_url, api_key) for the given model name.

    Checks policy.yaml model_routes first; falls back to UPSTREAM_* env vars.
    Shield re-runs always call this with the upstream model, so they always go
    to Claude regardless of AGENT_MODEL.
    """
    from app.policy import get_policy
    routes = get_policy().get("model_routes", {})
    if model in routes:
        spec = routes[model]
        base_url = os.getenv(spec["base_url_env"], "")
        api_key = os.getenv(spec["api_key_env"], "")
        if base_url and api_key:
            return base_url, api_key
    # Default: use UPSTREAM_* (Claude)
    return (
        os.getenv("UPSTREAM_BASE_URL", "https://api.anthropic.com/v1/"),
        os.getenv("UPSTREAM_API_KEY", ""),
    )


def _build_client(base_url: str, api_key: str) -> AsyncOpenAI:
    return AsyncOpenAI(base_url=base_url, api_key=api_key)


async def call_upstream(
    messages: list[dict],
    tools: list[dict] | None,
    model: str | None = None,
    extra_headers: dict | None = None,
    force_upstream: bool = False,
) -> dict[str, Any]:
    """Call the appropriate upstream LLM.

    force_upstream=True bypasses model_routes and always goes to UPSTREAM_* (Claude).
    Used by the PoC engine re-runs so the shield always uses Claude.
    """
    model = model or os.getenv("UPSTREAM_MODEL", "claude-haiku-5-5")

    if force_upstream:
        base_url = os.getenv("UPSTREAM_BASE_URL", "https://api.anthropic.com/v1/")
        api_key = os.getenv("UPSTREAM_API_KEY", "")
    else:
        base_url, api_key = _get_route(model)

    # Determine actual model: if routed to a non-Claude upstream, use as-is;
    # for the shield re-runs forced to Claude, use UPSTREAM_MODEL
    if force_upstream:
        actual_model = os.getenv("UPSTREAM_MODEL", "claude-haiku-5-5")
    else:
        actual_model = model

    client = _build_client(base_url, api_key)
    is_claude = _is_claude(actual_model) or "anthropic" in base_url.lower()

    kwargs: dict[str, Any] = {
        "model": actual_model,
        "messages": messages,
        "max_tokens": int(os.getenv("MAX_TOKENS", "1024")),
        "n": 1,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    # Claude rejects temperature < 1 and seed
    if not is_claude:
        kwargs["temperature"] = 0

    headers = extra_headers or {}
    if is_claude:
        headers.setdefault("anthropic-version", "2023-06-01")

    response = await client.chat.completions.create(
        **kwargs,
        extra_headers=headers if headers else None,
    )
    return response.model_dump()
