from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pivot_pipeline.critic_agent import CriticReport
from pivot_pipeline.semantic_critic_loop import run_pivot_critic_with_api_retries


def test_pivot_critic_interactive_retries_503_until_ok(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PIVOT_CRITIC_API_AUTO_RETRIES", "0")
    calls = {"n": 0}

    def flaky(*_a, **_k):
        calls["n"] += 1
        if calls["n"] < 4:
            raise RuntimeError("503 UNAVAILABLE")
        return "{}", CriticReport(verdict="PASS")

    monkeypatch.setattr(
        "pivot_pipeline.semantic_critic_loop.run_pivot_critic_parsed",
        flaky,
    )
    raw, report = run_pivot_critic_with_api_retries(
        "nl",
        "synth",
        interactive_any=True,
        print_fn=MagicMock(),
    )
    assert report.verdict == "PASS"
    assert calls["n"] == 4
