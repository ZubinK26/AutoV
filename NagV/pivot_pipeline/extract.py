from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal

from pivot_pipeline.json_util import parse_json_object
from pivot_pipeline.llm import pivot_llm_complete
from pivot_pipeline.paths import PROMPTS_DIR, read_v1_policy_encodability_contract


def is_abort_response(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    if "def " in t:
        return False
    if t.startswith("ABORT:"):
        return True
    phrase = "ABORT: Ruleset exceeds decidable scope."
    return phrase in t


class ExtractAbort(Exception):
    def __init__(self, line_index: int, line: str, raw: str) -> None:
        super().__init__(f"line {line_index}: extraction ABORT — {line!r}")
        self.line_index = line_index
        self.line = line
        self.raw = raw


class ExtractValidationError(Exception):
    def __init__(self, line_index: int, message: str, rule: dict[str, Any] | None = None) -> None:
        super().__init__(f"line {line_index}: {message}")
        self.line_index = line_index
        self.message = message
        self.rule = rule


@dataclass(frozen=True)
class RepairContext:
    """Structured context for schema/JSON repair of one extract line."""

    line_index: int
    line: str
    stage: Literal["json", "schema", "cross_rule"]
    messages: list[str]
    invalid_raw_trimmed: str
    partial_rule: dict[str, Any] | None = None


_PREEMPT_FORCE_ACTIONS = frozenset({"BYPASS_RULE", "FORCE_SATISFIED", "FORCE_UNSATISFIED"})


def _schema_repair_max_attempts() -> int:
    raw = os.getenv("PIVOT_EXTRACT_SCHEMA_REPAIR_MAX", "3").strip()
    try:
        n = int(raw)
        return max(0, min(n, 10))
    except ValueError:
        return 3


def _trim_for_prompt(s: str, limit: int = 6000) -> str:
    t = (s or "").strip()
    if len(t) <= limit:
        return t
    return t[: limit - 32] + "\n…(truncated for repair prompt)…"


def _pydantic_error_lines(exc: BaseException) -> list[str]:
    from pydantic import ValidationError as PydanticValidationError

    if not isinstance(exc, PydanticValidationError):
        return [str(exc)]
    out: list[str] = []
    for err in exc.errors():
        loc = ".".join(str(x) for x in err.get("loc", ()))
        msg = err.get("msg", "")
        typ = err.get("type", "")
        hint = ""
        if typ == "missing":
            hint = " — add this field with the correct type."
        elif typ in ("enum", "less_than_equal", "greater_than_equal"):
            hint = " — use an allowed value exactly as in the extractor spec."
        if loc:
            out.append(f"- `{loc}`: {msg}{hint}")
        else:
            out.append(f"- {msg}{hint}")
    return out


def _extract_validation_stage(msg: str) -> Literal["schema", "cross_rule"]:
    m = msg.lower()
    if any(
        x in m
        for x in (
            "target_rule_id",
            "preemption",
            "non-premption",
            "non-premption",
            "another preemption",
            "earlier rule",
            "requires non-null",
        )
    ):
        return "cross_rule"
    return "schema"


def build_repair_context(
    *,
    line_index: int,
    line: str,
    raw_model_output: str,
    exc: BaseException,
    partial_rule: dict[str, Any] | None = None,
) -> RepairContext:
    if isinstance(exc, ExtractValidationError):
        stage = _extract_validation_stage(exc.message)
        lines = [f"Validation: {exc.message}"]
        if exc.__cause__ is not None:
            lines.extend(_pydantic_error_lines(exc.__cause__))
        return RepairContext(
            line_index=line_index,
            line=line,
            stage=stage,
            messages=lines,
            invalid_raw_trimmed=_trim_for_prompt(raw_model_output),
            partial_rule=partial_rule if partial_rule is not None else exc.rule,
        )
    msg = str(exc)
    return RepairContext(
        line_index=line_index,
        line=line,
        stage="json",
        messages=[f"JSON parse: {msg}"],
        invalid_raw_trimmed=_trim_for_prompt(raw_model_output),
        partial_rule=partial_rule,
    )


def format_repair_diagnostic(ctx: RepairContext) -> str:
    parts = [f"**Stage:** {ctx.stage}\n"]
    parts.append("\n".join(ctx.messages))
    if ctx.partial_rule:
        try:
            parts.append("\n\n**Partial rule (may be invalid):**\n" + json.dumps(ctx.partial_rule, indent=2)[:4000])
        except (TypeError, ValueError):
            pass
    return "\n".join(parts)


def _repair_prompt_template() -> str:
    path = PROMPTS_DIR / "extract_schema_repair.md"
    if not path.is_file():
        raise FileNotFoundError(f"missing extract_schema_repair prompt: {path}")
    return path.read_text(encoding="utf-8")


def validate_preemption_cross_rule_targets(
    rule: dict[str, Any],
    *,
    line_index: int,
    prior_rules: list[dict[str, Any]],
) -> None:
    """Require PREEMPTION FORCE/BYPASS targets to reference an earlier non-PREEMPTION rule_id."""
    if rule.get("template_class") != "PREEMPTION":
        return
    action = rule.get("action")
    if action not in _PREEMPT_FORCE_ACTIONS:
        return
    tid = rule.get("target_rule_id")
    if not tid or not isinstance(tid, str) or not tid.strip():
        raise ExtractValidationError(
            line_index,
            "PREEMPTION with action FORCE_SATISFIED, FORCE_UNSATISFIED, or BYPASS_RULE requires "
            "non-null target_rule_id equal to an earlier rule's rule_id (not another PREEMPTION).",
            rule,
        )
    tid = tid.strip()
    by_id = {str(r.get("rule_id")): r for r in prior_rules if r.get("rule_id")}
    if tid not in by_id:
        known = ", ".join(sorted(by_id.keys())) or "(none yet)"
        raise ExtractValidationError(
            line_index,
            f"target_rule_id {tid!r} must name an earlier rule in this policy. Known earlier ids: {known}",
            rule,
        )
    tgt_tc = by_id[tid].get("template_class")
    if tgt_tc == "PREEMPTION":
        raise ExtractValidationError(
            line_index,
            f"target_rule_id {tid!r} must not reference another PREEMPTION rule.",
            rule,
        )


def _extract_prompt_template() -> str:
    path = PROMPTS_DIR / "extractor.md"
    if not path.is_file():
        raise FileNotFoundError(f"missing extractor prompt: {path}")
    base = path.read_text(encoding="utf-8")
    return (
        base
        + "\n\n---\n\n## Normative v1 encodability (shared with Phase 0 pivot WFM)\n\n"
        + read_v1_policy_encodability_contract()
    )


def _model_map() -> dict[str, type]:
    from pivot_pipeline.ir import (
        ArithmeticEvaluation,
        ConstantRelational,
        ExclusiveChoice,
        LogicalIff,
        LogicalImplication,
        Preemption,
        SetInclusion,
        VariableRelational,
    )

    return {
        "CONSTANT_RELATIONAL": ConstantRelational,
        "SET_INCLUSION": SetInclusion,
        "VARIABLE_RELATIONAL": VariableRelational,
        "ARITHMETIC_EVALUATION": ArithmeticEvaluation,
        "LOGICAL_IMPLICATION": LogicalImplication,
        "PREEMPTION": Preemption,
        "EXCLUSIVE_CHOICE": ExclusiveChoice,
        "LOGICAL_IFF": LogicalIff,
    }


def validate_rule_dict(rule: dict[str, Any], *, line_index: int) -> dict[str, Any]:
    t = rule.get("template_class")
    if not t:
        raise ExtractValidationError(line_index, "missing template_class", rule)
    mm = _model_map()
    cls = mm.get(str(t))
    if cls is None:
        raise ExtractValidationError(line_index, f"unknown template_class {t!r}", rule)
    try:
        m = cls.model_validate(rule)
    except Exception as e:
        from pydantic import ValidationError as PydanticValidationError

        if isinstance(e, PydanticValidationError):
            bullet = "\n".join(_pydantic_error_lines(e))
            raise ExtractValidationError(line_index, f"schema:\n{bullet}", rule) from e
        raise ExtractValidationError(line_index, f"schema: {e}", rule) from e
    return m.model_dump(mode="json")


def _rule_from_raw_output(
    line_index: int,
    line: str,
    raw: str,
    prior_rules: list[dict[str, Any]],
    *,
    apply_cross_rule: bool,
) -> dict[str, Any]:
    if is_abort_response(raw):
        raise ExtractAbort(line_index, line, raw)
    try:
        data = parse_json_object(raw)
    except (ValueError, json.JSONDecodeError) as e:
        raise e
    rid = f"R{line_index:04d}"
    data["rule_id"] = rid
    validated = validate_rule_dict(data, line_index=line_index)
    if apply_cross_rule:
        validate_preemption_cross_rule_targets(validated, line_index=line_index, prior_rules=prior_rules)
    return validated


def extract_one_line_with_repairs(
    line_index: int,
    line: str,
    *,
    tmpl: str,
    llm: Callable[..., str] = pivot_llm_complete,
    prior_rules: list[dict[str, Any]],
    max_repairs: int | None = None,
    apply_cross_rule: bool = True,
) -> dict[str, Any]:
    """
    Extract one line with up to ``max_repairs`` repair LLM calls after JSON/schema/cross-rule failures.
    """
    if not line.strip():
        raise ExtractValidationError(line_index, "empty line after strip")
    repairs = max_repairs if max_repairs is not None else _schema_repair_max_attempts()
    raw = llm(tmpl.replace("<<<LINE>>>", line))
    for attempt in range(repairs + 1):
        try:
            return _rule_from_raw_output(
                line_index,
                line,
                raw,
                prior_rules,
                apply_cross_rule=apply_cross_rule,
            )
        except ExtractAbort:
            raise
        except (ValueError, json.JSONDecodeError, ExtractValidationError) as e:
            last = e
        if attempt >= repairs:
            if isinstance(last, ExtractValidationError):
                raise last
            ctx = build_repair_context(
                line_index=line_index,
                line=line,
                raw_model_output=raw,
                exc=last,
            )
            raise ExtractValidationError(
                line_index,
                f"invalid JSON after {repairs} repair attempts: {last}\n{format_repair_diagnostic(ctx)}",
            ) from last

        ctx = build_repair_context(
            line_index=line_index,
            line=line,
            raw_model_output=raw,
            exc=last,
        )
        r_tmpl = _repair_prompt_template()
        diag = format_repair_diagnostic(ctx)
        repair_prompt = (
            r_tmpl.replace("<<<LINE>>>", line)
            .replace("<<<LINE_INDEX>>>", str(line_index))
            .replace("<<<INVALID_OUTPUT>>>", ctx.invalid_raw_trimmed or "(empty)")
            .replace("<<<DIAGNOSTIC>>>", diag)
        )
        raw = llm(repair_prompt)

    raise RuntimeError("extract repair: unreachable")


def extract_one_line(
    line_index: int,
    line: str,
    *,
    tmpl: str,
    llm: Callable[..., str] = pivot_llm_complete,
    prior_rules: list[dict[str, Any]] | None = None,
    max_repairs: int | None = None,
    apply_cross_rule: bool = True,
) -> dict[str, Any]:
    return extract_one_line_with_repairs(
        line_index,
        line,
        tmpl=tmpl,
        llm=llm,
        prior_rules=list(prior_rules or []),
        max_repairs=max_repairs,
        apply_cross_rule=apply_cross_rule,
    )


def extract_rules_from_lines(
    lines: list[str],
    *,
    llm: Callable[..., str] = pivot_llm_complete,
    max_workers: int | None = None,
) -> list[dict[str, Any]]:
    if not lines:
        return []
    tmpl = _extract_prompt_template()
    workers = max_workers if max_workers is not None else int(os.getenv("PIVOT_EXTRACT_WORKERS", "4"))
    workers = max(1, workers)

    if workers == 1:
        out: list[dict[str, Any]] = []
        for i, ln in enumerate(lines):
            out.append(
                extract_one_line_with_repairs(
                    i + 1,
                    ln,
                    tmpl=tmpl,
                    llm=llm,
                    prior_rules=list(out),
                    apply_cross_rule=True,
                )
            )
        return out

    def job(idx_line: tuple[int, str]) -> tuple[int, dict[str, Any]]:
        idx, ln = idx_line
        return idx, extract_one_line_with_repairs(
            idx,
            ln,
            tmpl=tmpl,
            llm=llm,
            prior_rules=[],
            apply_cross_rule=False,
        )

    indexed = [(i + 1, ln) for i, ln in enumerate(lines)]
    out_pairs: list[tuple[int, dict[str, Any]]] = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        out_pairs = list(ex.map(job, indexed))
    return [r for _i, r in out_pairs]


def extract_rules_from_nl_path(
    nl_path: Path,
    *,
    llm: Callable[..., str] = pivot_llm_complete,
    max_workers: int | None = None,
) -> list[dict[str, Any]]:
    from wfm_orchestration.nl_chunk_policy_pipeline import parse_nl_rules

    text = nl_path.read_text(encoding="utf-8")
    lines = parse_nl_rules(text)
    return extract_rules_from_lines(lines, llm=llm, max_workers=max_workers)


__all__ = [
    "ExtractAbort",
    "ExtractValidationError",
    "RepairContext",
    "build_repair_context",
    "extract_one_line",
    "extract_one_line_with_repairs",
    "extract_rules_from_lines",
    "extract_rules_from_nl_path",
    "format_repair_diagnostic",
    "is_abort_response",
    "validate_preemption_cross_rule_targets",
    "validate_rule_dict",
]
