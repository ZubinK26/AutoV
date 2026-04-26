"""Count `%% Rule:`` headers in ClinCon / Clingo policy text (mirrors SMT `rule_count` idea)."""

from __future__ import annotations

import re

_RULE_LINE = re.compile(r"^%\s*Rule:\s*(\S+)", re.MULTILINE)


def distinct_rule_ids_in_lp(s: str) -> set[str]:
    if not s or not s.strip():
        return set()
    return {m.group(1) for m in _RULE_LINE.finditer(s)}


def rule_count(s: str) -> int:
    return len(distinct_rule_ids_in_lp(s))
