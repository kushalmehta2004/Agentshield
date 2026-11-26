"""Regex baseline detector — ~15 injection patterns for comparison."""
import re

_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+instructions",
    r"disregard\s+(all\s+)?(previous|prior)\s+instructions",
    r"forget\s+(all\s+)?(previous|prior)\s+instructions",
    r"you\s+are\s+now\s+a",
    r"act\s+as\s+(a\s+|an\s+)?(?:new\s+)?ai",
    r"new\s+system\s+prompt",
    r"override\s+.*\s+instructions",
    r"task\s+override",
    r"execute\s+(the\s+)?following\s+(instructions|commands)",
    r"ai\s+assistant\s+instruction",
    r"<\!--.*?(instruction|execute|forward|send|read).*?-->",
    r"prompt\s+injection",
    r"jailbreak",
    r"do\s+not\s+follow\s+your\s+original",
    r"your\s+(real|true|actual)\s+instructions",
]

_COMPILED = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in _PATTERNS]


def matches_injection(text: str) -> bool:
    """Return True if text matches any known injection pattern."""
    for pattern in _COMPILED:
        if pattern.search(text):
            return True
    return False


def check_messages(messages: list[dict]) -> bool:
    """Return True if any untrusted (tool role) message matches an injection pattern."""
    for m in messages:
        if m.get("role") == "tool":
            content = m.get("content", "") or ""
            if isinstance(content, list):
                content = " ".join(p.get("text", "") for p in content if isinstance(p, dict))
            if matches_injection(str(content)):
                return True
    return False
