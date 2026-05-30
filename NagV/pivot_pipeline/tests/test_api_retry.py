from __future__ import annotations

import time

import pytest

from pivot_pipeline.api_retry import call_with_transient_api_retries, transient_api_retry_sleep_seconds


def test_transient_api_retry_sleep_default() -> None:
    assert transient_api_retry_sleep_seconds() == 1.5


def test_transient_api_retry_sleep_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PIVOT_API_RETRY_SLEEP_SEC", "2.5")
    assert transient_api_retry_sleep_seconds() == 2.5


def test_retries_503_until_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PIVOT_API_RETRY_SLEEP_SEC", "0")
    sleeps: list[float] = []
    monkeypatch.setattr(time, "sleep", sleeps.append)
    calls = {"n": 0}

    def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("503 UNAVAILABLE")
        return "ok"

    assert call_with_transient_api_retries(flaky, max_retries=None) == "ok"
    assert calls["n"] == 3


def test_retries_cap_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PIVOT_API_RETRY_SLEEP_SEC", "0")
    with pytest.raises(RuntimeError, match="503"):
        call_with_transient_api_retries(
            lambda: (_ for _ in ()).throw(RuntimeError("503 UNAVAILABLE")),
            max_retries=2,
        )
