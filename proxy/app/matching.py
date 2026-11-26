"""Tool call matching and normalization."""
import re


def normalize(value: str) -> str:
    return value.lower().strip().rstrip("/")


def calls_match(a: dict, b: dict, target_args: list[str]) -> bool:
    """Return True if a and b call the same tool with equal target args."""
    if a.get("function", {}).get("name") != b.get("function", {}).get("name"):
        return False
    import json
    try:
        args_a = json.loads(a["function"].get("arguments", "{}"))
        args_b = json.loads(b["function"].get("arguments", "{}"))
    except Exception:
        return False
    for arg in target_args:
        va = normalize(str(args_a.get(arg, "")))
        vb = normalize(str(args_b.get(arg, "")))
        if va != vb:
            return False
    return True


def response_has_match(response: dict, sc: dict, target_args: list[str]) -> bool:
    """Return True if any tool call in response matches sc."""
    for choice in response.get("choices", []):
        for tc in choice.get("message", {}).get("tool_calls") or []:
            if calls_match(tc, sc, target_args):
                return True
    return False


def target_in_text(sc: dict, target_args: list[str], text: str) -> bool:
    """Return True if any target arg value appears in text (case-insensitive)."""
    import json
    try:
        args = json.loads(sc["function"].get("arguments", "{}"))
    except Exception:
        return False
    text_lower = text.lower()
    for arg in target_args:
        val = normalize(str(args.get(arg, "")))
        if val and val in text_lower:
            return True
    return False


def lexical_overlap_score(sc: dict, target_args: list[str], text: str) -> float:
    """Score 0-1: fraction of target arg tokens found in text."""
    import json
    try:
        args = json.loads(sc["function"].get("arguments", "{}"))
    except Exception:
        return 0.0
    tokens: list[str] = []
    for arg in target_args:
        val = str(args.get(arg, ""))
        tokens += re.findall(r'\w+', val.lower())
    if not tokens:
        return 0.0
    text_lower = text.lower()
    hits = sum(1 for t in tokens if t in text_lower)
    return hits / len(tokens)
