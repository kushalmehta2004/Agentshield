import json
import time
import uuid
import logging
from typing import Any

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from app.models import ChatCompletionRequest
from app.upstream import call_upstream
from app.policy import is_sensitive, get_target_args, get_policy
from app import logger as db
from app.regex_baseline import check_messages
from app import poc_engine

log = logging.getLogger("agentshield.chat")

router = APIRouter()


def _extract_tool_calls(response: dict) -> list[dict]:
    tcs = []
    for choice in response.get("choices", []):
        tcs += choice.get("message", {}).get("tool_calls") or []
    return tcs


def _first_sensitive_tc(response: dict) -> dict | None:
    for tc in _extract_tool_calls(response):
        name = tc["function"]["name"]
        try:
            args = json.loads(tc["function"].get("arguments", "{}"))
        except Exception:
            args = {}
        if is_sensitive(name, args):
            return tc
    return None


def _sensitive_names(response: dict) -> set[str]:
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


def _blocked_response(session_id: str, mode: str, sc: dict, verdict_data: dict, proxy_url: str) -> dict:
    name = sc["function"]["name"]
    try:
        args = json.loads(sc["function"].get("arguments", "{}"))
    except Exception:
        args = {}
    target_args = get_target_args(name)
    target_summary = ", ".join(f"{k}={args.get(k, '?')}" for k in target_args)
    cause_label = "untrusted content"
    if verdict_data.get("causes"):
        c = verdict_data["causes"][0]
        cause_label = c.get("source_label", "untrusted content")
        if c.get("chunk_index") is not None:
            cause_label += f" (paragraph {c['chunk_index'] + 1})"
    msg = (
        f"[AgentShield] Blocked {name}({target_summary}): "
        f"triggered by {cause_label}. "
        f"See dashboard: {proxy_url}"
    )
    return {
        "id": f"agentshield-blocked-{uuid.uuid4()}",
        "object": "chat.completion",
        "model": "agentshield",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": msg, "tool_calls": None},
            "finish_reason": "stop",
        }],
        "agentshield_session_id": session_id,
        "agentshield_mode": mode,
        "agentshield_blocked": True,
        "agentshield_verdict": verdict_data,
    }


@router.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()

    if body.get("stream"):
        raise HTTPException(status_code=400, detail="AgentShield does not support stream=true in v1.")

    try:
        req = ChatCompletionRequest(**body)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    session_id = request.headers.get("X-AgentShield-Session") or str(uuid.uuid4())
    mode = request.headers.get("X-AgentShield-Mode", "shield").lower()
    if mode not in ("off", "regex", "shield"):
        mode = "shield"
    scenario = request.headers.get("X-AgentShield-Scenario")

    db.log_session(session_id, scenario, mode)

    messages = [m.model_dump(exclude_none=True) for m in req.messages]

    t0 = time.monotonic()
    response = await call_upstream(messages=messages, tools=req.tools, model=req.model)
    latency_ms = int((time.monotonic() - t0) * 1000)

    sensitive_names = _sensitive_names(response)
    db.log_llm_call(session_id, messages, response, latency_ms, sensitive_names)

    proxy_url = get_policy().get("proxy_public_url", "http://localhost:8000")
    import os
    proxy_url = os.getenv("PROXY_PUBLIC_URL", proxy_url)

    # --- mode=off: passthrough ---
    if mode == "off" or not sensitive_names:
        response["agentshield_session_id"] = session_id
        response["agentshield_mode"] = mode
        db.log_session_status(session_id, "allowed")
        return JSONResponse(content=response)

    sc = _first_sensitive_tc(response)
    if sc is None:
        response["agentshield_session_id"] = session_id
        response["agentshield_mode"] = mode
        db.log_session_status(session_id, "allowed")
        return JSONResponse(content=response)

    # --- mode=regex: simple pattern baseline ---
    if mode == "regex":
        blocked = check_messages(messages)
        verdict_data = {
            "decision": "BLOCK" if blocked else "ALLOW",
            "attack_detected": blocked,
            "unstable": False,
            "causes": [],
            "reruns": [],
            "latency_ms": latency_ms,
        }
        db.log_verdict({
            "session_id": session_id,
            "mode": mode,
            **verdict_data,
        })
        if blocked:
            log.info("BLOCK (regex) %s session=%s", sc["function"]["name"], session_id)
            db.log_session_status(session_id, "blocked")
            return JSONResponse(content=_blocked_response(session_id, mode, sc, verdict_data, proxy_url))
        response["agentshield_session_id"] = session_id
        response["agentshield_mode"] = mode
        db.log_session_status(session_id, "allowed")
        return JSONResponse(content=response)

    # --- mode=shield: Proof of Cause ---
    verdict = await poc_engine.run(
        messages=messages,
        tools=req.tools,
        model=req.model,
        sc=sc,
        session_id=session_id,
    )
    verdict_data = verdict.to_dict()
    db.log_verdict({
        "session_id": session_id,
        "mode": mode,
        **verdict_data,
    })

    final_status = verdict.decision.lower() if verdict.decision in ("BLOCK", "WARN") else "allowed"
    if verdict.decision == "BLOCK":
        db.log_session_status(session_id, "blocked")
        return JSONResponse(content=_blocked_response(session_id, mode, sc, verdict_data, proxy_url))
    elif verdict.decision == "WARN":
        db.log_session_status(session_id, "warn")
    else:
        db.log_session_status(session_id, "allowed")

    response["agentshield_session_id"] = session_id
    response["agentshield_mode"] = mode
    response["agentshield_verdict"] = verdict_data
    return JSONResponse(content=response)


@router.get("/v1/models")
async def list_models():
    return {"object": "list", "data": [{"id": "claude-haiku-5-5", "object": "model"}]}
