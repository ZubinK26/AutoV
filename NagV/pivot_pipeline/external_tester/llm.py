"""Per-stage Gemini models for external tester."""

from __future__ import annotations

import os
from typing import Literal

from pivot_pipeline.api_retry import api_auto_retries_max, call_with_transient_api_retries
from pivot_pipeline.llm import get_pivot_gemini_model, get_pivot_gemini_thinking_level_str
from registry_stage.llm.gemini_call import gemini_complete

Stage = Literal["fill", "review", "syntax"]

_DEFAULT_PRO = "gemini-3.1-pro-preview"


def _model_for(stage: Stage) -> str:
    if stage == "fill":
        return os.getenv("PIVOT_EXTERNAL_FILL_GEMINI_MODEL", "").strip() or _DEFAULT_PRO
    if stage == "review":
        return os.getenv("PIVOT_EXTERNAL_REVIEW_GEMINI_MODEL", "").strip() or _DEFAULT_PRO
    return os.getenv("PIVOT_EXTERNAL_SYNTAX_REPAIR_GEMINI_MODEL", "").strip() or get_pivot_gemini_model()


def external_llm_complete(prompt: str, *, stage: Stage) -> str:
    tl = os.getenv("PIVOT_EXTERNAL_TESTER_THINKING_LEVEL", "").strip() or "low"
    if not tl:
        tl = get_pivot_gemini_thinking_level_str()
    cap_raw = os.getenv("PIVOT_EXTERNAL_TESTER_MAX_OUTPUT_TOKENS", "").strip()
    cap = int(cap_raw) if cap_raw.isdigit() else None
    kw: dict = {
        "system_instruction": (
            "You are a precise assistant for policy test authoring. "
            "Follow the user prompt exactly on output format."
        ),
        "user_text": prompt,
        "model": _model_for(stage),
        "thinking_level": tl,
    }
    if cap is not None:
        kw["max_output_tokens"] = cap

    def _call() -> str:
        return gemini_complete(**kw)

    return call_with_transient_api_retries(
        _call,
        label=f"external_tester_{stage}",
        max_retries=api_auto_retries_max(env_var="PIVOT_EXTERNAL_TESTER_API_AUTO_RETRIES"),
    )


__all__ = ["external_llm_complete"]
