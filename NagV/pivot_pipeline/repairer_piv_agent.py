from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field

from pivot_pipeline.json_util import parse_json_object
from pivot_pipeline.llm import pivot_llm_complete
from pivot_pipeline.paths import (
    PROMPTS_DIR,
    read_repairer_ir_normative,
    read_semantic_repairer_ir_addendum,
    read_temporal_surrogates_addendum,
    read_vnext_template_examples,
)
from pivot_pipeline.test_repair_rules_payload import (
    MergeRepairerOutputError,
    build_rules_payload_stubs,
    focus_rule_ids_from_handoff,
    merge_repairer_output,
)

_JSON_ERR_SNIPPET_CAP = 1500
_FAILED_RAW_CAP = 800


class RepairerChangeSummaryItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    rule_id: str | None = None
    finding_id: str | None = None
    change: str = ""


class RepairerPivOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rules: list[dict[str, Any]]
    change_summary: list[RepairerChangeSummaryItem] = Field(default_factory=list)


def vnext_repairer_appendix() -> str:
    return (
        "\n\n---\n\n## vNext expansion templates (optional in `rules`)\n\n"
        "Rules may use expansion `template_class` values; `load_rules_and_compile` **lowers** them to core IR. "
        "Keep expansion shape in output when fixing NL↔IR drift. **`SUM_THRESHOLD`:** at most **4** terms.\n\n"
        + read_vnext_template_examples()
        + "\n\n---\n\n"
        + read_temporal_surrogates_addendum()
    )


def repairer_ir_normative_appendix() -> str:
    return "\n\n---\n\n" + read_repairer_ir_normative()


_vnext_repairer_appendix = vnext_repairer_appendix


def _tmpl_structural() -> str:
    p = PROMPTS_DIR / "repairer_piv_structural.md"
    if not p.is_file():
        raise FileNotFoundError(f"missing {p}")
    return p.read_text(encoding="utf-8") + repairer_ir_normative_appendix() + _vnext_repairer_appendix()


def _tmpl_semantic() -> str:
    p = PROMPTS_DIR / "repairer_piv_semantic.md"
    if not p.is_file():
        raise FileNotFoundError(f"missing {p}")
    return (
        p.read_text(encoding="utf-8")
        + "\n\n---\n\n"
        + read_repairer_ir_normative()
        + "\n\n---\n\n"
        + read_semantic_repairer_ir_addendum()
        + _vnext_repairer_appendix()
    )


def _truncate(s: str, n: int) -> str:
    t = (s or "").strip()
    if len(t) <= n:
        return t
    return t[: n - 40] + "\n…(truncated)…\n"


def repairer_json_parse_retry_count() -> int:
    """Extra LLM turns after a failed JSON parse (default 1); clamped 0..3."""
    raw = os.getenv("PIVOT_REPAIRER_JSON_PARSE_RETRIES", "1").strip()
    try:
        n = int(raw)
    except ValueError:
        n = 1
    return max(0, min(n, 3))


def merge_error_prompt_suffix(merge_error: str) -> str:
    msg = (merge_error or "").strip()
    if len(msg) > 3000:
        msg = msg[: 3000 - 24] + "\n…(truncated)…\n"
    append_hint = ""
    if "unknown rule_id" in msg.lower() or "missing rule_id" in msg.lower():
        append_hint = (
            " You may **append** new rules with fresh `rule_id` values (see "
            "`suggested_next_rule_ids` in the payload) for companion templates such as "
            "`CONSTANT_RELATIONAL` — but you must still include every existing `rule_id` "
            "(stubs for non-focus)."
        )
    return (
        "\n\n---\n\n## Merge validation error (previous repair attempt)\n\n"
        f"{msg}\n\n"
        "Your `rules` array must include **every** `rule_id` from the input payload. "
        "Return stubs unchanged for non-focus rules."
        f"{append_hint} "
        'Reply with **only** one JSON object with keys "rules" and "change_summary".\n'
    )


def _compile_error_prompt_suffix(compile_validation_error: str) -> str:
    msg = (compile_validation_error or "").strip()
    if len(msg) > 3000:
        msg = msg[: 3000 - 24] + "\n…(truncated)…\n"
    k_of_n_hint = ""
    lower = msg.lower()
    if "k_of_n" in lower or "result_variable" in lower:
        k_of_n_hint = (
            "\n**Likely fix:** Remove any `\"kind\": \"k_of_n\"` nested inside "
            "`trigger_condition` / `required_condition`. "
            "On `K_OF_N` rules use optional `result_variable` for aggregate booleans — never top-level "
            "`variable` or `yields` (stripped silently). "
            "Add `CONSTANT_RELATIONAL` companion rules for yields SATISFIED enforcement.\n"
        )
    elif "unchanged" in lower or "dropped unsupported" in lower:
        k_of_n_hint = (
            "\n**Likely fix:** Emit real IR edits on focus rules (e.g. `result_variable` on K_OF_N), "
            "not narrative-only change_summary.\n"
        )
    return (
        "\n\n---\n\n## Compile validation error (previous repair attempt)\n\n"
        f"{msg}\n\n"
        "The patched `rules` failed Pydantic / IR validation. Emit a corrected `rules` array only "
        "(plus `change_summary`). Remove illegal extra keys on rule objects (see denylist). "
        f"{k_of_n_hint}"
        'Reply with **only** one JSON object with keys "rules" and "change_summary".\n'
    )


