from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError as PydanticValidationError

from pivot_pipeline.json_util import parse_json_object
from pivot_pipeline.llm import pivot_llm_complete
from pivot_pipeline.paths import PROMPTS_DIR


class TesterOutputError(Exception):
    """Pivot Tester LLM output could not be parsed/validated after repair attempts."""

    def __init__(self, message: str, *, repair_attempts: int = 0) -> None:
        super().__init__(message)
        self.repair_attempts = repair_attempts


class TesterFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    severity: Literal["info", "warn", "critical"] = "warn"
    category: Literal[
        "omission",
        "contradiction",
        "pathway_mislabel",
        "preemption_gap",
        "threshold",
        "wrong_operator",
        "wrong_variable",
        "template_mismatch",
        "preemption_mismatch",
        "ordering",
        "misalignment",
        "other",
    ] = "other"
    nl_pointer: str = ""
    formal_pointer: str = ""
    explanation: str = ""
    recommendation: str = ""


class TesterReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verdict: Literal["ok", "issues"]
    compared_against: str = "processed_nl_and_linearized_model"
    findings: list[TesterFinding] = Field(default_factory=list)
    notes: str = ""


@dataclass(frozen=True)
class TesterRepairContext:
    stage: Literal["json", "schema"]
    messages: list[str]
    invalid_raw_trimmed: str


def _truncate(s: str, n: int) -> str:
    t = (s or "").strip()
    if len(t) <= n:
        return t
    return t[: n - 40] + "\n…(truncated)…\n"


def _trim_for_prompt(s: str, limit: int = 6000) -> str:
    t = (s or "").strip()
    if len(t) <= limit:
        return t
    return t[: limit - 32] + "\n…(truncated for repair prompt)…"


def _pydantic_error_lines(exc: BaseException) -> list[str]:
    if not isinstance(exc, PydanticValidationError):
        return [str(exc)]
    out: list[str] = []
    for err in exc.errors():
        loc = ".".join(str(x) for x in err.get("loc", ()))
        msg = err.get("msg", "")
        if loc:
            out.append(f"- `{loc}`: {msg}")
        else:
            out.append(f"- {msg}")
    return out


def tester_json_repair_max_attempts() -> int:
    raw = os.getenv("PIVOT_TESTER_JSON_REPAIR_MAX", "3").strip()
    try:
        n = int(raw)
        return max(0, min(n, 10))
    except ValueError:
        return 3


def build_tester_repair_context(*, raw_model_output: str, exc: BaseException) -> TesterRepairContext:
    if isinstance(exc, PydanticValidationError):
        return TesterRepairContext(
            stage="schema",
            messages=["Schema validation failed:"] + _pydantic_error_lines(exc),
            invalid_raw_trimmed=_trim_for_prompt(raw_model_output),
        )
    return TesterRepairContext(
        stage="json",
        messages=[f"JSON parse: {exc}"],
        invalid_raw_trimmed=_trim_for_prompt(raw_model_output),
    )


def format_tester_repair_diagnostic(ctx: TesterRepairContext) -> str:
    parts = [f"**Stage:** {ctx.stage}\n", "\n".join(ctx.messages)]
    return "\n".join(parts)


def _tester_tmpl() -> str:
    p = PROMPTS_DIR / "tester_pivot_semantic.md"
    if not p.is_file():
        raise FileNotFoundError(f"missing {p}")
    return p.read_text(encoding="utf-8")


def _tester_repair_prompt_template() -> str:
    p = PROMPTS_DIR / "tester_json_repair.md"
    if not p.is_file():
        raise FileNotFoundError(f"missing {p}")
    return p.read_text(encoding="utf-8")


def _tester_main_prompt(*, processed_nl: str, linearized_model: str) -> str:
    tmpl = _tester_tmpl()
    return (
        tmpl.replace("<<<PROCESSED_NL>>>", _truncate(processed_nl, 14000))
        .replace("<<<LINEARIZED_MODEL>>>", _truncate(linearized_model, 14000))
    )


def _tester_report_from_raw(raw: str) -> TesterReport:
    data = parse_json_object(raw)
    report = TesterReport.model_validate(data)
    if not report.compared_against:
        report = report.model_copy(update={"compared_against": "processed_nl_and_linearized_model"})
    return report


