from __future__ import annotations

import os
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field

from pivot_pipeline.json_util import parse_json_object
from pivot_pipeline.llm import pivot_llm_complete
from pivot_pipeline.paths import PROMPTS_DIR


class TesterFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    severity: Literal["info", "warn", "critical"] = "warn"
    category: Literal[
        "omission",
        "contradiction",
        "pathway_mislabel",
        "preemption_gap",
        "other",
    ] = "other"
    nl_pointer: str = ""
    formal_pointer: str = ""
    explanation: str = ""
    recommendation: str = ""


class TesterReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verdict: Literal["ok", "issues"]
    findings: list[TesterFinding] = Field(default_factory=list)
    notes: str = ""


def _truncate(s: str, n: int) -> str:
    t = (s or "").strip()
    if len(t) <= n:
        return t
    return t[: n - 40] + "\n…(truncated)…\n"


def _tester_tmpl() -> str:
    p = PROMPTS_DIR / "tester_pivot_semantic.md"
    if not p.is_file():
        raise FileNotFoundError(f"missing {p}")
    return p.read_text(encoding="utf-8")


def format_tester_report_terminal(report: TesterReport) -> str:
    lines = ["", "=== Pivot Tester (semantic) ===", f"Verdict: {report.verdict}", ""]
    if report.findings:
        for f in report.findings:
            lines.append(f"  [{f.id}] {f.severity.upper()} / {f.category}: {f.explanation}")
            if f.recommendation:
                lines.append(f"      → {f.recommendation}")
        lines.append("")
    if report.notes:
        lines.append(f"Notes: {report.notes}\n")
    lines.append("=== End Tester ===\n")
    return "\n".join(lines)


def run_pivot_tester(
    *,
    effective_nl: str,
    synthetic_en: str,
    z3_summary: str | None = None,
    llm: Callable[..., str] = pivot_llm_complete,
) -> tuple[str, TesterReport]:
    tmpl = _tester_tmpl()
    z3s = z3_summary or "(not provided)"
    prompt = (
        tmpl.replace("<<<EFFECTIVE_NL>>>", _truncate(effective_nl, 14000))
        .replace("<<<SYNTHETIC_EN>>>", _truncate(synthetic_en, 14000))
        .replace("<<<Z3_SUMMARY>>>", _truncate(z3s, 4000))
    )
    raw = llm(prompt)
    data = parse_json_object(raw)
    return raw, TesterReport.model_validate(data)


def tester_handoff_from_report(
    report: TesterReport,
    *,
    source_note: str,
) -> dict[str, Any]:
    return {
        "handoff_schema_version": "1",
        "source": "pivot_tester",
        "source_note": source_note,
        "verdict": report.verdict,
        "findings": [f.model_dump(mode="json") for f in report.findings],
        "notes": report.notes,
    }


def critic_repair_max_rounds() -> int:
    raw = os.getenv("PIVOT_CRITIC_SEMANTIC_REPAIR_MAX", "3").strip()
    try:
        return max(0, min(int(raw), 10))
    except ValueError:
        return 3


__all__ = [
    "TesterFinding",
    "TesterReport",
    "format_tester_report_terminal",
    "run_pivot_tester",
    "tester_handoff_from_report",
    "critic_repair_max_rounds",
]
