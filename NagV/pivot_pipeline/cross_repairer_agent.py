from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

from pivot_pipeline.llm import pivot_llm_complete
from pivot_pipeline.paths import PROMPTS_DIR
from pivot_pipeline.repairer_piv_agent import RepairerPivOutput, complete_repairer_prompt


def _tmpl() -> str:
    p = PROMPTS_DIR / "cross_repairer.md"
    if not p.is_file():
        raise FileNotFoundError(f"missing {p}")
    return p.read_text(encoding="utf-8")


def _truncate(s: str, n: int) -> str:
    t = (s or "").strip()
    if len(t) <= n:
        return t
    return t[: n - 40] + "\n…(truncated)…\n"


def cross_repair_max_rounds() -> int:
    raw = os.getenv("PIVOT_CROSS_REPAIR_MAX_ROUNDS", "3").strip()
    try:
        return max(0, min(int(raw), 10))
    except ValueError:
        return 3


def run_cross_repairer(
    *,
    policy_id: str,
    rules: list[dict[str, Any]],
    handoff: dict[str, Any],
    processed_nl_excerpt: str,
    linearized_excerpt: str,
    llm: Callable[..., str] = pivot_llm_complete,
) -> tuple[RepairerPivOutput, bool]:
    sys = _tmpl()
    payload = {
        "mode": "cross_coherence",
        "policy_id": policy_id,
        "handoff": handoff,
        "processed_nl_excerpt": _truncate(processed_nl_excerpt, 14_000),
        "linearized_excerpt": _truncate(linearized_excerpt, 14_000),
        "rules": rules,
    }
    user = json.dumps(payload, ensure_ascii=False, indent=2)
    prompt = sys + "\n\n---\n\n## Current payload JSON\n\n" + user
    return complete_repairer_prompt(base_prompt=prompt, llm=llm)


def append_cross_repairer_trace(work_dir: Path, record: dict[str, Any]) -> None:
    path = work_dir / "cross_repairer_trace.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    rec = {"kind": "cross", **record}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


__all__ = [
    "append_cross_repairer_trace",
    "cross_repair_max_rounds",
    "run_cross_repairer",
]
