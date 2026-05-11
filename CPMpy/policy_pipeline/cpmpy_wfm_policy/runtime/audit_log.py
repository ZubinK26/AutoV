"""Append-only audit log for runtime decisions (Project_Spec §7.5)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from cpmpy_wfm_policy.runtime.decision import Decision


@dataclass(frozen=True)
class AuditRecord:
    """Fields required by §7.5 (+ extension ``flags_for_routing``)."""

    policy_version: str
    tool_call: dict[str, Any]
    state_snapshot: dict[str, Any]
    decision_allow: bool
    violated_rules: list[str]
    rules_consulted: list[str]
    pattern_used: Literal["A", "B"]
    solver_time_ms: float
    flags_for_routing: dict[str, bool]
    explanation: str = ""

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "policy_version": self.policy_version,
            "tool_call": self.tool_call,
            "state_snapshot": self.state_snapshot,
            "decision": {
                "allow": self.decision_allow,
                "violated_rules": self.violated_rules,
                "pattern_used": self.pattern_used,
                "explanation": self.explanation,
                "solver_time_ms": self.solver_time_ms,
            },
            "rules_consulted": self.rules_consulted,
            "pattern_used": self.pattern_used,
            "solver_time_ms": self.solver_time_ms,
            "flags_for_routing": self.flags_for_routing,
        }


def append_audit_jsonl(path: str | Path, record: AuditRecord) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record.to_jsonable(), ensure_ascii=False) + "\n")


def audit_record_from_decision(
    *,
    policy_version: str,
    tool_call: dict[str, Any],
    state_snapshot: dict[str, Any],
    manifest: dict[str, Any],
    decision: Decision,
) -> AuditRecord:
    rules_consulted: list[str] = []
    for r in manifest.get("rules", []):
        if isinstance(r, dict) and r.get("id") is not None:
            rules_consulted.append(str(r["id"]))
    ug = any(
        bool(r.get("uses_global_constraints"))
        for r in manifest.get("rules", [])
        if isinstance(r, dict)
    )
    uv = any(
        bool(r.get("uses_vector_variables"))
        for r in manifest.get("rules", [])
        if isinstance(r, dict)
    )
    return AuditRecord(
        policy_version=policy_version,
        tool_call=tool_call,
        state_snapshot=state_snapshot,
        decision_allow=decision.allow,
        violated_rules=list(decision.violated_rules),
        rules_consulted=rules_consulted,
        pattern_used=decision.pattern_used,
        solver_time_ms=decision.solver_time_ms,
        flags_for_routing={"uses_global_constraints": ug, "uses_vector_variables": uv},
        explanation=decision.explanation,
    )
