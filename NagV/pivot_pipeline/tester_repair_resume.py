"""Resume Pivot Test-Repair from on-disk tester report + handoff."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pivot_pipeline.post_model_workflow import TesterFinding, TesterReport


class TesterRepairResumeError(Exception):
    """Cannot resume test repair from work_dir artifacts."""


def tester_handoff_path(work_dir: Path) -> Path:
    return work_dir / "tester_repair_handoff.json"


def tester_report_path(work_dir: Path) -> Path:
    return work_dir / "tester_report.json"


def load_tester_report(work_dir: Path) -> TesterReport:
    path = tester_report_path(work_dir)
    if not path.is_file():
        raise TesterRepairResumeError(f"missing {path.name}")
    return TesterReport.model_validate(json.loads(path.read_text(encoding="utf-8")))


def load_tester_repair_handoff(work_dir: Path) -> dict[str, Any]:
    path = tester_handoff_path(work_dir)
    if not path.is_file():
        raise TesterRepairResumeError(f"missing {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def validate_tester_repair_resume(work_dir: Path) -> tuple[TesterReport, dict[str, Any]]:
    report = load_tester_report(work_dir)
    handoff = load_tester_repair_handoff(work_dir)
    approved = handoff.get("approved_finding_ids") or []
    if not approved:
        raise TesterRepairResumeError(
            "tester_repair_handoff.json has no approved_finding_ids; triage and REPAIR first, or use full pivot-tester"
        )
    if report.verdict != "issues":
        raise TesterRepairResumeError(
            f"tester_report.json verdict is {report.verdict!r}; resume expects 'issues'"
        )
    return report, handoff


def triage_sets_from_handoff(handoff: dict[str, Any]) -> tuple[set[str], set[str]]:
    approved = {str(x) for x in handoff.get("approved_finding_ids") or []}
    ignored = {str(x) for x in handoff.get("ignored_finding_ids") or []}
    return approved, ignored


_COMPILE_FEEDBACK_STAGES = frozenset({"rules_compile", "rules_merge", None})


def load_last_test_repair_compile_error(work_dir: Path) -> str | None:
    handoff_path = tester_handoff_path(work_dir)
    if handoff_path.is_file():
        try:
            h = json.loads(handoff_path.read_text(encoding="utf-8"))
            stage = h.get("last_repair_error_stage")
            if stage is not None and stage not in _COMPILE_FEEDBACK_STAGES:
                return None
            err = h.get("last_compile_validation_error")
            if isinstance(err, str) and err.strip():
                return err.strip()
        except (json.JSONDecodeError, OSError):
            pass

    trace_path = work_dir / "test_repairer_trace.jsonl"
    if not trace_path.is_file():
        return None
    last_line = ""
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            last_line = line.strip()
    if not last_line:
        return None
    try:
        rec = json.loads(last_line)
    except json.JSONDecodeError:
        return None
    stage = rec.get("error_stage")
    if stage is not None and stage not in _COMPILE_FEEDBACK_STAGES:
        return None
    for key in ("compile_validation_error", "error", "last_error"):
        val = rec.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def enrich_handoff_for_write(
    handoff: dict[str, Any],
    *,
    last_compile_validation_error: str | None = None,
    repair_session_count: int | None = None,
) -> dict[str, Any]:
    out = dict(handoff)
    if last_compile_validation_error is not None:
        err = last_compile_validation_error.strip()
        if err:
            out["last_compile_validation_error"] = err
    if repair_session_count is not None:
        out["repair_session_count"] = repair_session_count
    return out


__all__ = [
    "TesterRepairResumeError",
    "enrich_handoff_for_write",
    "load_last_test_repair_compile_error",
    "load_tester_repair_handoff",
    "load_tester_report",
    "triage_sets_from_handoff",
    "tester_handoff_path",
    "tester_report_path",
    "validate_tester_repair_resume",
]
