from __future__ import annotations

import json
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field

from pivot_pipeline.json_util import parse_json_object
from pivot_pipeline.llm import pivot_llm_complete
from pivot_pipeline.paths import PROMPTS_DIR


class CrossCriticFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    severity: Literal["info", "warn", "critical"] = "warn"
    category: Literal["outcome_split", "preemption", "inconsistency", "other"] = "other"
    rule_ids: list[str] = Field(default_factory=list)
    explanation: str = ""
    recommendation: str = ""


class CrossCriticReport(BaseModel):
    """Structured CrossCritic output (IR coherence vs processed NL + linearized model)."""

    model_config = ConfigDict(extra="forbid")

    verdict: Literal["PASS", "ISSUES"]
    compared_against: Literal["processed_nl_and_linearized_model"] = "processed_nl_and_linearized_model"
    findings: list[CrossCriticFinding] = Field(default_factory=list)
    audit_trail_bullets: list[str] = Field(default_factory=list)
    notes: str = ""


def parse_cross_critic_response(raw: str) -> CrossCriticReport:
    t = (raw or "").strip()
    if not t:
        return CrossCriticReport(verdict="ISSUES", notes="empty cross critic response", findings=[])

    obj = parse_json_object(t)
    return CrossCriticReport.model_validate(obj)


def cross_critic_report_ok(report: CrossCriticReport) -> bool:
    return report.verdict == "PASS"


def format_cross_critic_report_terminal(report: CrossCriticReport) -> str:
    lines = [
        "",
        "=== CrossCritic (IR coherence) ===",
        f"Verdict: {report.verdict}",
        "Compared against: processed NL + linearized rules (not NL vs synthetic doc)",
        "",
    ]
    if report.audit_trail_bullets:
        lines.append("Audit trail:")
        for b in report.audit_trail_bullets:
            lines.append(f"  - {b}")
        lines.append("")
    if report.findings:
        lines.append("Findings:")
        for f in report.findings:
            rids = ", ".join(f.rule_ids) if f.rule_ids else "(none)"
            lines.append(
                f"  [{f.id}] {f.severity.upper()} / {f.category}: "
                f"{f.explanation or '(no explanation)'} (rules: {rids})"
            )
            if f.recommendation:
                lines.append(f"      → {f.recommendation}")
        lines.append("")
    if report.notes:
        lines.append(f"Notes: {report.notes}")
        lines.append("")
    lines.append("=== End CrossCritic ===")
    lines.append("")
    return "\n".join(lines)


def _cross_critic_prompt_template() -> str:
    path = PROMPTS_DIR / "cross_critic.md"
    if not path.is_file():
        raise FileNotFoundError(f"missing cross critic prompt: {path}")
    return path.read_text(encoding="utf-8")


def run_cross_critic(
    processed_nl: str,
    linearized_model: str,
    *,
    llm: Callable[..., str] = pivot_llm_complete,
    thinking_level: str | None = None,
) -> str:
    tmpl = _cross_critic_prompt_template()
    prompt = (
        tmpl.replace("<<<PROCESSED_NL>>>", processed_nl)
        .replace("<<<LINEARIZED_MODEL>>>", linearized_model)
    )
    if llm is pivot_llm_complete:
        return pivot_llm_complete(prompt, thinking_level=thinking_level)
    return llm(prompt)


def run_cross_critic_parsed(
    processed_nl: str,
    linearized_model: str,
    *,
    llm: Callable[..., str] = pivot_llm_complete,
    thinking_level: str | None = None,
) -> tuple[str, CrossCriticReport]:
    raw = run_cross_critic(processed_nl, linearized_model, llm=llm, thinking_level=thinking_level)
    return raw, parse_cross_critic_response(raw)


def cross_critic_handoff_dict(report: CrossCriticReport, *, source_note: str) -> dict[str, Any]:
    return {
        "handoff_schema_version": "1",
        "source": "cross_critic",
        "source_note": source_note,
        "verdict": report.verdict,
        "compared_against": report.compared_against,
        "findings": [f.model_dump(mode="json") for f in report.findings],
        "audit_trail_bullets": list(report.audit_trail_bullets),
        "notes": report.notes,
    }


__all__ = [
    "CrossCriticFinding",
    "CrossCriticReport",
    "cross_critic_handoff_dict",
    "cross_critic_report_ok",
    "format_cross_critic_report_terminal",
    "parse_cross_critic_response",
    "run_cross_critic",
    "run_cross_critic_parsed",
]
