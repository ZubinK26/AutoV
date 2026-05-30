from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

from pivot_pipeline.cross_critic_agent import CrossCriticReport
from pivot_pipeline.llm import pivot_llm_complete
from pivot_pipeline.paths import PROMPTS_DIR, read_cross_repairer_ir_addendum, read_repairer_ir_normative
from pivot_pipeline.repairer_piv_agent import (
    RepairerPivOutput,
    _compile_error_prompt_suffix,
    complete_repairer_prompt,
    merge_error_prompt_suffix,
    vnext_repairer_appendix,
)
from pivot_pipeline.test_repair_rules_payload import (
    MergeRepairerOutputError,
    build_rules_payload_stubs,
    focus_rule_ids_from_handoff,
    merge_repairer_output,
    repair_allow_append_rules,
    repairer_append_payload_fields,
)


def _truncate(s: str, n: int) -> str:
    t = (s or "").strip()
    if len(t) <= n:
        return t
    return t[: n - 40] + "\n…(truncated)…\n"


def cross_repairer_system_prompt() -> str:
    p = PROMPTS_DIR / "cross_repairer.md"
    if not p.is_file():
        raise FileNotFoundError(f"missing {p}")
    return (
        p.read_text(encoding="utf-8")
        + "\n\n---\n\n"
        + read_repairer_ir_normative()
        + "\n\n---\n\n"
        + read_cross_repairer_ir_addendum()
        + vnext_repairer_appendix()
    )


def cross_repair_handoff_dict(
    report: CrossCriticReport,
    *,
    approved_ids: list[str],
    ignored_ids: list[str],
    full_report_path: Path,
    source_note: str = "user approved repair subset",
) -> dict[str, Any]:
    approved_set = set(approved_ids)
    index_map = {str(i): f.id for i, f in enumerate(sorted(report.findings, key=lambda x: x.id), start=1)}
    return {
        "handoff_schema_version": "1.0",
        "source": "cross_critic",
        "source_note": source_note,
        "verdict": report.verdict,
        "compared_against": report.compared_against,
        "approved_finding_ids": sorted(approved_ids),
        "ignored_finding_ids": sorted(ignored_ids),
        "triage_index_map": index_map,
        "findings": [f.model_dump(mode="json") for f in report.findings if f.id in approved_set],
        "full_report_path": str(full_report_path.resolve()),
        "audit_trail_bullets": list(report.audit_trail_bullets),
        "notes": report.notes,
    }


def cross_repair_max_rounds() -> int:
    """Max user-initiated CrossRepairer sessions per cross slice; 0 = unlimited (default)."""
    raw = os.getenv("PIVOT_CROSS_REPAIR_MAX_ROUNDS", "0").strip()
    try:
        return max(0, min(int(raw), 100))
    except ValueError:
        return 0


def cross_repair_compile_attempts_max() -> int:
    raw = os.getenv("PIVOT_CROSS_REPAIR_COMPILE_ATTEMPTS", "5").strip()
    try:
        return max(1, min(int(raw), 10))
    except ValueError:
        return 5


def run_cross_repairer(
    *,
    policy_id: str,
    rules: list[dict[str, Any]],
    handoff: dict[str, Any],
    processed_nl_excerpt: str,
    linearized_excerpt: str,
    compile_validation_error: str | None = None,
    merge_validation_error: str | None = None,
    llm: Callable[..., str] = pivot_llm_complete,
) -> tuple[RepairerPivOutput, bool]:
    sys = cross_repairer_system_prompt()
    focus_ids = focus_rule_ids_from_handoff(handoff)
    rules_payload = build_rules_payload_stubs(rules, focus_ids)

    allow_append = repair_allow_append_rules()
    payload: dict[str, Any] = {
        "mode": "cross_coherence",
        "policy_id": policy_id,
        "handoff": handoff,
        "focus_rule_ids": focus_ids,
        "allow_append_rules": allow_append,
        "processed_nl_excerpt": _truncate(processed_nl_excerpt, 14_000),
        "linearized_excerpt": _truncate(linearized_excerpt, 14_000),
        "rules": rules_payload,
    }
    if allow_append:
        payload.update(repairer_append_payload_fields(rules))
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
    out, json_retry = complete_repairer_prompt(base_prompt=prompt, llm=llm)
    merged = merge_repairer_output(
        full_rules=rules,
        repairer_rules=out.rules,
        focus_rule_ids=focus_ids,
        allow_append_rules=allow_append,
    )
    out.rules = merged
    return out, json_retry


def append_cross_repairer_trace(work_dir: Path, record: dict[str, Any]) -> None:
    path = work_dir / "cross_repairer_trace.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    rec = {"kind": "cross", **record}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


__all__ = [
    "MergeRepairerOutputError",
    "append_cross_repairer_trace",
    "cross_repair_compile_attempts_max",
    "cross_repair_handoff_dict",
    "cross_repair_max_rounds",
    "cross_repairer_system_prompt",
    "run_cross_repairer",
]
