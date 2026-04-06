"""
Thin Gemini caller — env contract aligned with ``test_sets/wfm_api_contract_gemini.md``.

Do not import ``test_sets/scripts/*.py``; parity is maintained by matching the same variables
and ``google.genai`` usage as ``run_wfm_folio_gemini.call_gemini``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def repo_root_containing_registry_stage() -> Path:
    """``registry_stage/llm/`` → parents[2] = repo root (has ``bundles/``, ``.env``)."""
    return Path(__file__).resolve().parents[2]


def load_repo_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    env_file = repo_root_containing_registry_stage() / ".env"
    if env_file.is_file():
        load_dotenv(env_file, override=False)


def env_thinking_level():
    from google.genai import types as genai_types

    raw = os.environ.get("GEMINI_THINKING_LEVEL", "").strip().lower()
    if raw in ("", "low"):
        return genai_types.ThinkingLevel.LOW
    if raw == "medium":
        return genai_types.ThinkingLevel.MEDIUM
    if raw == "high":
        return genai_types.ThinkingLevel.HIGH
    if raw == "minimal":
        return genai_types.ThinkingLevel.MINIMAL
    if raw in ("unspecified", "api_default", "default"):
        return None
    print(f"WARNING: Unknown GEMINI_THINKING_LEVEL={raw!r}; using LOW.", file=sys.stderr)
    return genai_types.ThinkingLevel.LOW


def gemini_complete(*, system_instruction: str, user_text: str) -> str:
    """
    One Gemini ``generate_content`` turn. Raises if ``GEMINI_API_KEY`` is missing.
    """
    load_repo_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it to .env at the repo root (see .env.example)."
        )

    from google import genai
    from google.genai import types as genai_types

    model = os.environ.get("GEMINI_MODEL", "gemini-3.1-pro-preview").strip()
    temperature = float(os.environ.get("GEMINI_TEMPERATURE", "0.0"))
    max_out = int(os.environ.get("GEMINI_MAX_OUTPUT_TOKENS", "16384"))
    thinking_level = env_thinking_level()

    cfg_kwargs: dict = {
        "system_instruction": system_instruction,
        "temperature": temperature,
        "max_output_tokens": max_out,
    }
    if thinking_level is not None:
        cfg_kwargs["thinking_config"] = genai_types.ThinkingConfig(
            thinking_level=thinking_level,
        )

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=user_text,
        config=genai_types.GenerateContentConfig(**cfg_kwargs),
    )
    return (response.text or "").strip()
