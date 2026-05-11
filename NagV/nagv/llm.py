"""LLM calls for NagV agents (Gemini or Anthropic Claude)."""

from __future__ import annotations

import os

# Gemini 3 Flash (text) — override with NAGV_GEMINI_MODEL / NAGV_CRITIC_GEMINI_MODEL.
NAGV_DEFAULT_GEMINI_MODEL = "gemini-3-flash-preview"
NAGV_CRITIC_DEFAULT_GEMINI_MODEL = "gemini-3-flash-preview"


def nagv_gemini_model() -> str:
    return os.environ.get("NAGV_GEMINI_MODEL", NAGV_DEFAULT_GEMINI_MODEL).strip()


def nagv_critic_gemini_model() -> str:
    return os.environ.get("NAGV_CRITIC_GEMINI_MODEL", NAGV_CRITIC_DEFAULT_GEMINI_MODEL).strip()


def nagv_llm_backend() -> str:
    """``gemini`` (default) | ``anthropic`` | ``claude`` from ``NAGV_LLM``."""
    return os.environ.get("NAGV_LLM", "gemini").strip().lower()


# Gemini extended thinking passed per-call to ``call_llm`` (Claude ignores).
# Formalizer and repair use ``medium``; critic uses ``high`` (see ``critic_agent``).
NAGV_AGENT_THINKING_LEVEL = "medium"
NAGV_CRITIC_THINKING_LEVEL = "high"


def nagv_max_output_tokens() -> int:
    raw = os.environ.get("NAGV_MAX_OUTPUT_TOKENS", "").strip()
    if raw:
        return int(raw)
    if nagv_llm_backend() in ("anthropic", "claude"):
        return int(os.environ.get("ANTHROPIC_MAX_TOKENS", "16384"))
    return int(os.environ.get("GEMINI_MAX_OUTPUT_TOKENS", "32768"))


def call_llm(
    *,
    system_instruction: str,
    user_text: str,
    thinking_level: str | None = None,
    model: str | None = None,
) -> str:
    """
    One completion. Uses Claude when ``NAGV_LLM`` is ``anthropic`` or ``claude``; else Gemini.

    ``thinking_level`` applies only to Gemini (see ``registry_stage.llm.gemini_call``).
    ``model`` applies only to Gemini (per-call override; unset uses ``GEMINI_MODEL``).
    """
    b = nagv_llm_backend()
    if b in ("anthropic", "claude"):
        from nagv.anthropic_call import anthropic_complete

        return anthropic_complete(
            system_instruction=system_instruction,
            user_text=user_text,
            max_output_tokens=nagv_max_output_tokens(),
        )
    return call_gemini(
        system_instruction=system_instruction,
        user_text=user_text,
        thinking_level=thinking_level,
        model=model,
    )


def call_gemini(
    *,
    system_instruction: str,
    user_text: str,
    thinking_level: str | None = None,
    model: str | None = None,
) -> str:
    from registry_stage.llm.gemini_call import gemini_complete

    return gemini_complete(
        system_instruction=system_instruction,
        user_text=user_text,
        max_output_tokens=nagv_max_output_tokens(),
        thinking_level=thinking_level,
        model=model,
    )
