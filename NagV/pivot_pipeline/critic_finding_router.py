"""Classify Pivot Critic findings for semantic vs cross-coherence repair routing."""

from __future__ import annotations

import os
import re
from typing import Literal

from pivot_pipeline.critic_agent import CriticFinding, CriticReport

RepairRoute = Literal["cross_coherence", "semantic_drift"]

_CROSS_KEYWORDS = (
    "inconsistency",
    "outcome_split",
    "unreachable",
    "aggregate",
    "application_status",
    "escalation",
    "k_of_n",
    "advance_to_",
    "rejection-shaped",
    "rejection channel",
    "gatekeeper",
    "obligation",
    "enforcement",
    "yields satisfied",
    "logical_implication",
    "competency",
)

_CROSS_CATEGORIES = frozenset({"contradiction", "preemption", "pathway"})


def critic_semantic_repair_allow_cross_findings() -> bool:
    raw = os.getenv("PIVOT_CRITIC_SEMANTIC_REPAIR_ALLOW_CROSS_FINDINGS", "0").strip().lower()
    return raw in ("1", "true", "yes")


def classify_critic_finding(finding: CriticFinding) -> RepairRoute:
    text = " ".join(
        [
            finding.category or "",
            finding.explanation or "",
            finding.nl_pointer or "",
            finding.synthetic_pointer or "",
        ]
    ).lower()
    if finding.category in _CROSS_CATEGORIES:
        return "cross_coherence"
    if any(k in text for k in _CROSS_KEYWORDS):
        return "cross_coherence"
    rule_ids = re.findall(r"\bR\d{4,}\b", text, re.I)
    if len(set(rule_ids)) >= 4:
        return "cross_coherence"
    return "semantic_drift"


def partition_findings_by_route(
    findings: list[CriticFinding],
) -> tuple[list[CriticFinding], list[CriticFinding]]:
    cross: list[CriticFinding] = []
    semantic: list[CriticFinding] = []
    for f in findings:
        if classify_critic_finding(f) == "cross_coherence":
            cross.append(f)
        else:
            semantic.append(f)
    return cross, semantic


def format_routing_summary(
    *,
    approved_ids: set[str],
    report: CriticReport,
    with_cross_repair: bool,
) -> str:
    by_id = {f.id: f for f in report.findings}
    cross_ids: list[str] = []
    semantic_ids: list[str] = []
    for fid in sorted(approved_ids):
        f = by_id.get(fid)
        if f is None:
            continue
        if classify_critic_finding(f) == "cross_coherence":
            cross_ids.append(fid)
        else:
            semantic_ids.append(fid)
    lines = ["", "[policy gate] Critic repair routing:"]
    if cross_ids:
        rec = (
            "cross_coherence (CrossRepairer via pivot_pipeline.cross_coherence)"
            if with_cross_repair
            else "cross_coherence (enable --with-cross-critic and --with-cross-repair)"
        )
        lines.append(f"  {', '.join(cross_ids)} → {rec}")
    if semantic_ids:
        lines.append(f"  {', '.join(semantic_ids)} → semantic Repairer_Piv")
    if not cross_ids and not semantic_ids:
        lines.append("  (no approved findings)")
    lines.append("")
    return "\n".join(lines)


def should_defer_semantic_repair(
    *,
    approved_ids: set[str],
    report: CriticReport,
    with_cross_repair: bool,
) -> tuple[bool, str]:
    """
    Return (defer, reason). Defer when all approved findings are cross-tagged and cross repair is available.
    """
    if critic_semantic_repair_allow_cross_findings():
        return False, ""
    if not with_cross_repair or not approved_ids:
        return False, ""
    by_id = {f.id: f for f in report.findings}
    for fid in approved_ids:
        f = by_id.get(fid)
        if f is None or classify_critic_finding(f) != "cross_coherence":
            return False, ""
    return (
        True,
        "All approved critic findings are cross-rule IR coherence. "
        "Use the cross-coherence slice (CrossCritic triage + REPAIR), not semantic Repairer_Piv. "
        "Set PIVOT_CRITIC_SEMANTIC_REPAIR_ALLOW_CROSS_FINDINGS=1 to override.\n",
    )


__all__ = [
    "RepairRoute",
    "classify_critic_finding",
    "critic_semantic_repair_allow_cross_findings",
    "format_routing_summary",
    "partition_findings_by_route",
    "should_defer_semantic_repair",
]
