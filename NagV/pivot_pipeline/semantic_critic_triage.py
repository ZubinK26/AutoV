"""Interactive Pivot Critic finding triage (selective semantic Repairer_Piv)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from pivot_pipeline.critic_agent import CriticReport, critic_repair_handoff_dict
from pivot_pipeline.cross_critic_interactive_loop import parse_disagree_indices


def sorted_critic_findings(report: CriticReport) -> list:
    return sorted(report.findings, key=lambda f: f.id)


def triage_index_to_finding_id(report: CriticReport) -> dict[int, str]:
    return {i: f.id for i, f in enumerate(sorted_critic_findings(report), start=1)}


def format_critic_triage_summary(approved: set[str], ignored: set[str]) -> str:
    return "\n".join(
        [
            "",
            "Critic triage summary:",
            f"  Approved for repair: {', '.join(sorted(approved)) or '(none)'}",
            f"  Ignored: {', '.join(sorted(ignored)) or '(none)'}",
            "",
        ]
    )


def run_critic_finding_triage(
    report: CriticReport,
    *,
    input_fn: Callable[[str], str],
    print_fn: Callable[..., None],
) -> tuple[set[str], set[str]]:
    findings = sorted_critic_findings(report)
    if not findings:
        return set(), set()

    index_map = triage_index_to_finding_id(report)
    all_ids = {f.id for f in findings}
    max_index = len(findings)

    print_fn("\n=== Critic triage ===\n")
    while True:
        ans = input_fn("Accept all suggestions for repair? (y/n): ").strip().lower()
        if ans in ("y", "yes"):
            return set(all_ids), set()
        if ans in ("n", "no"):
            break
        print_fn("  Invalid choice; enter y or n.\n")

    while True:
        print_fn(
            "Enter the number(s) you DISAGREE with (comma-separated), "
            "or press Enter if you agree with all:\n"
            "  e.g. 2,3  — ignores findings 2 and 3; repairs the rest\n"
        )
        raw = input_fn("> ").strip()
        disagree_idx = parse_disagree_indices(raw, max_index=max_index)
        if disagree_idx is None:
            print_fn(f"  Invalid input; use integers 1–{max_index}, comma-separated.\n")
            continue
        ignored = {index_map[i] for i in disagree_idx}
        approved = all_ids - ignored
        return approved, ignored


def write_critic_repair_handoff(
    work_dir: Path,
    report: CriticReport,
    *,
    approved: set[str],
    ignored: set[str],
    source_note: str,
    **extra: object,
) -> Path:
    handoff_path = work_dir / "critic_drift_handoff.json"
    h = critic_repair_handoff_dict(
        report,
        approved_ids=sorted(approved),
        ignored_ids=sorted(ignored),
        full_report_path=work_dir / "critic_report.json",
        source_note=source_note,
        **extra,
    )
    handoff_path.write_text(json.dumps(h, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return handoff_path


__all__ = [
    "format_critic_triage_summary",
    "run_critic_finding_triage",
    "sorted_critic_findings",
    "triage_index_to_finding_id",
    "write_critic_repair_handoff",
]
