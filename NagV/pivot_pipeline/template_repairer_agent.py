"""Template Repairer — patch rules from approved template diagnostic findings."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

from pivot_pipeline.llm import pivot_llm_complete
from pivot_pipeline.paths import PROMPTS_DIR, read_repairer_ir_normative
from pivot_pipeline.repairer_piv_agent import (
    RepairerPivOutput,
    _compile_error_prompt_suffix,
    complete_repairer_prompt,
    merge_error_prompt_suffix,
    vnext_repairer_appendix,
)
from pivot_pipeline.template_diagnostician_agent import TemplateDiagnosticReport
from pivot_pipeline.test_repair_rules_payload import (
    MergeRepairerOutputError,
    build_rules_payload_stubs,
    focus_rule_ids_from_handoff,
    merge_repairer_output,
    repair_allow_append_rules,
    repairer_append_payload_fields,
    repairer_rules_with_missing_stubs,
)


def _trim(s: str, n: int) -> str:
    t = (s or "").strip()
    if len(t) <= n:
        return t
    return t[: n - 40] + "\n…(truncated)…\n"


def read_template_repairer_ir_addendum() -> str:
    p = PROMPTS_DIR / "template_repairer_ir_addendum.md"
    if not p.is_file():
        raise FileNotFoundError(f"missing {p}")
    return p.read_text(encoding="utf-8")


def template_repairer_system_prompt() -> str:
    p = PROMPTS_DIR / "template_repairer.md"
    if not p.is_file():
        raise FileNotFoundError(f"missing {p}")
    return (
        p.read_text(encoding="utf-8")
        + "\n\n---\n\n"
        + read_repairer_ir_normative()
        + "\n\n---\n\n"
        + read_template_repairer_ir_addendum()
        + vnext_repairer_appendix()
    )


def template_repair_max_rounds() -> int:
    raw = os.getenv("PIVOT_TEMPLATE_REPAIR_MAX_ROUNDS", "3").strip()
    try:
        return max(1, min(int(raw), 10))
    except ValueError:
        return 3


def template_repair_compile_attempts_max() -> int:
    raw = os.getenv("PIVOT_TEMPLATE_REPAIR_COMPILE_ATTEMPTS", "5").strip()
    try:
        return max(1, min(int(raw), 10))
    except ValueError:
        return 5


def focus_rule_ids_from_template_handoff(handoff: dict[str, Any]) -> list[str]:
    ids: set[str] = set()
    for f in handoff.get("findings") or []:
        if isinstance(f, dict):
            for rid in f.get("rule_ids") or []:
                if isinstance(rid, str) and rid.strip():
                    ids.add(rid.strip())
    extra = handoff.get("focus_rule_ids")
    if isinstance(extra, list):
        for rid in extra:
            if isinstance(rid, str) and rid.strip():
                ids.add(rid.strip())
    return sorted(ids) if ids else focus_rule_ids_from_handoff(handoff)


def run_template_repairer(
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
    sys = template_repairer_system_prompt()
    focus_ids = focus_rule_ids_from_template_handoff(handoff)
    rules_payload = build_rules_payload_stubs(rules, focus_ids)
    allow_append = repair_allow_append_rules()
    bundles = handoff.get("failure_bundles") or []
    payload: dict[str, Any] = {
        "mode": "template_suite_alignment",
        "policy_id": policy_id,
        "handoff": handoff,
        "focus_rule_ids": focus_ids,
        "allow_append_rules": allow_append,
        "processed_nl_excerpt": _trim(processed_nl_excerpt, 14_000),
        "linearized_excerpt": _trim(linearized_excerpt, 14_000),
        "failure_bundles": bundles[:12] if isinstance(bundles, list) else [],
        "rules": rules_payload,
    }
    if allow_append:
        payload.update(repairer_append_payload_fields(rules))
    cve = (compile_validation_error or "").strip()
    if cve:
        payload["compile_validation_error"] = _trim(cve, 4000)
    mve = (merge_validation_error or "").strip()
    if mve:
        payload["merge_validation_error"] = _trim(mve, 4000)
    user = json.dumps(payload, ensure_ascii=False, indent=2)
    prompt = sys + "\n\n---\n\n## Current payload JSON\n\n" + user
    if mve:
        prompt += merge_error_prompt_suffix(mve)
    elif cve:
        prompt += _compile_error_prompt_suffix(cve)
    out, json_retry = complete_repairer_prompt(base_prompt=prompt, llm=llm)
    repairer_rules, _filled_missing = repairer_rules_with_missing_stubs(rules, out.rules)
    merged = merge_repairer_output(
        full_rules=rules,
        repairer_rules=repairer_rules,
        focus_rule_ids=focus_ids,
        allow_append_rules=allow_append,
    )
    out.rules = merged
    return out, json_retry


def append_template_repairer_trace(work_dir: Path, record: dict[str, Any]) -> None:
    path = work_dir / "template_repairer_trace.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"kind": "template_repair", **record}, ensure_ascii=False) + "\n")


__all__ = [
    "MergeRepairerOutputError",
    "append_template_repairer_trace",
    "focus_rule_ids_from_template_handoff",
    "run_template_repairer",
    "template_repair_compile_attempts_max",
    "template_repair_max_rounds",
]
