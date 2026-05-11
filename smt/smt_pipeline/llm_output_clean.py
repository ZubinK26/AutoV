"""Heuristic cleanup of LLM formalizer output before Z3 parse."""

from __future__ import annotations

import re


def strip_markdown_fenced_smt(s: str) -> str:
    """
    If the model wrapped the policy fragment in a single markdown code fence, return inner text.
    Otherwise return ``s`` unchanged (still stripped).
    """
    t = s.strip()
    m = re.match(r"^```[a-zA-Z0-9_-]*\s*\r?\n([\s\S]*?)\r?\n```\s*$", t)
    if m:
        return m.group(1).strip()
    return t
