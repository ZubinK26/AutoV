"""
Thin Gemini caller — env contract aligned with ``test_sets/wfm_api_contract_gemini.md``.

Do not import ``test_sets/scripts/*.py``; parity is maintained by matching the same variables
and ``google.genai`` usage as ``run_wfm_folio_gemini.call_gemini``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any


def repo_root_containing_registry_stage() -> Path:
    """``registry_stage/llm/`` → parents[2] = repo root (has ``bundles/``, ``.env``)."""
    return Path(__file__).resolve().parents[2]


def load_repo_dotenv() -> None:
    try:
        from dotenv import dotenv_values, load_dotenv
    except ImportError:
        return
    env_file = repo_root_containing_registry_stage() / ".env"
    if not env_file.is_file():
        return
    load_dotenv(env_file, override=False)
    # ``override=False`` skips vars already present in os.environ. On Windows, GEMINI_API_KEY is
    # sometimes set to an empty string in the shell/user profile, which blocks loading from .env.
    if os.environ.get("GEMINI_API_KEY", "").strip():
        return
    vals = dotenv_values(env_file)
    raw = (vals.get("GEMINI_API_KEY") or "").strip()
    if raw:
        os.environ["GEMINI_API_KEY"] = raw


def _thinking_level_from_str(raw: str) -> Any:
    """Map a level string to ``ThinkingLevel`` or ``None`` (API default). Warn on unknown."""
    from google.genai import types as genai_types

    s = raw.strip().lower()
    if s in ("", "low"):
        return genai_types.ThinkingLevel.LOW
    if s == "medium":
        return genai_types.ThinkingLevel.MEDIUM
    if s == "high":
        return genai_types.ThinkingLevel.HIGH
    if s == "minimal":
        return genai_types.ThinkingLevel.MINIMAL
    if s in ("unspecified", "api_default", "default"):
        return None
    print(f"WARNING: Unknown GEMINI_THINKING_LEVEL={raw!r}; using LOW.", file=sys.stderr)
    return genai_types.ThinkingLevel.LOW


def env_thinking_level():
    return _thinking_level_from_str(os.environ.get("GEMINI_THINKING_LEVEL", ""))


def gemini_complete(
    *,
    system_instruction: str,
    user_text: str,
    model: str | None = None,
    thinking_level: str | None = None,
    max_output_tokens: int | None = None,
    temperature: float | None = None,
    response_mime_type: str | None = None,
    response_json_schema: dict[str, Any] | None = None,
) -> str:
    """
    One Gemini ``generate_content`` turn. Raises if ``GEMINI_API_KEY`` is missing.

    Optional ``model``, ``thinking_level``, ``max_output_tokens``, ``temperature``,
    ``response_mime_type`` (e.g. ``application/json``), and ``response_json_schema`` override
    defaults when provided (used by pivot / NagV / policy refinement).
    """
    load_repo_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it to .env at the repo root (see .env.example)."
        )

    from google import genai
    from google.genai import types as genai_types

    model_eff = (model if model is not None else os.environ.get("GEMINI_MODEL", "gemini-3.1-pro-preview")).strip()
    temperature_eff = (
        float(temperature) if temperature is not None else float(os.environ.get("GEMINI_TEMPERATURE", "0.0"))
    )
    max_out = (
        int(max_output_tokens)
        if max_output_tokens is not None
        else int(os.environ.get("GEMINI_MAX_OUTPUT_TOKENS", "16384"))
    )
    thinking_level_eff = (
        _thinking_level_from_str(thinking_level) if thinking_level is not None else env_thinking_level()
    )

    cfg_kwargs: dict = {
        "system_instruction": system_instruction,
        "temperature": temperature_eff,
        "max_output_tokens": max_out,
    }
    if response_mime_type:
        cfg_kwargs["response_mime_type"] = response_mime_type.strip()
    if response_json_schema is not None:
        cfg_kwargs["response_json_schema"] = response_json_schema
    if thinking_level_eff is not None:
        cfg_kwargs["thinking_config"] = genai_types.ThinkingConfig(
            thinking_level=thinking_level_eff,
        )

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model_eff,
        contents=user_text,
        config=genai_types.GenerateContentConfig(**cfg_kwargs),
    )
    return (response.text or "").strip()
