"""Interactive CrossCritic triage and policy gate (selective CrossRepairer)."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Callable

from pivot_pipeline.cross_critic_agent import (
    CrossCriticOutputError,
    CrossCriticReport,
    run_cross_critic_parsed_with_repairs,
)
from pivot_pipeline.cross_repairer_agent import cross_repair_handoff_dict
from pivot_pipeline.policy_gates import PROCEED_INCOMPLETE_TOKEN, REPAIR_CRITIC_DRIFT_TOKEN
from pivot_pipeline.api_retry import api_auto_retries_max, transient_api_retry_sleep_seconds
from pivot_pipeline.test_repair_registry import is_repairer_api_error

REPAIR_TOKEN = REPAIR_CRITIC_DRIFT_TOKEN


class CrossCriticResumeAtGate(Exception):
    """Interactive: return to CrossCritic triage/REPAIR gate without exiting the pipeline."""


def cross_critic_api_auto_retries() -> int | None:
    """
    Max automatic CrossCritic retries on transient API errors.

    ``PIVOT_CROSS_CRITIC_API_AUTO_RETRIES=0`` (default) = unlimited in interactive mode.
    """
    raw = os.getenv("PIVOT_CROSS_CRITIC_API_AUTO_RETRIES", "0").strip()
    if raw in ("", "0"):
        return None
    try:
        return max(1, min(int(raw), 100))
    except ValueError:
        return None


def load_cached_cross_critic_report(work_dir: Path) -> tuple[str, CrossCriticReport] | None:
    """Load last persisted CrossCritic report from work_dir, if present."""
    report_path = work_dir / "cross_critic_report.json"
    if not report_path.is_file():
        return None
    raw_path = work_dir / "cross_critic_result.txt"
    raw = raw_path.read_text(encoding="utf-8") if raw_path.is_file() else report_path.read_text(encoding="utf-8")
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
        report = CrossCriticReport.model_validate(data)
    except (json.JSONDecodeError, ValueError):
        return None
    return raw, report


def fetch_cross_critic_report(
    processed_nl: str,
    linearized_model: str,
    *,
    work_dir: Path,
    summary: dict,
    interactive_any: bool,
    input_fn: Callable[[str], str],
    print_fn: Callable[..., None],
    resume_at_gate: bool = False,
) -> tuple[str, CrossCriticReport]:
    """
    Run CrossCritic with automatic JSON repair.

    Interactive: prompt ``retry`` on parse/API failure. When ``resume_at_gate`` is true
    (post–CrossRepairer re-check), Enter returns to the repair gate via ``CrossCriticResumeAtGate``.
    """
    api_cap = cross_critic_api_auto_retries()
    api_attempts = 0

    while True:
        try:
            raw, report, json_repair_attempts = run_cross_critic_parsed_with_repairs(
                processed_nl,
                linearized_model,
                work_dir=work_dir,
            )
            summary["cross_critic_json_repair_attempts"] = json_repair_attempts
            return raw, report
        except CrossCriticOutputError as e:
            invalid = work_dir / "cross_critic_result_invalid_attempt_0.txt"
            if invalid.is_file():
                summary["cross_critic_result"] = str(invalid.resolve())
            if not interactive_any:
                raise
            print_fn(
                f"\n[policy gate] CrossCritic output could not be parsed "
                f"({e.repair_attempts} automatic JSON repair tries).\n"
                f"  {e}\n"
                "  Type 'retry' to call CrossCritic again.\n"
            )
            if resume_at_gate:
                print_fn("  Press Enter to return to the cross repair gate (same findings).\n")
            else:
                print_fn("  Press Enter to abort.\n")
            if input_fn("> ").strip().lower() == "retry":
                api_attempts = 0
                continue
            if resume_at_gate:
                raise CrossCriticResumeAtGate() from e
            raise
        except Exception as e:
            if not is_repairer_api_error(e):
                raise
            api_attempts += 1
            if api_cap is None or api_attempts <= api_cap:
                label = f"{api_attempts}/{api_cap}" if api_cap is not None else str(api_attempts)
                print_fn(
                    f"\n[policy gate] CrossCritic API unavailable ({label}): {e}\n"
                    f"  Retrying in {transient_api_retry_sleep_seconds():g}s…\n",
                )
                time.sleep(transient_api_retry_sleep_seconds())
                continue
            if not interactive_any:
                raise
            print_fn(
                f"\n[policy gate] CrossCritic API unavailable after {api_cap} automatic retries.\n"
                f"  {e}\n"
                "  Type 'retry' to call CrossCritic again.\n",
            )
            if resume_at_gate:
                print_fn(
                    "  Press Enter to return to the cross repair gate "
                    "(same CrossCritic report; triage skipped once).\n"
                )
            else:
                cached = load_cached_cross_critic_report(work_dir)
                if cached is not None:
                    print_fn(
                        "  Press Enter to continue with the last saved CrossCritic report, "
                        "or type 'retry'.\n",
                    )
                else:
                    print_fn("  Press Enter to abort.\n")
            ans = input_fn("> ").strip().lower()
            if ans == "retry":
                api_attempts = 0
                continue
            if resume_at_gate:
                raise CrossCriticResumeAtGate() from e
            cached = load_cached_cross_critic_report(work_dir)
            if cached is not None and not ans:
                print_fn("[policy gate] Using last saved cross_critic_report.json.\n")
                return cached
            raise


def sorted_cross_findings(report: CrossCriticReport) -> list:
    return sorted(report.findings, key=lambda f: f.id)


def triage_index_to_finding_id(report: CrossCriticReport) -> dict[int, str]:
    """1-based display index → finding id (stable sort by id)."""
    return {i: f.id for i, f in enumerate(sorted_cross_findings(report), start=1)}


def parse_disagree_indices(raw: str, *, max_index: int) -> set[int] | None:
    """Parse comma-separated 1-based indices; None if invalid or empty (approve all)."""
    text = (raw or "").strip()
    if not text:
        return set()
    out: set[int] = set()
    for part in text.split(","):
        piece = part.strip()
        if not piece:
            continue
        if not piece.isdigit():
            return None
        n = int(piece)
        if n < 1 or n > max_index:
            return None
        out.add(n)
    return out


def format_cross_triage_summary(approved: set[str], ignored: set[str]) -> str:
    lines = [
        "",
        "CrossCritic triage summary:",
        f"  Approved for repair: {', '.join(sorted(approved)) or '(none)'}",
        f"  Ignored: {', '.join(sorted(ignored)) or '(none)'}",
        "",
    ]
    return "\n".join(lines)


def run_cross_finding_triage(
    report: CrossCriticReport,
    *,
    input_fn: Callable[[str], str],
    print_fn: Callable[..., None],
) -> tuple[set[str], set[str]]:
    """Accept-all or disagree-by-index triage; returns (approved_ids, ignored_ids)."""
    findings = sorted_cross_findings(report)
    if not findings:
        return set(), set()

    index_map = triage_index_to_finding_id(report)
    all_ids = {f.id for f in findings}
    max_index = len(findings)

    print_fn("\n=== CrossCritic triage ===\n")
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


def write_cross_repair_handoff(
    work_dir: Path,
    report: CrossCriticReport,
    *,
    approved: set[str],
    ignored: set[str],
    source_note: str = "user approved repair subset",
) -> Path:
    full_path = work_dir / "cross_critic_report.json"
    handoff_path = work_dir / "cross_repair_handoff.json"
    h = cross_repair_handoff_dict(
        report,
        approved_ids=sorted(approved),
        ignored_ids=sorted(ignored),
        full_report_path=full_path,
        source_note=source_note,
    )
    handoff_path.write_text(json.dumps(h, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return handoff_path


def warn_change_summary_outside_approved(
    change_summary: list[Any],
    approved_ids: set[str],
    *,
    print_fn: Callable[..., None],
) -> None:
    approved = set(approved_ids)
    for entry in change_summary:
        fid = None
        if isinstance(entry, dict):
            fid = entry.get("finding_id")
        else:
            fid = getattr(entry, "finding_id", None)
        if fid and fid not in approved:
            print_fn(
                f"[cross repair] warning: change_summary references non-approved finding {fid!r}\n",
            )


__all__ = [
    "CrossCriticResumeAtGate",
    "REPAIR_TOKEN",
    "cross_critic_api_auto_retries",
    "fetch_cross_critic_report",
    "format_cross_triage_summary",
    "load_cached_cross_critic_report",
    "parse_disagree_indices",
    "run_cross_finding_triage",
    "sorted_cross_findings",
    "triage_index_to_finding_id",
    "warn_change_summary_outside_approved",
    "write_cross_repair_handoff",
]
