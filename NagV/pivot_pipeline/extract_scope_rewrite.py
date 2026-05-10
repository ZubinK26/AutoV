"""LLM-assisted rewrite of an NL rule line into pivot v1–encodable form."""

from __future__ import annotations

import os
from typing import Any, Callable

from pivot_pipeline.json_util import parse_json_object
from pivot_pipeline.llm import pivot_llm_complete
from pivot_pipeline.paths import PROMPTS_DIR, read_v1_policy_encodability_contract


def scope_rewrite_hint_max_chars() -> int:
    raw = os.getenv("PIVOT_SCOPE_REWRITE_HINT_MAX_CHARS", "500").strip()
    try:
        n = int(raw)
    except ValueError:
        n = 500
    return max(1, min(n, 2000))


def normalize_operator_hint_input(s: str) -> str:
    t = (s or "").strip()
    cap = scope_rewrite_hint_max_chars()
    if len(t) > cap:
        t = t[:cap]
    return t


def _operator_hint_for_prompt(operator_hint: str | None) -> str:
    t = normalize_operator_hint_input(operator_hint or "")
    return t if t else "(none)"


def _prompt_template() -> str:
    path = PROMPTS_DIR / "scope_rewrite.md"
    if not path.is_file():
        raise FileNotFoundError(f"missing scope_rewrite prompt: {path}")
    return (
        path.read_text(encoding="utf-8")
        + "\n\n---\n\n## Normative v1 encodability (shared)\n\n"
        + read_v1_policy_encodability_contract()
    )


def run_scope_rewrite(
    original_line: str,
    *,
    extractor_abort_text: str = "",
    operator_hint: str | None = None,
    llm: Callable[..., str] = pivot_llm_complete,
) -> dict[str, Any]:
    """Return dict with ``rewritten_line``, ``semantic_deltas``, ``fidelity_notes``."""
    tmpl = _prompt_template()
    snippet = (extractor_abort_text or "").strip()[:4000]
    hint_block = _operator_hint_for_prompt(operator_hint)
    prompt = (
        tmpl.replace("<<<ORIGINAL_LINE>>>", original_line.strip())
        .replace("<<<ABORT_SNIPPET>>>", snippet if snippet else "(none)")
        .replace("<<<OPERATOR_HINT>>>", hint_block)
    )
    raw = llm(prompt)
    data = parse_json_object(raw)
    rw = data.get("rewritten_line")
    if not isinstance(rw, str) or not rw.strip():
        raise ValueError("scope_rewrite: missing rewritten_line")
    deltas = data.get("semantic_deltas")
    if deltas is None:
        deltas = []
    if isinstance(deltas, str):
        deltas = [deltas]
    if not isinstance(deltas, list):
        raise ValueError("scope_rewrite: semantic_deltas must be a list or string")
    notes = data.get("fidelity_notes")
    if notes is not None and not isinstance(notes, str):
        raise ValueError("scope_rewrite: fidelity_notes must be a string")
    return {
        "rewritten_line": rw.strip(),
        "semantic_deltas": [str(d).strip() for d in deltas if str(d).strip()],
        "fidelity_notes": (notes or "").strip(),
    }


__all__ = [
    "normalize_operator_hint_input",
    "run_scope_rewrite",
    "scope_rewrite_hint_max_chars",
]
