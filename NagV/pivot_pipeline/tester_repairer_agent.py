from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable, Literal

from pivot_pipeline.ir import load_rules_and_compile, sanitize_rules_jsonable
from pivot_pipeline.llm import pivot_llm_complete
from pivot_pipeline.paths import PROMPTS_DIR, read_repairer_ir_normative, read_test_repairer_ir_addendum
from pivot_pipeline.post_model_workflow import TesterReport
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
)

RepairErrorStage = Literal[
    "repairer_json",
    "repairer_api",
    "rules_merge",
    "rules_compile",
    "registry_json",
    "registry_api",
]


def _truncate(s: str, n: int) -> str:
    t = (s or "").strip()
    if len(t) <= n:
        return t
    return t[: n - 40] + "\n…(truncated)…\n"


def test_repairer_system_prompt() -> str:
    p = PROMPTS_DIR / "test_repairer.md"
    if not p.is_file():
        raise FileNotFoundError(f"missing {p}")
    return (
        p.read_text(encoding="utf-8")
        + "\n\n---\n\n"
        + read_repairer_ir_normative()
        + "\n\n---\n\n"
        + read_test_repairer_ir_addendum()
        + vnext_repairer_appendix()
    )


def test_repair_max_rounds() -> int:
    raw = os.getenv("PIVOT_TESTER_REPAIR_MAX_ROUNDS", "3").strip()
    try:
        return max(1, min(int(raw), 10))
    except ValueError:
        return 3


def test_repair_compile_attempts_max() -> int:
    raw = os.getenv("PIVOT_TESTER_REPAIR_COMPILE_ATTEMPTS", "5").strip()
    try:
        return max(1, min(int(raw), 10))
    except ValueError:
        return 5


def tester_repair_handoff_dict(
    report: TesterReport,
    *,
    approved_ids: list[str],
    ignored_ids: list[str],
    full_report_path: Path,
    source_note: str = "user approved repair subset",
    last_compile_validation_error: str | None = None,
    last_repair_error_stage: str | None = None,
    last_registry_error: str | None = None,
    repair_session_count: int | None = None,
) -> dict[str, Any]:
    approved_set = set(approved_ids)
    out: dict[str, Any] = {
        "handoff_schema_version": "1.2",
        "source": "pivot_tester",
        "source_note": source_note,
        "verdict": report.verdict,
        "compared_against": report.compared_against,
        "approved_finding_ids": sorted(approved_ids),
        "ignored_finding_ids": sorted(ignored_ids),
        "findings": [f.model_dump(mode="json") for f in report.findings if f.id in approved_set],
        "full_report_path": str(full_report_path.resolve()),
        "notes": report.notes,
    }
    err = (last_compile_validation_error or "").strip()
    if err:
        out["last_compile_validation_error"] = err
    stage = (last_repair_error_stage or "").strip()
    if stage:
        out["last_repair_error_stage"] = stage
    reg_err = (last_registry_error or "").strip()
    if reg_err:
        out["last_registry_error"] = reg_err
    if repair_session_count is not None:
        out["repair_session_count"] = repair_session_count
    return out


def precompile_repaired_rules(
    policy_id: str,
    rules: list[dict[str, Any]],
    *,
    skip_vnext_lowering: bool = False,
    policy_semantics_version: str | None = None,
) -> list[dict[str, Any]]:
    """Sanitize and validate rules compile before registry pass."""
    sanitized = sanitize_rules_jsonable(rules)
    load_rules_and_compile(
        policy_id,
        sanitized,
        skip_vnext_lowering=skip_vnext_lowering,
        policy_semantics_version=policy_semantics_version,
    )
    return sanitized


def run_test_repairer(
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
    sys = test_repairer_system_prompt()
    focus_ids = focus_rule_ids_from_handoff(handoff)
    rules_payload = build_rules_payload_stubs(rules, focus_ids)

    payload: dict[str, Any] = {
        "mode": "tester_nl_alignment",
        "policy_id": policy_id,
        "handoff": handoff,
        "focus_rule_ids": focus_ids,
        "processed_nl_excerpt": _truncate(processed_nl_excerpt, 14_000),
        "linearized_excerpt": _truncate(linearized_excerpt, 14_000),
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
    out, json_retry = complete_repairer_prompt(base_prompt=prompt, llm=llm)
    merged = merge_repairer_output(
        full_rules=rules,
        repairer_rules=out.rules,
        focus_rule_ids=focus_ids,
    )
    out.rules = merged
    return out, json_retry


def append_test_repairer_trace(work_dir: Path, record: dict[str, Any]) -> None:
    path = work_dir / "test_repairer_trace.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    rec = {"kind": "test_repair", **record}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


__all__ = [
    "MergeRepairerOutputError",
    "RepairErrorStage",
    "append_test_repairer_trace",
    "focus_rule_ids_from_handoff",
    "merge_repairer_output",
    "precompile_repaired_rules",
    "run_test_repairer",
    "test_repair_compile_attempts_max",
    "test_repair_max_rounds",
    "test_repairer_system_prompt",
    "tester_repair_handoff_dict",
]
