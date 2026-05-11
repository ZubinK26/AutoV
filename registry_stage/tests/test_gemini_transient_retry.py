"""Unit tests for transient Gemini error detection."""

from __future__ import annotations

import pytest

from registry_stage.llm.gemini_transient_retry import (
    env_transient_retry_limits,
    is_transient_gemini_error,
    run_with_transient_retries,
)


@pytest.mark.parametrize(
    "msg,expected",
    [
        ("503 UNAVAILABLE", True),
        ("429 RESOURCE_EXHAUSTED", True),
        ("try again later", True),
        ("This model is currently experiencing high demand", True),
        ("invalid api key", False),
        ("400 bad request", False),
    ],
)
def test_is_transient_gemini_error_string_heuristics(msg: str, expected: bool) -> None:
    assert is_transient_gemini_error(RuntimeError(msg)) is expected


def test_run_with_transient_retries_succeeds_second_try(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}
    log: list[str] = []

    def op() -> int:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("503 UNAVAILABLE try again")
        return 42

    monkeypatch.setenv("GEMINI_TRANSIENT_MAX_ATTEMPTS", "4")
    monkeypatch.setenv("GEMINI_TRANSIENT_BASE_SEC", "0.01")
    monkeypatch.setenv("GEMINI_TRANSIENT_MAX_SEC", "0.05")

    assert run_with_transient_retries(op, log=log.append, what="test") == 42
    assert calls["n"] == 2
    assert len(log) == 1


def test_env_transient_retry_limits_clamped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_TRANSIENT_MAX_ATTEMPTS", "999")
    monkeypatch.setenv("GEMINI_TRANSIENT_BASE_SEC", "0.1")
    monkeypatch.setenv("GEMINI_TRANSIENT_MAX_SEC", "50")
    n, base, cap = env_transient_retry_limits()
    assert n == 30
    assert base == 0.5
    assert cap == 50
