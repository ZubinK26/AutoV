from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError as PydanticValidationError

from pivot_pipeline.json_util import extract_first_json_value, parse_json_array
from pivot_pipeline.llm import pivot_llm_complete
from pivot_pipeline.paths import PROMPTS_DIR


class CrossCriticOutputError(Exception):
    """CrossCritic LLM output could not be parsed/validated after repair attempts."""

    def __init__(self, message: str, *, repair_attempts: int = 0) -> None:
        super().__init__(message)
        self.repair_attempts = repair_attempts


def _trim_for_prompt(s: str, limit: int = 6000) -> str:
    t = (s or "").strip()
    if len(t) <= limit:
        return t
    return t[: limit - 40] + "\n…(truncated)…\n"


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


def _coerce_cross_critic_object(data: Any) -> dict[str, Any]:
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        return {
            "verdict": "ISSUES",
            "compared_against": "processed_nl_and_linearized_model",
            "findings": data,
            "audit_trail_bullets": [],
            "notes": "model returned findings array only; wrapped to object",
        }
    raise ValueError(f"expected JSON object or findings array, got {type(data).__name__}")


def _cross_critic_report_from_raw(raw: str) -> CrossCriticReport:
    t = (raw or "").strip()
    if not t:
        return CrossCriticReport(verdict="ISSUES", notes="empty cross critic response", findings=[])

    data = extract_first_json_value(t)
    obj = _coerce_cross_critic_object(data)
    return CrossCriticReport.model_validate(obj)


def parse_cross_critic_response(raw: str) -> CrossCriticReport:
    return _cross_critic_report_from_raw(raw)


def cross_critic_json_repair_max_attempts() -> int:
    raw = os.getenv("PIVOT_CROSS_CRITIC_JSON_REPAIR_MAX", "3").strip()
    try:
        n = int(raw)
        return max(0, min(n, 10))
    except ValueError:
        return 3


def _cross_critic_repair_prompt_template() -> str:
    p = PROMPTS_DIR / "cross_critic_json_repair.md"
    if not p.is_file():
        raise FileNotFoundError(f"missing {p}")
    return p.read_text(encoding="utf-8")


def _cross_critic_repair_diagnostic(raw: str, exc: BaseException) -> str:
    if isinstance(exc, PydanticValidationError):
        lines = ["Schema validation failed:"]
        for err in exc.errors():
            loc = ".".join(str(x) for x in err.get("loc", ()))
            lines.append(f"- {loc}: {err.get('msg', '')}")
        return "\n".join(lines)
    return f"JSON parse: {exc}"


def append_cross_critic_json_repair_trace(work_dir: Path, entry: dict[str, Any]) -> None:
    path = work_dir / "cross_critic_json_repair_trace.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def run_cross_critic_parsed_with_repairs(
    processed_nl: str,
    linearized_model: str,
    *,
    llm: Callable[..., str] = pivot_llm_complete,
    thinking_level: str | None = None,
    max_repairs: int | None = None,
    work_dir: Path | None = None,
) -> tuple[str, CrossCriticReport, int]:
    """
    Run CrossCritic with JSON/schema repair LLM calls after parse failures.

    Returns ``(raw, report, json_repair_attempts)``.
    """
    repairs = max_repairs if max_repairs is not None else cross_critic_json_repair_max_attempts()
    raw = run_cross_critic(
        processed_nl,
        linearized_model,
        llm=llm,
        thinking_level=thinking_level,
    )
    repair_rounds = 0
    last: BaseException | None = None

    for attempt in range(repairs + 1):
        try:
            report = _cross_critic_report_from_raw(raw)
            return raw, report, repair_rounds
        except (json.JSONDecodeError, ValueError, PydanticValidationError) as e:
            last = e

        if work_dir is not None:
            fail_path = work_dir / f"cross_critic_result_invalid_attempt_{attempt}.txt"
            fail_path.write_text(raw, encoding="utf-8")

        if attempt >= repairs:
            diag = _cross_critic_repair_diagnostic(raw, last)  # type: ignore[arg-type]
            raise CrossCriticOutputError(
                f"invalid cross critic JSON after {repairs} repair attempts: {last}\n{diag}",
                repair_attempts=repair_rounds,
            ) from last

        if work_dir is not None:
            append_cross_critic_json_repair_trace(
                work_dir,
                {
                    "attempt": attempt,
                    "repair_round": repair_rounds + 1,
                    "error": str(last),
                },
            )
        r_tmpl = _cross_critic_repair_prompt_template()
        repair_prompt = (
            r_tmpl.replace("<<<INVALID_OUTPUT>>>", _trim_for_prompt(raw) or "(empty)")
            .replace("<<<DIAGNOSTIC>>>", _cross_critic_repair_diagnostic(raw, last))  # type: ignore[arg-type]
        )
        if llm is pivot_llm_complete:
            raw = pivot_llm_complete(repair_prompt, thinking_level=thinking_level)
        else:
            raw = llm(repair_prompt)
        repair_rounds += 1

    raise RuntimeError("cross critic repair: unreachable")


def cross_critic_report_ok(report: CrossCriticReport) -> bool:
    return report.verdict == "PASS"


def format_cross_critic_report_terminal(report: CrossCriticReport, *, numbered: bool = False) -> str:
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
        ordered = sorted(report.findings, key=lambda f: f.id)
        for idx, f in enumerate(ordered, start=1):
            rids = ", ".join(f.rule_ids) if f.rule_ids else "(none)"
            prefix = f"  {idx}. " if numbered else "  "
            lines.append(
                f"{prefix}[{f.id}] {f.severity.upper()} / {f.category}: "
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
    work_dir: Path | None = None,
) -> tuple[str, CrossCriticReport]:
    raw, report, _ = run_cross_critic_parsed_with_repairs(
        processed_nl,
        linearized_model,
        llm=llm,
        thinking_level=thinking_level,
        work_dir=work_dir,
    )
    return raw, report


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
    "CrossCriticOutputError",
    "CrossCriticReport",
    "append_cross_critic_json_repair_trace",
    "cross_critic_handoff_dict",
    "cross_critic_json_repair_max_attempts",
    "cross_critic_report_ok",
    "format_cross_critic_report_terminal",
    "parse_cross_critic_response",
    "run_cross_critic",
    "run_cross_critic_parsed",
    "run_cross_critic_parsed_with_repairs",
]
