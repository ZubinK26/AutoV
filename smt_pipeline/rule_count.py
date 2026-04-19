"""Count distinct rule_ids from policy_model.smt2 per `control_flow_v3.md` § Rule counting."""

from __future__ import annotations

import re
from typing import Set

_RULE_HEADER = re.compile(r"^; Rule: (\S+)\s+\|\s+Line: (\d+)\s*$", re.MULTILINE)


def distinct_rule_ids_in_policy(s: str) -> set[str]:
    if not s or not s.strip():
        return set()
    return {m.group(1) for m in _RULE_HEADER.finditer(s)}


def rule_count(s: str) -> int:
    return len(distinct_rule_ids_in_policy(s))