def _json_recovery_suffix(*, failed_raw: str, err: str) -> str:
    msg = (err or "").strip()
    if len(msg) > _JSON_ERR_SNIPPET_CAP:
        msg = msg[: _JSON_ERR_SNIPPET_CAP - 24] + "\n…(truncated)…\n"
    prev = (failed_raw or "").strip()
    if len(prev) > _FAILED_RAW_CAP:
        prev = prev[: _FAILED_RAW_CAP - 24] + "\n…(truncated)…\n"
    return (
        "\n\n---\n\n## JSON recovery\n\n"
        "Your previous output was not valid JSON or was not a single JSON object.\n\n"
        f"Parse error:\n{msg}\n\n"
        "Beginning of your previous output (trimmed):\n"
        f"{prev}\n\n"
        'Reply with **only** one JSON object with keys "rules" and "change_summary". '
        "No markdown code fences, no prose before or after. "
        "Keep the same repair intent as in the instructions and payload above.\n"
    )


def _coerce_repairer_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize common LLM shape mistakes before Pydantic validation."""
    cs = data.get("change_summary")
    if not isinstance(cs, list):
        return data
    coerced: list[Any] = []
    for item in cs:
        if isinstance(item, str):
            coerced.append({"finding_id": None, "rule_id": None, "change": item})
        else:
            coerced.append(item)
    data = dict(data)
    data["change_summary"] = coerced
    return data


def _llm_repairer_output(
    *,
    base_prompt: str,
    llm: Callable[..., str],
) -> tuple[RepairerPivOutput, bool]:
    """
    Parse LLM reply as Repairer JSON; on parse failure, retry up to
    ``repairer_json_parse_retry_count()`` extra calls with recovery suffix.

    Returns (output, json_parse_retry_used). Pydantic validation errors are not retried here.
    """
    json_parse_retry_used = False
    raw = llm(base_prompt)
    try:
        data = parse_json_object(raw)
    except ValueError as e:
        last_err: ValueError = e
        for _ in range(repairer_json_parse_retry_count()):
            raw = llm(base_prompt + _json_recovery_suffix(failed_raw=raw, err=str(last_err)))
            try:
                data = parse_json_object(raw)
                json_parse_retry_used = True
                break
            except ValueError as e2:
                last_err = e2
        else:
            raise last_err
    out = RepairerPivOutput.model_validate(_coerce_repairer_payload(data))
    return out, json_parse_retry_used


def complete_repairer_prompt(
    *,
    base_prompt: str,
    llm: Callable[..., str] = pivot_llm_complete,
) -> tuple[RepairerPivOutput, bool]:
    """
    Parse LLM reply as ``RepairerPivOutput`` from a fully built system+payload prompt.

    Same JSON/retry behavior as structural/semantic repairer entrypoints.
    """
    return _llm_repairer_output(base_prompt=base_prompt, llm=llm)


def run_repairer_piv_structural(
    *,
    policy_id: str,
    rules: list[dict[str, Any]],
    error_text: str,
    llm: Callable[..., str] = pivot_llm_complete,
) -> tuple[RepairerPivOutput, bool]:
    sys = _tmpl_structural()
    payload = {
        "mode": "structural",
        "policy_id": policy_id,
        "error": error_text[:8000],
        "rules": rules,
    }
    user = json.dumps(payload, ensure_ascii=False, indent=2)
    prompt = sys + "\n\n---\n\n## Current payload JSON\n\n" + user
    return _llm_repairer_output(base_prompt=prompt, llm=llm)


def run_repairer_piv_semantic(
    *,
    policy_id: str,
    rules: list[dict[str, Any]],
    handoff: dict[str, Any],
    effective_nl_excerpt: str,
    synthetic_excerpt: str,
    compile_validation_error: str | None = None,
    merge_validation_error: str | None = None,
    llm: Callable[..., str] = pivot_llm_complete,
) -> tuple[RepairerPivOutput, bool]:
    sys = _tmpl_semantic()
    focus_ids = focus_rule_ids_from_handoff(handoff)
    rules_payload = build_rules_payload_stubs(rules, focus_ids)
    payload: dict[str, Any] = {
        "mode": "semantic",
        "policy_id": policy_id,
        "handoff": handoff,
        "focus_rule_ids": focus_ids,
        "effective_nl_excerpt": _truncate(effective_nl_excerpt, 12000),
        "synthetic_excerpt": _truncate(synthetic_excerpt, 12000),
        "rules": rules_payload,
    }
    cve = (compile_validation_error or "").strip()
    if cve:
        payload["compile_validation_error"] = _truncate(cve, 4000)
    mve = (merge_validation_error or "").strip()
    if mve:
        payload["merge_validation_error"] = _truncate(mve, 4000)
    user = json.dumps(payload, ensure_ascii=False, indent=2)
    prompt = sys + "\n\n---\n\n## Current payload JSON\n\n" + user
    if mve:
        prompt += merge_error_prompt_suffix(mve)
    elif cve:
        prompt += _compile_error_prompt_suffix(cve)
    out, json_retry = _llm_repairer_output(base_prompt=prompt, llm=llm)
    merged = merge_repairer_output(
        full_rules=rules,
        repairer_rules=out.rules,
        focus_rule_ids=focus_ids,
    )
    out.rules = merged
    return out, json_retry


def append_repairer_trace(work_dir: Path, record: dict[str, Any], *, kind: str) -> None:
    path = work_dir / f"repairer_piv_{kind}_trace.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    rec = {"kind": kind, **record}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


__all__ = [
    "MergeRepairerOutputError",
    "RepairerChangeSummaryItem",
    "RepairerPivOutput",
    "append_repairer_trace",
    "complete_repairer_prompt",
    "merge_error_prompt_suffix",
    "repairer_ir_normative_appendix",
    "repairer_json_parse_retry_count",
    "run_repairer_piv_semantic",
    "run_repairer_piv_structural",
    "vnext_repairer_appendix",
]
