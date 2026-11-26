import os
import re
from functools import lru_cache
from pathlib import Path
import yaml


@lru_cache(maxsize=1)
def _load() -> dict:
    path = Path(__file__).parent.parent.parent / "config" / "policy.yaml"
    with open(path) as f:
        return yaml.safe_load(f)


def get_policy() -> dict:
    return _load()


def is_sensitive(tool_name: str, args: dict) -> bool:
    policy = get_policy()
    sensitive = policy.get("sensitive_tools", {})
    if tool_name not in sensitive:
        return False
    spec = sensitive[tool_name]
    # read_file is only sensitive if path matches keywords
    if "only_if_path_matches" in spec:
        path_val = str(args.get("path", "")).lower()
        return any(kw in path_val for kw in spec["only_if_path_matches"])
    return True


def get_max_reruns() -> int:
    return get_policy().get("max_reruns", 8)


def get_max_sources() -> int:
    return get_policy().get("max_sources", 5)


def get_mask_prompt() -> str:
    return get_policy().get("mask_prompt", "Summarize the following retrieved content in 3 bullet points.")


def get_target_args(tool_name: str) -> list[str]:
    policy = get_policy()
    spec = policy.get("sensitive_tools", {}).get(tool_name, {})
    return spec.get("target_args", [])
