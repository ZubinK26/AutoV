from __future__ import annotations

import json
import re
from typing import Any, Union


def extract_first_json_value(text: str) -> Union[dict, list]:
    """Pull the first JSON object or array from possibly fenced/markdown model output."""
    t = (text or "").strip()
    if not t:
        raise ValueError("empty model output")

    # Fenced ```json ... ```
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", t, re.IGNORECASE)
    if fence:
        chunk = fence.group(1).strip()
        try:
            return json.loads(chunk)
        except json.JSONDecodeError:
            pass

    # First { ... } or [ ... ]
    blk = _balanced_json(t, "{", "}")
    if blk is not None:
        return json.loads(blk)
    blk = _balanced_json(t, "[", "]")
    if blk is not None:
        return json.loads(blk)

    return json.loads(t)


def _balanced_json(s: str, open_c: str, close_c: str) -> str | None:
    start = s.find(open_c)
    if start < 0:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(s)):
        ch = s[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
            continue
        if ch == open_c:
            depth += 1
        elif ch == close_c:
            depth -= 1
            if depth == 0:
                return s[start : i + 1]
    return None


def parse_json_object(text: str) -> dict[str, Any]:
    v = extract_first_json_value(text)
    if not isinstance(v, dict):
        raise ValueError(f"expected JSON object, got {type(v).__name__}")
    return v


def parse_json_array(text: str) -> list[Any]:
    v = extract_first_json_value(text)
    if not isinstance(v, list):
        raise ValueError(f"expected JSON array, got {type(v).__name__}")
    return v


__all__ = ["extract_first_json_value", "parse_json_object", "parse_json_array"]
