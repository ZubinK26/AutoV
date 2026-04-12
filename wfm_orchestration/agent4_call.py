"""Single Agent 4 Gemini call (structured disagreement payload → assistant text)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO / "test_sets" / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "test_sets" / "scripts"))

import wfm_agent4_common as w4  # noqa: E402


def call_agent4_gemini(user_payload: str, *, system: str | None = None) -> str:
    """Return Agent 4 assistant text (no file write)."""
    w4.load_repo_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            f"Set GEMINI_API_KEY in {_REPO / '.env'} or environment."
        )
    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError as e:
        raise RuntimeError("pip install -r test_sets/requirements-wfm-test.txt") from e

    if system is None:
        system = w4.extract_system_prompt(_REPO / "WFM" / "prompts" / "agent_4_user_interaction.md")
    model = os.environ.get("GEMINI_MODEL", w4.DEFAULT_MODEL).strip()
    temperature = float(os.environ.get("GEMINI_TEMPERATURE", str(w4.DEFAULT_TEMPERATURE)))
    max_out = int(os.environ.get("GEMINI_MAX_OUTPUT_TOKENS", str(w4.DEFAULT_MAX_OUTPUT_TOKENS)))

    thinking_level = None
    raw_tl = os.environ.get("GEMINI_THINKING_LEVEL", "").strip().lower()
    if raw_tl not in ("", "low", "unspecified", "api_default", "default"):
        if raw_tl == "medium":
            thinking_level = genai_types.ThinkingLevel.MEDIUM
        elif raw_tl == "high":
            thinking_level = genai_types.ThinkingLevel.HIGH
        else:
            thinking_level = genai_types.ThinkingLevel.LOW

    client = genai.Client(api_key=api_key)
    cfg_kwargs: dict = {
        "system_instruction": system,
        "temperature": temperature,
        "max_output_tokens": max_out,
    }
    if thinking_level is not None:
        cfg_kwargs["thinking_config"] = genai_types.ThinkingConfig(thinking_level=thinking_level)

    response = client.models.generate_content(
        model=model,
        contents=user_payload,
        config=genai_types.GenerateContentConfig(**cfg_kwargs),
    )
    return (response.text or "").strip()
