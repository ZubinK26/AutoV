from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pivot_pipeline.cross_critic_agent import CrossCriticOutputError, CrossCriticReport
from pivot_pipeline.cross_critic_interactive_loop import (
    CrossCriticResumeAtGate,
    fetch_cross_critic_report,
)


def test_fetch_cross_critic_interactive_retry(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls = {"n": 0}

    def fake_with_repairs(*_a, **_k):
        calls["n"] += 1
        if calls["n"] == 1:
            raise CrossCriticOutputError("invalid", repair_attempts=3)
        return "{}", CrossCriticReport(verdict="PASS"), 0

    monkeypatch.setattr(
        "pivot_pipeline.cross_critic_interactive_loop.run_cross_critic_parsed_with_repairs",
        fake_with_repairs,
    )
    inputs = iter(["retry"])
    raw, report = fetch_cross_critic_report(
        "nl",
        "lin",
        work_dir=tmp_path,
        summary={},
        interactive_any=True,
        input_fn=lambda _p: next(inputs),
        print_fn=MagicMock(),
    )
    assert raw == "{}"
    assert report.verdict == "PASS"
    assert calls["n"] == 2


def test_fetch_cross_critic_api_503_resume_at_gate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("PIVOT_CROSS_CRITIC_API_AUTO_RETRIES", "1")

    def boom(*_a, **_k):
        raise RuntimeError("503 UNAVAILABLE")

    monkeypatch.setattr(
        "pivot_pipeline.cross_critic_interactive_loop.run_cross_critic_parsed_with_repairs",
        boom,
    )
    with pytest.raises(CrossCriticResumeAtGate):
        fetch_cross_critic_report(
            "nl",
            "lin",
            work_dir=tmp_path,
            summary={},
            interactive_any=True,
            input_fn=lambda _p: "",
            print_fn=lambda *_a, **_k: None,
            resume_at_gate=True,
        )


def test_fetch_cross_critic_api_503_auto_retries_then_ok(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("PIVOT_CROSS_CRITIC_API_AUTO_RETRIES", "3")
    calls = {"n": 0}

    def flaky(*_a, **_k):
        calls["n"] += 1
        if calls["n"] <= 3:
            raise RuntimeError("503 UNAVAILABLE")
        return "{}", CrossCriticReport(verdict="PASS"), 0  # succeeds on 4th call

    monkeypatch.setattr(
        "pivot_pipeline.cross_critic_interactive_loop.run_cross_critic_parsed_with_repairs",
        flaky,
    )
    raw, report = fetch_cross_critic_report(
        "nl",
        "lin",
        work_dir=tmp_path,
        summary={},
        interactive_any=False,
        input_fn=lambda _p: "",
        print_fn=lambda *_a, **_k: None,
    )
    assert report.verdict == "PASS"
    assert calls["n"] == 4
