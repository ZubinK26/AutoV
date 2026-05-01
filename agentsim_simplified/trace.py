from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class TraceEntry:
    step: int
    description: str
    tool_name: str
    parameters: dict[str, Any]
    decision: str
    unsat_core: list[str]
    explanation: str
    result_summary: str


def print_trace(entries: list[TraceEntry]) -> None:
    for e in entries:
        print(f"[{e.step}] {e.description}")
        print(f"    tool={e.tool_name} params={e.parameters}")
        print(f"    decision={e.decision} | {e.result_summary}")
        if e.explanation:
            print(f"    note: {e.explanation}")
        print()


def print_summary(entries: list[TraceEntry]) -> None:
    gated = [e for e in entries if e.tool_name == "apply_refund"]
    n_allow = sum(1 for e in gated if e.decision == "ALLOW")
    n_block = sum(1 for e in gated if e.decision == "BLOCK")
    print(f"apply_refund: {n_allow} ALLOW, {n_block} BLOCK (of {len(gated)} gated steps)")
