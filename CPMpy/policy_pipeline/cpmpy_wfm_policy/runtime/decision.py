"""Runtime types (Project_Spec §7.4)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Decision:
    allow: bool
    violated_rules: list[str]
    pattern_used: Literal["A", "B"]
    explanation: str
    solver_time_ms: float
