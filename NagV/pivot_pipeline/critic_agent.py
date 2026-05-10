from __future__ import annotations

import json
import re
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field

from pivot_pipeline.json_util import parse_json_object
from pivot_pipeline.llm import pivot_llm_complete
from pivot_pipeline.paths import PROMPTS_DIR


class CriticFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    severity: Literal["info", "warn", "critical"] = "warn"
    category: Literal[
        "omission",
        "contradiction",
        "pathway",
        "preemption",
        "threshold",
        "scoping",
        "other",
    ] = "other"
    nl_pointer: str = ""
    synthetic_pointer: str = ""
    explanation: str = ""


class CriticReport(BaseModel):
    """Structured pivot critic output (vs effective NL and synthetic IR markdown)."""

    model_config = ConfigDict(extra="forbid")

    verdict: Literal["PASS", "DRIFT"]
    compared_against: Literal["effective_nl"] = "effective_nl"
    findings: list[CriticFinding] = Field(default_factory=list)
    audit_trail_bullets: list[str] = Field(default_factory=list)
    notes: str = ""


def _legacy_verdict_from_text(raw: str) -> Literal["PASS", "DRIFT"] | None:
    t = (raw or "").strip()
    matches = list(re.finditer(r"\[VERDICT:\s*([^\]]+)\]", t, re.IGNORECASE))
    if not matches:
        return None
    last = matches[-1].group(1).strip().upper()
    if last == "PASS":
        return "PASS"
    if last == "DRIFT":
        return "DRIFT"
    return "DRIFT"


def parse_critic_response(raw: str) -> CriticReport:
    """
    Parse LLM critic output: prefer one JSON object; fall back to legacy ``[VERDICT: …]`` line.
    """
    t = (raw or "").strip()
    if not t:
        return CriticReport(verdict="DRIFT", notes="empty critic response", findings=[])

    try:
        obj = parse_json_object(t)
        return CriticReport.model_validate(obj)
    except Exception:
        pass

    legacy = _legacy_verdict_from_text(t)
    if legacy is None:
        return CriticReport(
            verdict="DRIFT",
            notes="critic response was not valid JSON and had no [VERDICT: …] line",
            audit_trail_bullets=[t[:500] + ("…" if len(t) > 500 else "")],
        )
    bullets: list[str] = []
    for line in t.splitlines():
        s = line.strip()
        if s.startswith(("-", "*")) and "[VERDICT" not in s:
            bullets.append(s.lstrip("-* ").strip())
    return CriticReport(verdict=legacy, findings=[], audit_trail_bullets=bullets[:20], notes="parsed legacy non-JSON critic")


def pivot_critic_passed(raw: str) -> bool:
    """True when structured verdict is PASS, or legacy last line was PASS."""
    try:
        return parse_critic_response(raw).verdict == "PASS"
    except Exception:
        return _legacy_verdict_from_text(raw) == "PASS"


def critic_report_passed(report: CriticReport) -> bool:
    return report.verdict == "PASS"


def format_critic_report_terminal(report: CriticReport) -> str:
    lines = [
        "",
        "=== Pivot critic (structured) ===",
        f"Verdict: {report.verdict}",
        f"Compared against: {report.compared_against} (NL text the pipeline used for formalization)",
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
            lines.append(
                f"  [{f.id}] {f.severity.upper()} / {f.category}: "
                f"{f.explanation or '(no explanation)'}"
            )
            if f.nl_pointer:
                lines.append(f"      NL: {f.nl_pointer}")
            if f.synthetic_pointer:
                lines.append(f"      Synthetic: {f.synthetic_pointer}")
        lines.append("")
    if report.notes:
        lines.append(f"Notes: {report.notes}")
        lines.append("")
    lines.append("=== End critic ===")
    lines.append("")
    return "\n".join(lines)


def _critic_prompt_template() -> str:
    path = PROMPTS_DIR / "pivot_critic.md"
    if not path.is_file():
        raise FileNotFoundError(f"missing critic prompt: {path}")
    return path.read_text(encoding="utf-8")


def run_pivot_critic(
    nl_policy: str,
    synthetic_en: str,
    *,
    varprod_rules_linearized: str = "",
    llm: Callable[..., str] = pivot_llm_complete,
    thinking_level: str | None = None,
) -> str:
    tmpl = _critic_prompt_template()
    vp = (varprod_rules_linearized or "").strip()
    if not vp:
        vp = "(none — no LOGICAL_IMPLICATION rules with varprod_cmp in this policy snapshot)"
    prompt = (
        tmpl.replace("<<<NL_POLICY>>>", nl_policy)
        .replace("<<<SYNTHETIC_EN>>>", synthetic_en)
        .replace("<<<VARPROD_RULES_LINEARIZED>>>", vp)
    )
    if llm is pivot_llm_complete:
        return pivot_llm_complete(prompt, thinking_level=thinking_level)
    return llm(prompt)


def run_pivot_critic_parsed(
    nl_policy: str,
    synthetic_en: str,
    *,
    varprod_rules_linearized: str = "",
    llm: Callable[..., str] = pivot_llm_complete,
    thinking_level: str | None = None,
) -> tuple[str, CriticReport]:
    raw = run_pivot_critic(
        nl_policy,
        synthetic_en,
        varprod_rules_linearized=varprod_rules_linearized,
        llm=llm,
        thinking_level=thinking_level,
    )
    return raw, parse_critic_response(raw)


def critic_handoff_dict(report: CriticReport, *, source_note: str) -> dict[str, Any]:
    return {
        "handoff_schema_version": "1",
        "source": "pivot_critic",
        "source_note": source_note,
        "verdict": report.verdict,
        "compared_against": report.compared_against,
        "findings": [f.model_dump(mode="json") for f in report.findings],
        "audit_trail_bullets": list(report.audit_trail_bullets),
        "notes": report.notes,
    }


__all__ = [
    "CriticFinding",
    "CriticReport",
    "critic_handoff_dict",
    "critic_report_passed",
    "format_critic_report_terminal",
    "parse_critic_response",
    "pivot_critic_passed",
    "run_pivot_critic",
    "run_pivot_critic_parsed",
]
