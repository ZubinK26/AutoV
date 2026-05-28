"""Detect repeated repair errors within one operator REPAIR session."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

_STALL_NORMALIZE_PATTERNS = (
    (re.compile(r"attempt \d+/\d+", re.I), "attempt N/M"),
    (re.compile(r"registry attempt \d+/\d+", re.I), "registry attempt N/M"),
    (re.compile(r"line \d+", re.I), "line N"),
    (re.compile(r"column \d+", re.I), "column N"),
    (re.compile(r"char \d+", re.I), "char N"),
)


def semantic_repair_stall_threshold() -> int:
    raw = os.getenv("PIVOT_SEMANTIC_REPAIR_STALL_THRESHOLD", "2").strip()
    try:
        return max(2, min(int(raw), 10))
    except ValueError:
        return 2


def semantic_repair_stall_fail_fast() -> bool:
    raw = os.getenv("PIVOT_SEMANTIC_REPAIR_STALL_FAIL_FAST", "1").strip().lower()
    return raw in ("1", "true", "yes")


def normalize_error_message(msg: str) -> str:
    t = (msg or "").strip()
    for pat, repl in _STALL_NORMALIZE_PATTERNS:
        t = pat.sub(repl, t)
    return t


@dataclass
class RepairStallTracker:
    """Track consecutive identical (stage, message) fingerprints."""

    threshold: int = 2
    _last_stage: str | None = None
    _last_fingerprint: str | None = None
    _consecutive: int = 0
    stall_detected: bool = False
    stall_stage: str | None = None
    stall_fingerprint: str | None = None

    def record(self, stage: str, message: str) -> bool:
        """
        Record an error. Returns True if stall threshold reached (same stage + fingerprint).
        """
        fp = normalize_error_message(message)
        if stage == self._last_stage and fp == self._last_fingerprint:
            self._consecutive += 1
        else:
            self._last_stage = stage
            self._last_fingerprint = fp
            self._consecutive = 1
        if self._consecutive >= self.threshold:
            self.stall_detected = True
            self.stall_stage = stage
            self.stall_fingerprint = fp
            return True
        return False

    def reset_repairer_track(self) -> None:
        """Reset after a successful repairer+compile step (registry may still fail)."""
        self._last_stage = None
        self._last_fingerprint = None
        self._consecutive = 0


def stall_gate_message(*, stage: str, proceed_token: str = "PROCEED_INCOMPLETE") -> str:
    return (
        f"[policy gate] Repair stalled: repeated {stage} error (automated).\n"
        "  Type 'REPAIR' again later, 'retriage' to narrow approved findings, "
        f"or {proceed_token!r} to continue without a successful repair.\n"
        "  No new LLM calls in this REPAIR session until you start a new REPAIR.\n"
    )


__all__ = [
    "RepairStallTracker",
    "normalize_error_message",
    "semantic_repair_stall_fail_fast",
    "semantic_repair_stall_threshold",
    "stall_gate_message",
]
