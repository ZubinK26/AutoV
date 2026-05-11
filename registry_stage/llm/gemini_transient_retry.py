"""Retry helpers for transient Google GenAI failures (503, 429, etc.)."""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def is_transient_gemini_error(exc: BaseException) -> bool:
    """True for capacity / rate / overload errors that are worth sleeping and retrying."""
    s = str(exc).lower()
    if any(
        x in s
        for x in (
            "503",
            "429",
            "504",
            "502",
            "500",
            "unavailable",
            "resource_exhausted",
            "try again",
            "overload",
            "high demand",
            "deadline exceeded",
            "timeout",
            "temporar",
        )
    ):
        return True
    try:
        from google.genai.errors import ServerError

        if isinstance(exc, ServerError):
            return True
    except ImportError:
        pass
    return False


def env_transient_retry_limits() -> tuple[int, float, float]:
    """(max_attempts, base_delay_sec, cap_delay_sec)."""
    try:
        n = int(os.environ.get("GEMINI_TRANSIENT_MAX_ATTEMPTS", "8").strip())
    except ValueError:
        n = 8
    n = max(1, min(n, 30))
    try:
        base = float(os.environ.get("GEMINI_TRANSIENT_BASE_SEC", "2.0").strip())
    except ValueError:
        base = 2.0
    base = max(0.5, min(base, 60.0))
    try:
        cap = float(os.environ.get("GEMINI_TRANSIENT_MAX_SEC", "120").strip())
    except ValueError:
        cap = 120.0
    cap = max(base, min(cap, 600.0))
    return n, base, cap


def run_with_transient_retries(
    op: Callable[[], T],
    *,
    log,
    what: str = "Gemini request",
) -> T:
    max_attempts, base_s, cap_s = env_transient_retry_limits()
    last: BaseException | None = None
    for attempt in range(max_attempts):
        try:
            return op()
        except Exception as e:
            last = e
            if attempt >= max_attempts - 1 or not is_transient_gemini_error(e):
                raise
            delay = min(cap_s, base_s * (2**attempt))
            log(
                f"[gemini] {what}: transient error ({e!s}); "
                f"sleep {delay:.1f}s then retry {attempt + 2}/{max_attempts}…"
            )
            time.sleep(delay)
    assert last is not None
    raise last


__all__ = [
    "env_transient_retry_limits",
    "is_transient_gemini_error",
    "run_with_transient_retries",
]
