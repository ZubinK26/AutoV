"""Gemini backend — same API key as WFM / ``registry_stage.llm.gemini_call``."""

from __future__ import annotations

import os
from contextlib import contextmanager

from cpmpy_wfm_policy.llm import FormalizerLLM


@contextmanager
def _optional_env(key: str, val: str | None):
    """Temporarily set *key* for one formalizer call (provider still routed via registry)."""
    if not val:
        yield
        return
    prev = os.environ.get(key)
    os.environ[key] = val
    try:
        yield
    finally:
        if prev is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = prev


def gemini_formalizer_llm(
    *,
    max_output_tokens: int | None = None,
) -> FormalizerLLM:
    if max_output_tokens is None:
        raw = os.environ.get("CPMPY_FORMALIZER_MAX_OUTPUT_TOKENS", "").strip()
        max_output_tokens = int(raw) if raw else 8192

    def _call(*, system_instruction: str, user_text: str) -> str:
        from registry_stage.llm.gemini_call import gemini_complete

        override = os.environ.get("CPMPY_GEMINI_MODEL", "").strip() or None
        with _optional_env("GEMINI_MODEL", override):
            return gemini_complete(
                system_instruction=system_instruction,
                user_text=user_text,
                max_output_tokens=max_output_tokens,
            )

    return _call
