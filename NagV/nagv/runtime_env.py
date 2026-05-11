"""Process-level Gemini defaults for NagV (and WFM when invoked from NagV)."""

from __future__ import annotations

import os

_applied = False


def _set_process_gemini_thinking_level(token: str) -> None:
    """Assign ``GEMINI_THINKING_LEVEL`` from a repo contract token."""
    t = token.strip().lower()
    if t == "unspecified":
        os.environ["GEMINI_THINKING_LEVEL"] = "unspecified"
    elif t in ("", "low"):
        os.environ["GEMINI_THINKING_LEVEL"] = "low"
    elif t == "high":
        os.environ["GEMINI_THINKING_LEVEL"] = "high"
    elif t in ("medium", "minimal"):
        os.environ["GEMINI_THINKING_LEVEL"] = t
    else:
        os.environ["GEMINI_THINKING_LEVEL"] = t


def apply_nagv_gemini_defaults() -> None:
    """
    Set Gemini extended thinking for the **WFM** phase (and anything before post-WFM switch).

    NagV uses ``registry_stage.llm.gemini_call`` and WFM via ``wfm_orchestration``; both read
    ``GEMINI_THINKING_LEVEL`` from the environment.

    - Default: set ``GEMINI_THINKING_LEVEL=low``.
    - ``NAGV_GEMINI_THINKING_LEVEL=inherit`` — do not modify ``GEMINI_THINKING_LEVEL``.
    - Other values (``low``, ``medium``, ``high``, ``minimal``, ``unspecified``) set
      ``GEMINI_THINKING_LEVEL`` for the process accordingly (same strings as repo-wide contract).

    Formalizer/critic/repair use :func:`apply_nagv_gemini_post_wfm_thinking` after WFM completes.
    """
    global _applied
    if _applied:
        return

    raw = os.environ.get("NAGV_GEMINI_THINKING_LEVEL", "low").strip().lower()
    if raw in ("inherit", "keep", "no_override"):
        _applied = True
        return

    _set_process_gemini_thinking_level(raw)

    _applied = True


def apply_nagv_gemini_post_wfm_thinking() -> None:
    """
    Set ``GEMINI_THINKING_LEVEL`` after WFM for processes that read env (not the per-call
    override). Formalizer/repair pass ``medium`` explicitly; critic passes ``high``. Default
    here is ``medium`` so env matches non-critic agents.

    Set ``NAGV_POST_WFM_GEMINI_THINKING_LEVEL=inherit`` to leave the current process value
    unchanged.
    """
    raw = os.environ.get("NAGV_POST_WFM_GEMINI_THINKING_LEVEL", "medium").strip().lower()
    if raw in ("inherit", "keep", "no_override"):
        return
    if not raw:
        raw = "medium"
    _set_process_gemini_thinking_level(raw)
