"""Provenance labelling: identify untrusted sources in a message list and
manipulate them for re-runs.
"""
import re
from dataclasses import dataclass, field


@dataclass
class Source:
    index: int          # position among untrusted sources (0-based)
    tool_call_id: str
    tool_name: str
    key_arg: str        # the URL/path that identifies the source
    label: str          # "{tool_name}:{key_arg}"
    content: str        # the tool result text


def label_sources(messages: list[dict]) -> list[Source]:
    """Return ordered list of untrusted (tool role) sources from the messages."""
    # Build a map from tool_call_id → (tool_name, key_arg) from assistant tool_calls
    tc_map: dict[str, tuple[str, str]] = {}
    for m in messages:
        if m.get("role") == "assistant":
            for tc in m.get("tool_calls") or []:
                name = tc["function"]["name"]
                try:
                    import json
                    args = json.loads(tc["function"].get("arguments", "{}"))
                except Exception:
                    args = {}
                key_arg = _key_arg(name, args)
                tc_map[tc["id"]] = (name, key_arg)

    sources = []
    idx = 0
    for m in messages:
        if m.get("role") == "tool":
            tool_call_id = m.get("tool_call_id", "")
            tool_name, key_arg = tc_map.get(tool_call_id, ("unknown", "unknown"))
            sources.append(Source(
                index=idx,
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                key_arg=key_arg,
                label=f"{tool_name}:{key_arg}",
                content=_extract_content(m),
            ))
            idx += 1
    return sources


def _key_arg(tool_name: str, args: dict) -> str:
    priority = {
        "web_fetch": ["url"],
        "read_file": ["path"],
        "http_post": ["url"],
        "send_email": ["to"],
    }
    for k in priority.get(tool_name, []):
        if k in args:
            return str(args[k])
    for v in args.values():
        return str(v)
    return "unknown"


def _extract_content(message: dict) -> str:
    c = message.get("content", "")
    if isinstance(c, list):
        return " ".join(p.get("text", "") for p in c if isinstance(p, dict))
    return str(c or "")


def mask_user(messages: list[dict], mask_prompt: str) -> list[dict]:
    """Replace all user messages with a single neutral mask_prompt."""
    result = []
    inserted = False
    for m in messages:
        if m.get("role") == "user":
            if not inserted:
                result.append({"role": "user", "content": mask_prompt})
                inserted = True
            # skip extra user messages
        else:
            result.append(m)
    if not inserted:
        result.append({"role": "user", "content": mask_prompt})
    return result


def remove_source(messages: list[dict], source: Source) -> list[dict]:
    """Replace the tool result for a specific source with '[content removed]'."""
    result = []
    for m in messages:
        if m.get("role") == "tool" and m.get("tool_call_id") == source.tool_call_id:
            result.append({**m, "content": "[content removed]"})
        else:
            result.append(m)
    return result


def split_paragraphs(text: str) -> list[str]:
    """Split text into paragraphs; HTML comments become their own paragraph."""
    # Extract HTML comments as separate items
    comment_re = re.compile(r'(<!--.*?-->)', re.DOTALL)
    # Strip HTML tags
    tag_re = re.compile(r'<[^>]+>')

    parts = comment_re.split(text)
    paragraphs = []
    for part in parts:
        if comment_re.match(part):
            stripped = part.strip()
            if stripped:
                paragraphs.append(stripped)
        else:
            # Strip HTML tags and split on blank lines
            plain = tag_re.sub('', part)
            for block in re.split(r'\n\s*\n', plain):
                stripped = block.strip()
                if stripped:
                    paragraphs.append(stripped)
    return paragraphs


def remove_paragraphs(messages: list[dict], source: Source, indices_to_remove: set[int]) -> list[dict]:
    """Return messages with the given paragraph indices removed from source's content."""
    paragraphs = split_paragraphs(source.content)
    kept = [p for i, p in enumerate(paragraphs) if i not in indices_to_remove]
    new_content = "\n\n".join(kept) if kept else "[content removed]"
    result = []
    for m in messages:
        if m.get("role") == "tool" and m.get("tool_call_id") == source.tool_call_id:
            result.append({**m, "content": new_content})
        else:
            result.append(m)
    return result
