import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.fake_upstream import make_fake, make_response, make_tool_call

client = TestClient(app)


def _post(body: dict, headers: dict | None = None):
    return client.post("/v1/chat/completions", json=body, headers=headers or {})


SIMPLE_REQ = {
    "model": "claude-haiku-5-5",
    "messages": [{"role": "user", "content": "Hello"}],
}


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_stream_rejected():
    r = _post({**SIMPLE_REQ, "stream": True})
    assert r.status_code == 400
    assert "stream" in r.json()["detail"].lower()


def test_passthrough_returns_tool_calls(monkeypatch):
    tc = make_tool_call("web_fetch", {"url": "http://example.com"})
    fake_resp = make_response(tool_calls=[tc])
    monkeypatch.setattr("app.routes.chat.call_upstream", make_fake(fake_resp))
    monkeypatch.setattr("app.routes.chat.db.log_session", lambda *a, **kw: None)
    monkeypatch.setattr("app.routes.chat.db.log_llm_call", lambda *a, **kw: None)
    monkeypatch.setattr("app.routes.chat.db.log_session_status", lambda *a, **kw: None)

    r = _post(SIMPLE_REQ)
    assert r.status_code == 200
    data = r.json()
    tcs = data["choices"][0]["message"]["tool_calls"]
    assert len(tcs) == 1
    assert tcs[0]["function"]["name"] == "web_fetch"


def test_session_header_respected(monkeypatch):
    fake_resp = make_response(content="hi")
    monkeypatch.setattr("app.routes.chat.call_upstream", make_fake(fake_resp))
    monkeypatch.setattr("app.routes.chat.db.log_session", lambda *a, **kw: None)
    monkeypatch.setattr("app.routes.chat.db.log_llm_call", lambda *a, **kw: None)
    monkeypatch.setattr("app.routes.chat.db.log_session_status", lambda *a, **kw: None)

    r = _post(SIMPLE_REQ, headers={"X-AgentShield-Session": "sess-abc"})
    assert r.status_code == 200
    assert r.json()["agentshield_session_id"] == "sess-abc"


def test_mode_header_off(monkeypatch):
    fake_resp = make_response(content="hi")
    monkeypatch.setattr("app.routes.chat.call_upstream", make_fake(fake_resp))
    monkeypatch.setattr("app.routes.chat.db.log_session", lambda *a, **kw: None)
    monkeypatch.setattr("app.routes.chat.db.log_llm_call", lambda *a, **kw: None)
    monkeypatch.setattr("app.routes.chat.db.log_session_status", lambda *a, **kw: None)

    r = _post(SIMPLE_REQ, headers={"X-AgentShield-Mode": "off"})
    assert r.status_code == 200
    assert r.json()["agentshield_mode"] == "off"


def test_mode_header_invalid_defaults_to_shield(monkeypatch):
    fake_resp = make_response(content="hi")
    monkeypatch.setattr("app.routes.chat.call_upstream", make_fake(fake_resp))
    monkeypatch.setattr("app.routes.chat.db.log_session", lambda *a, **kw: None)
    monkeypatch.setattr("app.routes.chat.db.log_llm_call", lambda *a, **kw: None)
    monkeypatch.setattr("app.routes.chat.db.log_session_status", lambda *a, **kw: None)

    r = _post(SIMPLE_REQ, headers={"X-AgentShield-Mode": "badvalue"})
    assert r.status_code == 200
    assert r.json()["agentshield_mode"] == "shield"
