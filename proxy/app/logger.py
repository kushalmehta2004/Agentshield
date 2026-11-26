import asyncio
import json
import logging
import os
from typing import Any

from supabase import create_client, Client

log = logging.getLogger("agentshield.logger")

_client: Client | None = None


def _get_client() -> Client | None:
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_SERVICE_KEY", "")
        if url and key:
            _client = create_client(url, key)
    return _client


def _fire(coro) -> None:
    """Schedule a coroutine as a background task; never raises."""
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(coro)
    except Exception:
        pass


async def _safe(coro) -> None:
    try:
        await coro
    except Exception as e:
        log.warning("Supabase log error: %s", e)


async def _upsert_session(session_id: str, scenario: str | None, mode: str) -> None:
    client = _get_client()
    if not client:
        return
    await asyncio.to_thread(
        client.table("sessions").upsert({
            "id": session_id,
            "scenario": scenario,
            "mode": mode,
            "status": "running",
        }).execute
    )


async def _insert_llm_call(
    session_id: str,
    request_messages: list[dict],
    response: dict,
    latency_ms: int,
) -> str | None:
    client = _get_client()
    if not client:
        return None
    result = await asyncio.to_thread(
        client.table("llm_calls").insert({
            "session_id": session_id,
            "request_messages": request_messages,
            "response": response,
            "latency_ms": latency_ms,
        }).execute
    )
    return result.data[0]["id"] if result.data else None


async def _insert_tool_calls(
    session_id: str,
    llm_call_id: str,
    tool_calls: list[dict],
    sensitive_tool_names: set[str],
) -> list[str]:
    client = _get_client()
    if not client or not tool_calls:
        return []
    rows = [
        {
            "session_id": session_id,
            "llm_call_id": llm_call_id,
            "tool_name": tc["function"]["name"],
            "args": json.loads(tc["function"].get("arguments", "{}")),
            "is_sensitive": tc["function"]["name"] in sensitive_tool_names,
        }
        for tc in tool_calls
    ]
    result = await asyncio.to_thread(
        client.table("tool_calls").insert(rows).execute
    )
    return [r["id"] for r in (result.data or [])]


async def _insert_verdict(verdict_data: dict) -> None:
    client = _get_client()
    if not client:
        return
    await asyncio.to_thread(
        client.table("verdicts").insert(verdict_data).execute
    )


async def _update_session_status(session_id: str, status: str) -> None:
    client = _get_client()
    if not client:
        return
    await asyncio.to_thread(
        client.table("sessions").update({"status": status}).eq("id", session_id).execute
    )


async def _insert_outbox(session_id: str, kind: str, payload: dict) -> None:
    client = _get_client()
    if not client:
        return
    await asyncio.to_thread(
        client.table("outbox").insert({
            "session_id": session_id,
            "kind": kind,
            "payload": payload,
        }).execute
    )


# Public fire-and-forget helpers

def log_session(session_id: str, scenario: str | None, mode: str) -> None:
    _fire(_safe(_upsert_session(session_id, scenario, mode)))


def log_llm_call(
    session_id: str,
    request_messages: list[dict],
    response: dict,
    latency_ms: int,
    sensitive_tool_names: set[str] | None = None,
) -> asyncio.Task | None:
    """Returns the task so callers can await if they need the llm_call_id."""
    async def _run():
        llm_call_id = await _upsert_session.__wrapped__ if False else None
        llm_call_id = await _insert_llm_call(session_id, request_messages, response, latency_ms)
        if llm_call_id and sensitive_tool_names is not None:
            tcs = []
            for choice in response.get("choices", []):
                tcs += choice.get("message", {}).get("tool_calls") or []
            await _insert_tool_calls(session_id, llm_call_id, tcs, sensitive_tool_names)
        return llm_call_id

    try:
        loop = asyncio.get_event_loop()
        return loop.create_task(_safe(_run()))
    except Exception:
        return None


def log_verdict(verdict_data: dict) -> None:
    _fire(_safe(_insert_verdict(verdict_data)))


def log_session_status(session_id: str, status: str) -> None:
    _fire(_safe(_update_session_status(session_id, status)))


def log_outbox(session_id: str, kind: str, payload: dict) -> None:
    _fire(_safe(_insert_outbox(session_id, kind, payload)))
