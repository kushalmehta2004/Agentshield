"""Proof of Cause engine — Section 7 of the PRD."""
import asyncio
import json
import logging
import time

from app.provenance import (
    Source, label_sources, mask_user, remove_source,
    split_paragraphs, remove_paragraphs,
)
from app.matching import response_has_match, lexical_overlap_score, target_in_text
from app.decision import CauseInfo, Verdict, decide
from app.policy import get_max_reruns, get_mask_prompt, get_target_args
from app.upstream import call_upstream

log = logging.getLogger("agentshield.poc")


class Budget:
    def __init__(self, max_reruns: int):
        self.max_reruns = max_reruns
        self.used = 0

    def take(self, n: int = 1) -> bool:
        if self.used + n > self.max_reruns:
            return False
        self.used += n
        return True

    def remaining(self) -> int:
        return self.max_reruns - self.used


async def _rerun(messages: list[dict], tools: list[dict] | None, model: str | None) -> dict:
    return await call_upstream(messages=messages, tools=tools, model=model, force_upstream=True)


def _first_sc(response: dict, sc_name: str, target_args: list[str]) -> dict | None:
    """Find the first sensitive call matching sc_name in response."""
    for choice in response.get("choices", []):
        for tc in choice.get("message", {}).get("tool_calls") or []:
            if tc["function"]["name"] == sc_name:
                return tc
    return None


def _top_k_sources(sources: list[Source], sc: dict, target_args: list[str], k: int) -> list[Source]:
    if len(sources) <= k:
        return sources
    scored = sorted(
        sources,
        key=lambda s: lexical_overlap_score(sc, target_args, s.content),
        reverse=True,
    )
    return scored[:k]


async def _binary_search_paragraph(
    messages: list[dict],
    source: Source,
    sc: dict,
    target_args: list[str],
    tools: list[dict] | None,
    model: str | None,
    budget: Budget,
) -> tuple[int | None, str | None]:
    """Return (paragraph_index, paragraph_text) of culprit or (None, None)."""
    paragraphs = split_paragraphs(source.content)
    if not paragraphs:
        return None, None

    lo, hi = 0, len(paragraphs)
    # We already know removing the whole source removes the call, so we do binary search
    # over which half contains the culprit.
    while hi - lo > 1:
        if not budget.take():
            break
        mid = (lo + hi) // 2
        # Remove paragraphs in [lo, mid)
        indices_to_remove = set(range(lo, mid))
        variant = remove_paragraphs(messages, source, indices_to_remove)
        resp = await _rerun(variant, tools, model)
        if not response_has_match(resp, sc, target_args):
            # Culprit is in the removed half [lo, mid)
            hi = mid
        else:
            # Culprit is in [mid, hi)
            lo = mid

    idx = lo
    if idx < len(paragraphs):
        return idx, paragraphs[idx]
    return None, None


async def run(
    messages: list[dict],
    tools: list[dict] | None,
    model: str | None,
    sc: dict,
    session_id: str,
) -> Verdict:
    t0 = time.monotonic()
    target_args = get_target_args(sc["function"]["name"])
    max_reruns = get_max_reruns()
    mask_prompt = get_mask_prompt()
    budget = Budget(max_reruns)

    sources = label_sources(messages)
    top_sources = _top_k_sources(sources, sc, target_args, k=5)

    # Parallel: original re-run (stability) + masked re-run (Check A) + source-level (Check B)
    n_parallel = 1 + 1 + len(top_sources)
    if not budget.take(n_parallel):
        # Not enough budget; fall back to just the masked re-run
        budget.used = 0
        budget.take(2)
        orig_coro = _rerun(messages, tools, model)
        masked_coro = _rerun(mask_user(messages, mask_prompt), tools, model)
        orig_resp, masked_resp = await asyncio.gather(orig_coro, masked_coro)
        src_resps = []
        top_sources = []
    else:
        orig_coro = _rerun(messages, tools, model)
        masked_coro = _rerun(mask_user(messages, mask_prompt), tools, model)
        src_coros = [_rerun(remove_source(messages, s), tools, model) for s in top_sources]
        results = await asyncio.gather(orig_coro, masked_coro, *src_coros)
        orig_resp, masked_resp, *src_resps = results

    stable = response_has_match(orig_resp, sc, target_args)
    attack_detected = response_has_match(masked_resp, sc, target_args)

    reruns = [
        {"variant": "original", "tool_calls": _extract_tcs(orig_resp)},
        {"variant": "masked", "tool_calls": _extract_tcs(masked_resp)},
    ]
    for s, r in zip(top_sources, src_resps):
        reruns.append({"variant": f"minus_{s.label}", "tool_calls": _extract_tcs(r)})

    # Build causes from source-level checks
    causes: list[CauseInfo] = []
    for s, r in zip(top_sources, src_resps):
        if not response_has_match(r, sc, target_args):
            effect = "removes_call"
        else:
            orig_tc = _first_sc(orig_resp, sc["function"]["name"], target_args)
            new_tc = _first_sc(r, sc["function"]["name"], target_args)
            if orig_tc and new_tc and not _same_target(orig_tc, new_tc, target_args):
                effect = "changes_target"
            else:
                effect = "none"

        if effect != "none":
            causes.append(CauseInfo(
                source_label=s.label,
                chunk_index=None,
                chunk_text=None,
                effect=effect,
            ))

    # Paragraph-level binary search for each cause source
    for cause in causes:
        # Find the source object
        src = next((s for s in top_sources if s.label == cause.source_label), None)
        if src and budget.remaining() > 0:
            idx, text = await _binary_search_paragraph(
                messages, src, sc, target_args, tools, model, budget
            )
            cause.chunk_index = idx
            cause.chunk_text = text

    decision_str = decide(attack_detected, causes, sc, messages, target_args, unstable=not stable)

    latency_ms = int((time.monotonic() - t0) * 1000)
    log.info(
        "%s %s(%s) cause=%s reruns=%d %dms",
        decision_str,
        sc["function"]["name"],
        _target_summary(sc, target_args),
        causes[0].source_label + (f"#p{causes[0].chunk_index}" if causes[0].chunk_index is not None else "") if causes else "none",
        budget.used,
        latency_ms,
    )

    return Verdict(
        decision=decision_str,
        attack_detected=attack_detected,
        unstable=not stable,
        causes=causes,
        reruns=reruns,
        latency_ms=latency_ms,
    )


def _extract_tcs(response: dict) -> list[dict]:
    tcs = []
    for choice in response.get("choices", []):
        for tc in choice.get("message", {}).get("tool_calls") or []:
            tcs.append({
                "name": tc["function"]["name"],
                "arguments": tc["function"].get("arguments", "{}"),
            })
    return tcs


def _same_target(a: dict, b: dict, target_args: list[str]) -> bool:
    try:
        args_a = json.loads(a["function"].get("arguments", "{}"))
        args_b = json.loads(b["function"].get("arguments", "{}"))
    except Exception:
        return True
    from app.matching import normalize
    return all(normalize(str(args_a.get(k, ""))) == normalize(str(args_b.get(k, ""))) for k in target_args)


def _target_summary(sc: dict, target_args: list[str]) -> str:
    try:
        args = json.loads(sc["function"].get("arguments", "{}"))
    except Exception:
        return "?"
    return ", ".join(f"{k}={args.get(k, '?')}" for k in target_args)
