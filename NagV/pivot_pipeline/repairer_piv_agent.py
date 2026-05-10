from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field

from pivot_pipeline.json_util import parse_json_object
from pivot_pipeline.llm import pivot_llm_complete
from pivot_pipeline.paths import PROMPTS_DIR

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


def _tmpl_structural() -> str:
    p = PROMPTS_DIR / "repairer_piv_structural.md"
    if not p.is_file():
        raise FileNotFoundError(f"missing {p}")
    return p.read_text(encoding="utf-8")


def _tmpl_semantic() -> str:
    p = PROMPTS_DIR / "repairer_piv_semantic.md"
    if not p.is_file():
        raise FileNotFoundError(f"missing {p}")
    return p.read_text(encoding="utf-8")


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
    out = RepairerPivOutput.model_validate(data)
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
    llm: Callable[..., str] = pivot_llm_complete,
) -> tuple[RepairerPivOutput, bool]:
    sys = _tmpl_semantic()
    payload = {
        "mode": "semantic",
        "policy_id": policy_id,
        "handoff": handoff,
        "effective_nl_excerpt": _truncate(effective_nl_excerpt, 12000),
        "synthetic_excerpt": _truncate(synthetic_excerpt, 12000),
        "rules": rules,
    }
    user = json.dumps(payload, ensure_ascii=False, indent=2)
    prompt = sys + "\n\n---\n\n## Current payload JSON\n\n" + user
    return _llm_repairer_output(base_prompt=prompt, llm=llm)


def append_repairer_trace(work_dir: Path, record: dict[str, Any], *, kind: str) -> None:
    path = work_dir / f"repairer_piv_{kind}_trace.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    rec = {"kind": kind, **record}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


__all__ = [
    "RepairerChangeSummaryItem",
    "RepairerPivOutput",
    "append_repairer_trace",
    "complete_repairer_prompt",
    "repairer_json_parse_retry_count",
    "run_repairer_piv_semantic",
    "run_repairer_piv_structural",
]
