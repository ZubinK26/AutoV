from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

from pivot_pipeline.llm import pivot_llm_complete
from pivot_pipeline.paths import PROMPTS_DIR
from pivot_pipeline.post_model_workflow import TesterReport
from pivot_pipeline.repairer_piv_agent import (
    RepairerPivOutput,
    _compile_error_prompt_suffix,
    complete_repairer_prompt,
)


def _truncate(s: str, n: int) -> str:
    t = (s or "").strip()
    if len(t) <= n:
        return t
    return t[: n - 40] + "\n…(truncated)…\n"


def _tmpl() -> str:
    p = PROMPTS_DIR / "test_repairer.md"
    if not p.is_file():
        raise FileNotFoundError(f"missing {p}")
    return p.read_text(encoding="utf-8")


def test_repair_max_rounds() -> int:
    raw = os.getenv("PIVOT_TESTER_REPAIR_MAX_ROUNDS", "3").strip()
    try:
        return max(1, min(int(raw), 10))
    except ValueError:
        return 3


def test_repair_compile_attempts_max() -> int:
    raw = os.getenv("PIVOT_TESTER_REPAIR_COMPILE_ATTEMPTS", "3").strip()
    try:
        return max(1, min(int(raw), 10))
    except ValueError:
        return 3


def tester_repair_handoff_dict(
    report: TesterReport,
    *,
    approved_ids: list[str],
    ignored_ids: list[str],
    full_report_path: Path,
    source_note: str = "user approved repair subset",
) -> dict[str, Any]:
    approved_set = set(approved_ids)
    return {
        "handoff_schema_version": "1",
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


def run_test_repairer(
    *,
    policy_id: str,
    rules: list[dict[str, Any]],
    handoff: dict[str, Any],
    processed_nl_excerpt: str,
    linearized_excerpt: str,
    compile_validation_error: str | None = None,
    llm: Callable[..., str] = pivot_llm_complete,
) -> tuple[RepairerPivOutput, bool]:
    sys = _tmpl()
    payload: dict[str, Any] = {
        "mode": "tester_nl_alignment",
        "policy_id": policy_id,
        "handoff": handoff,
        "processed_nl_excerpt": _truncate(processed_nl_excerpt, 14_000),
        "linearized_excerpt": _truncate(linearized_excerpt, 14_000),
        "rules": rules,
    }
    cve = (compile_validation_error or "").strip()
    if cve:
        payload["compile_validation_error"] = _truncate(cve, 4000)
    user = json.dumps(payload, ensure_ascii=False, indent=2)
    prompt = sys + "\n\n---\n\n## Current payload JSON\n\n" + user
    if cve:
        prompt += _compile_error_prompt_suffix(cve)
    return complete_repairer_prompt(base_prompt=prompt, llm=llm)


def append_test_repairer_trace(work_dir: Path, record: dict[str, Any]) -> None:
    path = work_dir / "test_repairer_trace.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    rec = {"kind": "test_repair", **record}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


__all__ = [
    "append_test_repairer_trace",
    "run_test_repairer",
    "test_repair_compile_attempts_max",
    "test_repair_max_rounds",
    "tester_repair_handoff_dict",
]
