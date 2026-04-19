"""Extract JSON object from LLM markdown responses."""

from __future__ import annotations

import json
import re
from typing import Any


def extract_first_json_object(text: str) -> dict[str, Any]:
    if not text or not text.strip():
        raise ValueError("empty_response")
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fence:
        raw = fence.group(1).strip()
        return json.loads(raw)
    start = text.find("{")
    if start < 0:
        raise ValueError("no_json_object")
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    raise ValueError("unbalanced_braces")
