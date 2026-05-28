"""Safe parsing of operator line-index prompts (WFM interactive)."""

from __future__ import annotations

import sys
from typing import Callable, TextIO


def parse_int_list(s: str) -> list[int]:
    s = s.strip()
    if not s:
        return []
    out: list[int] = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        out.append(int(part))
    return out


def prompt_int_list(
    *,
    input_fn: Callable[[str], str],
    stderr: TextIO,
    prompt: str,
    allow_empty: bool = True,
    initial: str | None = None,
) -> list[int]:
    """
    Parse comma-separated 1-based indices; re-prompt on non-integer input (no traceback).
    """
    raw: str | None = initial
    while True:
        if raw is None:
            raw = input_fn(prompt).strip()
        if not raw:
            if allow_empty:
                return []
            stderr.write("Enter at least one line number (e.g. 2 or 2,4).\n")
            raw = None
            continue
        try:
            return parse_int_list(raw)
        except ValueError:
            stderr.write(
                "Expected comma-separated line numbers (e.g. 2 or 2,4), not rule text.\n"
            )
            raw = None


__all__ = ["parse_int_list", "prompt_int_list"]
