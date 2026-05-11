"""
Anthropic Claude caller for SMT formalizer/critic only (WFM remains Gemini).

Env (see ``.env.example``):
  ``ANTHROPIC_API_KEY``, ``ANTHROPIC_MODEL`` (default ``claude-sonnet-4-6`` if unset —
  must match a model enabled for your key), ``ANTHROPIC_MAX_TOKENS``,
  ``ANTHROPIC_TEMPERATURE`` (ignored when temperature is omitted; see below),
  ``ANTHROPIC_THINKING_BUDGET_TOKENS`` (nonzero enables extended thinking; incompatible with ``temperature``).

Some models (e.g. ``claude-opus-4-7``) return **400** if ``temperature`` is sent; we omit it for those.
Set ``ANTHROPIC_OMIT_TEMPERATURE=1`` to omit ``temperature`` for **any** model.
"""

from __future__ import annotations

import os
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def load_repo_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    env_file = _repo_root() / ".env"
    if env_file.is_file():
        load_dotenv(env_file, override=False)


def _omit_temperature_for_model(model_id: str) -> bool:
    """Anthropic deprecates ``temperature`` on some 4.x models (400 invalid_request_error)."""
    if os.environ.get("ANTHROPIC_OMIT_TEMPERATURE", "").strip().lower() in ("1", "true", "yes"):
        return True
    mid = model_id.strip().lower()
    return mid.startswith("claude-opus-4-")


def anthropic_complete(
    *,
    system_instruction: str,
    user_text: str,
    max_output_tokens: int | None = None,
) -> str:
    """
    One Messages API turn. Raises if ``ANTHROPIC_API_KEY`` is missing or ``anthropic`` is not installed.
    """
    load_repo_dotenv()
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Add it to .env at the repo root (see .env.example)."
        )
    try:
        import anthropic
    except ImportError as e:
        raise RuntimeError(
            "The `anthropic` package is required for Claude-backed SMT steps. "
            "Install with: pip install 'anthropic>=0.34'"
        ) from e

    model = os.environ.get(
        "ANTHROPIC_MODEL",
        "claude-sonnet-4-6",
    ).strip()
    temperature = float(os.environ.get("ANTHROPIC_TEMPERATURE", "0.0"))
    if max_output_tokens is not None:
        max_tokens = int(max_output_tokens)
    else:
        max_tokens = int(os.environ.get("ANTHROPIC_MAX_TOKENS", "16384"))

    tb_raw = os.environ.get("ANTHROPIC_THINKING_BUDGET_TOKENS", "").strip()
    thinking_budget: int | None
    if tb_raw in ("", "0"):
        thinking_budget = None
    else:
        thinking_budget = int(tb_raw)

    kwargs: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system_instruction,
        "messages": [{"role": "user", "content": user_text}],
    }
    if thinking_budget is not None:
        kwargs["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}
    elif not _omit_temperature_for_model(model):
        kwargs["temperature"] = temperature

    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(**kwargs)
    text_blocks = [b.text for b in msg.content if getattr(b, "type", None) == "text"]
    return "".join(text_blocks).strip()
