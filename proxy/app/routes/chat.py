import json
import time
import uuid
import logging
from typing import Any

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from app.models import ChatCompletionRequest
from app.upstream import call_upstream
from app.policy import is_sensitive, get_target_args
from app import logger as db

log = logging.getLogger("agentshield.chat")

router = APIRouter()


def _extract_tool_calls(response: dict) -> list[dict]:
    tcs = []
    for choice in response.get("choices", []):
        tcs += choice.get("message", {}).get("tool_calls") or []
    return tcs


def _sensitive_tools_in_response(response: dict) -> set[str]:
    names = set()
    for tc in _extract_tool_calls(response):
        name = tc["function"]["name"]
        try:
            args = json.loads(tc["function"].get("arguments", "{}"))
        except Exception:
            args = {}
        if is_sensitive(name, args):
            names.add(name)
    return names


@router.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()

    # Reject streaming
    if body.get("stream"):
        raise HTTPException(status_code=400, detail="AgentShield does not support stream=true in v1.")

    try:
        req = ChatCompletionRequest(**body)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Session and mode from headers
    session_id = request.headers.get("X-AgentShield-Session") or str(uuid.uuid4())
    mode = request.headers.get("X-AgentShield-Mode", "shield").lower()
    if mode not in ("off", "regex", "shield"):
        mode = "shield"
    scenario = request.headers.get("X-AgentShield-Scenario")

    db.log_session(session_id, scenario, mode)

    # Build messages for upstream (strip our custom fields pydantic added)
    messages = [m.model_dump(exclude_none=True) for m in req.messages]

    t0 = time.monotonic()
    response = await call_upstream(
        messages=messages,
        tools=req.tools,
        model=req.model,
    )
    latency_ms = int((time.monotonic() - t0) * 1000)

    sensitive_names = _sensitive_tools_in_response(response)
    db.log_llm_call(session_id, messages, response, latency_ms, sensitive_names)

    # In Phase 1, mode=off and passthrough only. Shield/regex wired in Phase 3.
    if mode != "off" and sensitive_names:
        log.info(
            "session=%s mode=%s sensitive_tools=%s — shield/regex wired in Phase 3",
            session_id, mode, sensitive_names,
        )

    # Add session_id to response so caller can track it
    response["agentshield_session_id"] = session_id
    response["agentshield_mode"] = mode

    db.log_session_status(session_id, "allowed")

    return JSONResponse(content=response)


@router.get("/v1/models")
async def list_models():
    return {"object": "list", "data": [{"id": "claude-haiku-5-5", "object": "model"}]}