def append_tester_json_repair_trace(work_dir: Path, entry: dict[str, Any]) -> None:
    path = work_dir / "tester_json_repair_trace.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def run_pivot_tester_with_repairs(
    *,
    processed_nl: str,
    linearized_model: str,
    llm: Callable[..., str] = pivot_llm_complete,
    max_repairs: int | None = None,
    work_dir: Path | None = None,
) -> tuple[str, TesterReport, int]:
    """
    Run Pivot Tester with up to ``max_repairs`` JSON/schema repair LLM calls after parse failures.

    Returns ``(raw, report, json_repair_attempts)`` where ``json_repair_attempts`` is the number
    of repair LLM calls used (0 if the first response parsed).
    """
    repairs = max_repairs if max_repairs is not None else tester_json_repair_max_attempts()
    raw = llm(_tester_main_prompt(processed_nl=processed_nl, linearized_model=linearized_model))
    repair_rounds = 0
    last: BaseException | None = None

    for attempt in range(repairs + 1):
        try:
            report = _tester_report_from_raw(raw)
            return raw, report, repair_rounds
        except (json.JSONDecodeError, ValueError, PydanticValidationError) as e:
            last = e

        if work_dir is not None:
            fail_path = work_dir / f"tester_result_invalid_attempt_{attempt}.txt"
            fail_path.write_text(raw, encoding="utf-8")

        if attempt >= repairs:
            ctx = build_tester_repair_context(raw_model_output=raw, exc=last)  # type: ignore[arg-type]
            diag = format_tester_repair_diagnostic(ctx)
            raise TesterOutputError(
                f"invalid tester JSON after {repairs} repair attempts: {last}\n{diag}",
                repair_attempts=repair_rounds,
            ) from last

        ctx = build_tester_repair_context(raw_model_output=raw, exc=last)  # type: ignore[arg-type]
        if work_dir is not None:
            append_tester_json_repair_trace(
                work_dir,
                {
                    "attempt": attempt,
                    "repair_round": repair_rounds + 1,
                    "stage": ctx.stage,
                    "error": str(last),
                },
            )
        r_tmpl = _tester_repair_prompt_template()
        repair_prompt = (
            r_tmpl.replace("<<<INVALID_OUTPUT>>>", ctx.invalid_raw_trimmed or "(empty)")
            .replace("<<<DIAGNOSTIC>>>", format_tester_repair_diagnostic(ctx))
        )
        raw = llm(repair_prompt)
        repair_rounds += 1

    raise RuntimeError("tester repair: unreachable")


def run_pivot_tester(
    *,
    processed_nl: str,
    linearized_model: str,
    llm: Callable[..., str] = pivot_llm_complete,
    work_dir: Path | None = None,
) -> tuple[str, TesterReport]:
    raw, report, _ = run_pivot_tester_with_repairs(
        processed_nl=processed_nl,
        linearized_model=linearized_model,
        llm=llm,
        work_dir=work_dir,
    )
    return raw, report


def format_tester_report_terminal(report: TesterReport) -> str:
    lines = [
        "",
        "=== Pivot Tester (NL ↔ linearized IR) ===",
        f"Verdict: {report.verdict}",
        f"Compared: {report.compared_against}",
        "",
    ]
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
        "compared_against": report.compared_against,
        "findings": [f.model_dump(mode="json") for f in report.findings],
        "notes": report.notes,
    }


def critic_repair_max_rounds() -> int:
    """User REPAIR sessions at DRIFT gate; 0 = unlimited (default)."""
    raw = os.getenv("PIVOT_CRITIC_SEMANTIC_REPAIR_MAX", "0").strip()
    try:
        return max(0, min(int(raw), 10))
    except ValueError:
        return 0


def critic_repair_compile_attempts_max() -> int:
    """LLM repairer invocations per user REPAIR before giving up on compile (clamped 1..10)."""
    raw = os.getenv("PIVOT_CRITIC_SEMANTIC_REPAIR_COMPILE_ATTEMPTS", "5").strip()
    try:
        return max(1, min(int(raw), 10))
    except ValueError:
        return 5


def critic_semantic_repair_count_api_as_attempt() -> bool:
    raw = os.getenv("PIVOT_CRITIC_SEMANTIC_REPAIR_COUNT_API_AS_ATTEMPT", "0").strip().lower()
    return raw in ("1", "true", "yes")


def critic_semantic_repair_max_findings() -> int:
    """Max approved findings per REPAIR; 0 = unlimited."""
    raw = os.getenv("PIVOT_CRITIC_SEMANTIC_REPAIR_MAX_FINDINGS", "0").strip()
    try:
        return max(0, min(int(raw), 50))
    except ValueError:
        return 0


__all__ = [
    "TesterFinding",
    "TesterOutputError",
    "TesterRepairContext",
    "TesterReport",
    "append_tester_json_repair_trace",
    "build_tester_repair_context",
    "critic_repair_compile_attempts_max",
    "critic_repair_max_rounds",
    "critic_semantic_repair_count_api_as_attempt",
    "critic_semantic_repair_max_findings",
    "format_tester_repair_diagnostic",
    "format_tester_report_terminal",
    "run_pivot_tester",
    "run_pivot_tester_with_repairs",
    "tester_handoff_from_report",
    "tester_json_repair_max_attempts",
]
