from __future__ import annotations

import os

from registry_stage.llm.gemini_call import gemini_complete


def get_pivot_gemini_model() -> str:
    """Default ``gemini-3-flash-preview``; override with ``PIVOT_GEMINI_MODEL`` only."""
    return os.getenv("PIVOT_GEMINI_MODEL", "").strip() or "gemini-3-flash-preview"


def get_pivot_gemini_thinking_level_str() -> str:
    """Default ``medium``; override with ``PIVOT_GEMINI_THINKING_LEVEL`` only."""
    return os.getenv("PIVOT_GEMINI_THINKING_LEVEL", "").strip() or "medium"


def _pivot_max_output_tokens() -> int | None:
    for key in ("PIVOT_GEMINI_MAX_OUTPUT_TOKENS", "NAGV_MAX_OUTPUT_TOKENS"):
        raw = os.getenv(key, "").strip()
        if raw:
            try:
                return int(raw)
            except ValueError:
                break
    return None


def pivot_llm_complete(
    prompt: str,
    *,
    thinking_level: str | None = None,
    max_output_tokens: int | None = None,
) -> str:
    """One Gemini turn for pivot prompts (parity with ``registry_stage.llm.gemini_call``)."""
    model = get_pivot_gemini_model()
    tl = thinking_level if thinking_level is not None else get_pivot_gemini_thinking_level_str()
    cap = max_output_tokens if max_output_tokens is not None else _pivot_max_output_tokens()
    kw: dict = {
        "system_instruction": (
            "You are a precise assistant for policy formalization. "
            "Follow the user prompt exactly on output format."
        ),
        "user_text": prompt,
        "model": model,
        "thinking_level": tl,
    }
    if cap is not None:
        kw["max_output_tokens"] = cap
    return gemini_complete(**kw)


__all__ = [
    "get_pivot_gemini_model",
    "get_pivot_gemini_thinking_level_str",
    "pivot_llm_complete",
]
