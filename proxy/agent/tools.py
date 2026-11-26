"""Agent tool implementations with sandboxing.

web_fetch   — only fetches from the demo site (allowlisted)
read_file   — confined to agent/sandbox/
send_email  — fake: writes to Supabase outbox
http_post   — fake: writes to Supabase outbox
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

import httpx

SANDBOX_DIR = Path(__file__).parent / "sandbox"
PROXY_URL = os.getenv("PROXY_PUBLIC_URL", "http://localhost:8000")
ALLOWED_HOST = os.getenv("DEMO_HOST", f"localhost:8000")


def _allowlisted(url: str) -> bool:
    return ALLOWED_HOST in url or "localhost:8000" in url or "127.0.0.1:8000" in url


def web_fetch(url: str) -> str:
    if not _allowlisted(url):
        return f"[BLOCKED] web_fetch is restricted to the demo site. Attempted: {url}"
    try:
        resp = httpx.get(url, timeout=10)
        resp.raise_for_status()
        # Strip HTML tags for readability; keep HTML comments as text
        import re
        text = resp.text
        # Expose HTML comments as plain text so agents see them
        text = re.sub(r"<!--(.*?)-->", r"\1", text, flags=re.DOTALL)
        # Strip remaining tags
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s{2,}", "\n", text).strip()
        return text
    except Exception as e:
        return f"[ERROR] web_fetch failed: {e}"


def read_file(path: str) -> str:
    target = (SANDBOX_DIR / path).resolve()
    if not str(target).startswith(str(SANDBOX_DIR.resolve())):
        return f"[BLOCKED] read_file is restricted to agent/sandbox/. Attempted: {path}"
    if not target.exists():
        return f"[ERROR] File not found: {path}"
    return target.read_text(encoding="utf-8")


def _sync_outbox(session_id: str, kind: str, payload: dict) -> None:
    """Write directly to Supabase outbox — synchronous, no event loop needed."""
    import os
    from supabase import create_client
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if url and key:
        try:
            client = create_client(url, key)
            client.table("outbox").insert({
                "session_id": session_id,
                "kind": kind,
                "payload": payload,
            }).execute()
        except Exception as e:
            import logging
            logging.getLogger("agentshield.tools").warning("outbox insert failed: %s", e)


def send_email(to: str, subject: str, body: str, session_id: str = "") -> str:
    _sync_outbox(session_id, "email", {"to": to, "subject": subject, "body": body})
    return f"[FAKE] Email sent to {to} — subject: {subject}"


def http_post(url: str, body: str, session_id: str = "") -> str:
    _sync_outbox(session_id, "http_post", {"url": url, "body": body})
    return f"[FAKE] POST sent to {url}"


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Fetch the text content of a web page.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "URL to fetch"}},
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from the sandbox directory.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Filename relative to sandbox/"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Send an email.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["to", "subject", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "http_post",
            "description": "Make an HTTP POST request.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["url", "body"],
            },
        },
    },
]


def dispatch(tool_name: str, args: dict, session_id: str = "") -> str:
    if tool_name == "web_fetch":
        return web_fetch(args["url"])
    if tool_name == "read_file":
        return read_file(args["path"])
    if tool_name == "send_email":
        return send_email(args["to"], args.get("subject", ""), args.get("body", ""), session_id)
    if tool_name == "http_post":
        return http_post(args["url"], args.get("body", ""), session_id)
    return f"[ERROR] Unknown tool: {tool_name}"
