"""API retry helpers for external tester LLM calls."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from pivot_pipeline.api_retry import api_auto_retries_max, call_with_transient_api_retries

T = TypeVar("T")


def external_tester_api_auto_retries() -> int | None:
    """
    ``PIVOT_EXTERNAL_TESTER_API_AUTO_RETRIES=0`` (default) = unlimited retries on API errors.
    Falls back to ``PIVOT_API_AUTO_RETRIES``.
    """
    return api_auto_retries_max(env_var="PIVOT_EXTERNAL_TESTER_API_AUTO_RETRIES")


def call_with_api_retries(fn: Callable[[], T], *, label: str) -> T:
    return call_with_transient_api_retries(
        fn,
        label=label,
        max_retries=external_tester_api_auto_retries(),
    )


__all__ = ["call_with_api_retries", "external_tester_api_auto_retries"]
