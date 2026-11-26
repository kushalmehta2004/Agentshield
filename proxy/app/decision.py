"""Decision table from PRD Section 7.4."""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CauseInfo:
    source_label: str
    chunk_index: int | None
    chunk_text: str | None
    effect: str  # "removes_call" | "changes_target" | "none"


@dataclass
class Verdict:
    decision: str           # ALLOW | BLOCK | WARN
    attack_detected: bool
    unstable: bool
    causes: list[CauseInfo] = field(default_factory=list)
    reruns: list[dict] = field(default_factory=list)
    latency_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "attack_detected": self.attack_detected,
            "unstable": self.unstable,
            "causes": [
                {
                    "source_label": c.source_label,
                    "chunk_index": c.chunk_index,
                    "chunk_text": c.chunk_text,
                    "effect": c.effect,
                }
                for c in self.causes
            ],
            "reruns": self.reruns,
            "latency_ms": self.latency_ms,
        }


def decide(
    attack_detected: bool,
    causes: list[CauseInfo],
    sc: dict,
    messages: list[dict],
    target_args: list[str],
    unstable: bool,
) -> str:
    """Return ALLOW, BLOCK, or WARN per PRD Section 7.4."""
    if attack_detected:
        return "BLOCK"

    untrusted_causes = [c for c in causes if c.effect in ("removes_call", "changes_target")]
    if not untrusted_causes:
        return "ALLOW"

    # Check if the SC target value appears in any trusted message
    import json
    try:
        sc_args = json.loads(sc["function"].get("arguments", "{}"))
    except Exception:
        sc_args = {}

    target_in_trusted = False
    for m in messages:
        if m.get("role") in ("system", "user"):
            content = m.get("content", "") or ""
            if isinstance(content, list):
                content = " ".join(p.get("text", "") for p in content if isinstance(p, dict))
            content_lower = content.lower()
            for arg in target_args:
                val = str(sc_args.get(arg, "")).lower().strip()
                if val and val in content_lower:
                    target_in_trusted = True
                    break

    # Also check if target appears in the culprit chunk text
    target_in_untrusted_chunk = any(
        c.chunk_text and any(
            str(sc_args.get(arg, "")).lower().strip() in c.chunk_text.lower()
            for arg in target_args
        )
        for c in untrusted_causes
    )

    if target_in_untrusted_chunk and not target_in_trusted:
        return "BLOCK"
    return "WARN"
