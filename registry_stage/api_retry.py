"""Transient API error retries (503 / UNAVAILABLE / rate limits) for Gemini and related callers."""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def is_transient_api_error(exc: BaseException) -> bool:
    """503 / UNAVAILABLE / rate-limit style errors worth retrying."""
    code = getattr(exc, "status_code", None)
    if code in (503, 429):
        return True
    msg = str(exc).upper()
    return "503" in msg or "UNAVAILABLE" in msg or "RATE" in msg or "QUOTA" in msg


def transient_api_retry_sleep_seconds() -> float:
    """Pause between retries; default 1.5s (``PIVOT_API_RETRY_SLEEP_SEC``)."""
    raw = os.getenv("PIVOT_API_RETRY_SLEEP_SEC", "1.5").strip()
    try:
        return max(0.0, min(float(raw), 60.0))
    except ValueError:
        return 1.5


def api_auto_retries_max(
    *,
    env_var: str | None = None,
    fallback_env: str = "PIVOT_API_AUTO_RETRIES",
) -> int | None:
    """
    Max automatic retries on transient API errors.

    ``0`` or explicit ``0`` on the chosen env var = unlimited.
    Checks ``env_var`` first, then ``fallback_env``.
    """
    for key in (env_var, fallback_env):
        if not key:
            continue
        raw = os.getenv(key, "").strip()
        if raw == "":
            continue
        if raw == "0":
            return None
        try:
            return max(1, min(int(raw), 100))
        except ValueError:
            break
    return None


def _stderr_print(*args: object, **kwargs: object) -> None:
    print(*args, **kwargs, file=sys.stderr, flush=True)


def call_with_transient_api_retries(
    fn: Callable[[], T],
    *,
    label: str = "api",
    max_retries: int | None = None,
    print_fn: Callable[..., None] | None = None,
) -> T:
    """
    Retry ``fn`` on transient API errors with a fixed sleep between attempts.

    ``max_retries`` is the number of *retries after the first failure* (not total calls).
    ``None`` = unlimited.
    """
    attempt = 0
    sleep_s = transient_api_retry_sleep_seconds()
    log = print_fn if print_fn is not None else _stderr_print
    while True:
        try:
            return fn()
        except Exception as e:
            if not is_transient_api_error(e):
                raise
            attempt += 1
            if max_retries is not None and attempt > max_retries:
                raise
            cap_lbl = f"{attempt}/{max_retries}" if max_retries is not None else str(attempt)
            log(
                f"\n[{label}] transient API error ({cap_lbl}): {e}\n"
                f"  Retrying in {sleep_s:g}s…\n",
            )
            time.sleep(sleep_s)


__all__ = [
    "api_auto_retries_max",
    "call_with_transient_api_retries",
    "is_transient_api_error",
    "transient_api_retry_sleep_seconds",
]
