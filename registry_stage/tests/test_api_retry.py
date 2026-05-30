from __future__ import annotations

import time

import pytest

from registry_stage.api_retry import (
    call_with_transient_api_retries,
    is_transient_api_error,
    transient_api_retry_sleep_seconds,
)


def test_server_error_status_code() -> None:
    class Fake503(Exception):
        status_code = 503

    assert is_transient_api_error(Fake503("busy"))


def test_retries_503_until_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PIVOT_API_RETRY_SLEEP_SEC", "0")
    monkeypatch.setattr(time, "sleep", lambda _s: None)
    calls = {"n": 0}

    def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("503 UNAVAILABLE")
        return "ok"

    assert call_with_transient_api_retries(flaky, max_retries=None, print_fn=lambda *_a, **_k: None) == "ok"
    assert calls["n"] == 3


def test_sleep_default() -> None:
    assert transient_api_retry_sleep_seconds() == 1.5
