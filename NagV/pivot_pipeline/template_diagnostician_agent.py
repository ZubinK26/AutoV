"""Template Diagnostician — LLM explanations for template suite failures."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError as PydanticValidationError

from pivot_pipeline.json_util import extract_first_json_value
from pivot_pipeline.llm import pivot_llm_complete
from pivot_pipeline.paths import PROMPTS_DIR


class TemplateDiagnosticOutputError(Exception):
    def __init__(self, message: str, *, repair_attempts: int = 0) -> None:
        super().__init__(message)
        self.repair_attempts = repair_attempts


class TemplateDiagnosticFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    severity: Literal["info", "warn", "critical"] = "warn"
    category: Literal[
        "policy_vs_nl",
        "vacuous_k_of_n",
        "variable_collision",
        "trigger_inconsistency",
        "template_golden",
        "template_world",
        "inconclusive_ambiguous",
        "other",
    ] = "other"
    instance_ids: list[str] = Field(default_factory=list)
    rule_ids: list[str] = Field(default_factory=list)
    nl_pointer: str = ""
    explanation: str = ""
    recommendation: str = ""
    blame: Literal[
        "policy_ir",
        "template_golden",
        "template_world",
        "inconclusive_ambiguous",
    ] = "policy_ir"
    repair_target: Literal["rules", "suite", "none"] = "rules"


class TemplateDiagnosticReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1"] = "1"
    verdict: Literal["PASS", "ISSUES"]
    suite_summary: dict[str, int] = Field(default_factory=dict)
    findings: list[TemplateDiagnosticFinding] = Field(default_factory=list)
    audit_trail_bullets: list[str] = Field(default_factory=list)
    notes: str = ""


def _trim(s: str, limit: int = 8000) -> str:
    t = (s or "").strip()
    if len(t) <= limit:
        return t
    return t[: limit - 40] + "\n…(truncated)…\n"


def _coerce_object(data: Any) -> dict[str, Any]:
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        return {
            "verdict": "ISSUES",
            "findings": data,
            "suite_summary": {},
            "audit_trail_bullets": [],
            "notes": "wrapped findings array",
        }
    raise ValueError(f"expected object or array, got {type(data).__name__}")


def parse_template_diagnostic_response(raw: str) -> TemplateDiagnosticReport:
    t = (raw or "").strip()
    if not t:
        return TemplateDiagnosticReport(verdict="ISSUES", notes="empty response")
    data = extract_first_json_value(t)
    obj = _coerce_object(data)
    obj.setdefault("schema_version", "1")
    return TemplateDiagnosticReport.model_validate(obj)


def template_diagnostic_system_prompt() -> str:
    p = PROMPTS_DIR / "template_diagnostician.md"
    if not p.is_file():
        raise FileNotFoundError(f"missing {p}")
    return p.read_text(encoding="utf-8")


def format_template_diagnostic_terminal(
    report: TemplateDiagnosticReport,
    *,
    suite_summary: dict[str, int] | None = None,
) -> str:
    s = suite_summary or report.suite_summary
    lines = [
        "=== Template suite diagnostic ===",
        f"Verdict: {report.verdict}",
        f"Suite: passed={s.get('passed', 0)} failed={s.get('failed', 0)} "
        f"inconclusive={s.get('inconclusive', 0)} errors={s.get('errors', 0)}",
        "",
    ]
    if not report.findings:
        lines.append("(no findings)")
        return "\n".join(lines)
    for idx, f in enumerate(report.findings, start=1):
        lines.append(
            f"Finding {idx} of {len(report.findings)}: [{f.id}] {f.severity} / {f.category}"
        )
        if f.instance_ids:
            lines.append(f"  Instances: {', '.join(f.instance_ids)}")
        if f.rule_ids:
            lines.append(f"  Rules: {', '.join(f.rule_ids)}")
        if f.nl_pointer:
            lines.append(f"  NL: {f.nl_pointer}")
        lines.append(f"  Problem: {f.explanation}")
        if f.recommendation:
            lines.append(f"  Recommendation: {f.recommendation}")
        elig = " [REPAIR-ELIGIBLE]" if finding_repair_eligible(f) else ""
        lines.append(f"  Blame: {f.blame} → repair_target={f.repair_target}{elig}")
        lines.append("")
    if report.notes:
        lines.append(f"Notes: {report.notes}")
    return "\n".join(lines)


def finding_repair_eligible(f: TemplateDiagnosticFinding) -> bool:
    return f.blame == "policy_ir" and f.repair_target == "rules"


def template_diagnostic_json_repair_max() -> int:
    raw = os.getenv("PIVOT_TEMPLATE_DIAGNOSTIC_JSON_REPAIR_MAX", "3").strip()
    try:
        return max(0, min(int(raw), 10))
    except ValueError:
        return 3


def run_template_diagnostician(
    *,
    processed_nl: str,
    linearized_model: str,
    failure_bundles: list[dict[str, Any]],
    suite_summary: dict[str, int],
    llm: Callable[..., str] = pivot_llm_complete,
) -> tuple[str, TemplateDiagnosticReport]:
    sys = template_diagnostic_system_prompt()
    payload = {
        "processed_nl_excerpt": _trim(processed_nl, 14_000),
        "linearized_model_excerpt": _trim(linearized_model, 14_000),
        "suite_summary": suite_summary,
        "failure_bundles": failure_bundles[:20],
    }
    user = json.dumps(payload, ensure_ascii=False, indent=2)
    prompt = sys + "\n\n---\n\n## Failure payload JSON\n\n" + user
    if llm is pivot_llm_complete:
        raw = pivot_llm_complete(prompt)
    else:
        raw = llm(prompt)
    report = parse_template_diagnostic_response(raw)
    report.suite_summary = dict(suite_summary)
    if not report.findings and report_needs_issues(suite_summary):
        report.verdict = "ISSUES"
    elif report.findings:
        report.verdict = "ISSUES"
    else:
        report.verdict = "PASS"
    return raw, report


def report_needs_issues(summary: dict[str, int]) -> bool:
    return int(summary.get("failed", 0)) + int(summary.get("inconclusive", 0)) > 0


def run_template_diagnostician_with_repairs(
    *,
    processed_nl: str,
    linearized_model: str,
    failure_bundles: list[dict[str, Any]],
    suite_summary: dict[str, int],
    llm: Callable[..., str] = pivot_llm_complete,
    max_repairs: int | None = None,
) -> tuple[str, TemplateDiagnosticReport, int]:
    cap = template_diagnostic_json_repair_max() if max_repairs is None else max_repairs
    last_raw = ""
    last_err: BaseException | None = None
    for attempt in range(cap + 1):
        try:
            raw, report = run_template_diagnostician(
                processed_nl=processed_nl,
                linearized_model=linearized_model,
                failure_bundles=failure_bundles,
                suite_summary=suite_summary,
                llm=llm,
            )
            return raw, report, attempt
        except (ValueError, PydanticValidationError) as e:
            last_err = e
            last_raw = ""
            if attempt >= cap:
                break
    raise TemplateDiagnosticOutputError(
        f"template diagnostician parse failed after {cap} repairs: {last_err}",
        repair_attempts=cap,
    )


def template_repair_handoff_dict(
    report: TemplateDiagnosticReport,
    *,
    approved_ids: list[str],
    ignored_ids: list[str],
    processed_nl_path: Path,
    template_run_report_path: Path,
    suite_path: Path,
    failure_bundles: list[dict[str, Any]],
    source_note: str = "approved template findings",
    last_compile_validation_error: str | None = None,
    last_repair_error_stage: str | None = None,
    repair_session_count: int = 0,
) -> dict[str, Any]:
    from pivot_pipeline.template_repair_strategy import enrich_findings_with_strategies

    approved_set = set(approved_ids)
    raw_findings = [f.model_dump(mode="json") for f in report.findings if f.id in approved_set]
    h: dict[str, Any] = {
        "handoff_schema_version": "1",
        "source": "template_suite",
        "source_note": source_note,
        "verdict": report.verdict,
        "approved_finding_ids": sorted(approved_ids),
        "ignored_finding_ids": sorted(ignored_ids),
        "findings": enrich_findings_with_strategies(raw_findings, failure_bundles),
        "processed_nl_path": str(processed_nl_path.resolve()),
        "template_run_report_path": str(template_run_report_path.resolve()),
        "suite_path": str(suite_path.resolve()),
        "failure_bundles": failure_bundles,
        "notes": report.notes,
        "repair_session_count": repair_session_count,
    }
    if last_compile_validation_error:
        h["last_compile_validation_error"] = last_compile_validation_error
    if last_repair_error_stage:
        h["last_repair_error_stage"] = last_repair_error_stage
    return h


__all__ = [
    "TemplateDiagnosticFinding",
    "TemplateDiagnosticOutputError",
    "TemplateDiagnosticReport",
    "finding_repair_eligible",
    "format_template_diagnostic_terminal",
    "parse_template_diagnostic_response",
    "run_template_diagnostician_with_repairs",
    "template_repair_handoff_dict",
]
