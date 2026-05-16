from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pivot_pipeline.critic_agent import CriticFinding, CriticReport
from pivot_pipeline.policy_gates import REPAIR_CRITIC_DRIFT_TOKEN
from pivot_pipeline.semantic_critic_loop import (
    BLOCKED_SEMANTIC_REPAIR_COMPILE,
    run_semantic_critic_interactive_loop,
)


def test_failed_compile_does_not_re_run_critic_before_next_gate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """After repair fails compile, the loop must not immediately invoke the critic again."""
    monkeypatch.setenv("PIVOT_CRITIC_SEMANTIC_REPAIR_MAX", "3")
    monkeypatch.setenv("PIVOT_CRITIC_SEMANTIC_REPAIR_COMPILE_ATTEMPTS", "2")

    critic_calls = 0

    def fake_critic(*_a, **_k):
        nonlocal critic_calls
        critic_calls += 1
        r = CriticReport(
            verdict="DRIFT",
            findings=[
                CriticFinding(
                    id="C001",
                    severity="critical",
                    category="omission",
                    explanation="test",
                )
            ],
        )
        return "{}", r

    monkeypatch.setattr(
        "pivot_pipeline.semantic_critic_loop.run_pivot_critic_parsed",
        fake_critic,
    )

    fake_out = MagicMock()
    fake_out.change_summary = []
    fake_out.rules = []

    monkeypatch.setattr(
        "pivot_pipeline.semantic_critic_loop.run_repairer_piv_semantic",
        lambda **_k: (fake_out, False),
    )

    def boom(_policy_id: str, _rules: object):
        msg = "did not compile"
        raise ValueError(msg)

    monkeypatch.setattr(
        "pivot_pipeline.semantic_critic_loop.load_rules_and_compile",
        boom,
    )

    inputs = iter([REPAIR_CRITIC_DRIFT_TOKEN, ""])

    _, _, _, _, _, _, early = run_semantic_critic_interactive_loop(
        work_dir=tmp_path,
        nl_text_for_artifacts="nl",
        nl_for_precheck=tmp_path / "n.md",
        nl_lines_reg=[],
        policy_id="p",
        rules=[],
        meta_path=tmp_path / "m.json",
        skip_registry=True,
        no_llm=False,
        interactive_any=True,
        print_fn=lambda *_a, **_k: None,
        input_fn=lambda _p: next(inputs),
        summary={},
        synth="synthetic",
        meta=None,
        z3_result={},
        ok=True,
        issues=[],
    )

    assert critic_calls == 1
    assert early == "blocked_critic"


def test_exhaust_repair_sessions_returns_blocked_semantic_repair_compile(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("PIVOT_CRITIC_SEMANTIC_REPAIR_MAX", "1")
    monkeypatch.setenv("PIVOT_CRITIC_SEMANTIC_REPAIR_COMPILE_ATTEMPTS", "1")

    def fake_critic(*_a, **_k):
        return "{}", CriticReport(
            verdict="DRIFT",
            findings=[CriticFinding(id="C001", severity="warn", category="other", explanation="x")],
        )

    monkeypatch.setattr(
        "pivot_pipeline.semantic_critic_loop.run_pivot_critic_parsed",
        fake_critic,
    )

    fake_out = MagicMock()
    fake_out.change_summary = []
    fake_out.rules = []

    monkeypatch.setattr(
        "pivot_pipeline.semantic_critic_loop.run_repairer_piv_semantic",
        lambda **_k: (fake_out, False),
    )

    monkeypatch.setattr(
        "pivot_pipeline.semantic_critic_loop.load_rules_and_compile",
        lambda *_a, **_k: (_ for _ in ()).throw(ValueError("compile failed")),
    )

    summary: dict = {}
    _, _, _, _, _, _, early = run_semantic_critic_interactive_loop(
        work_dir=tmp_path,
        nl_text_for_artifacts="nl",
        nl_for_precheck=tmp_path / "n.md",
        nl_lines_reg=[],
        policy_id="p",
        rules=[],
        meta_path=tmp_path / "m.json",
        skip_registry=True,
        no_llm=False,
        interactive_any=True,
        print_fn=lambda *_a, **_k: None,
        input_fn=lambda _p: REPAIR_CRITIC_DRIFT_TOKEN,
        summary=summary,
        synth="synthetic",
        meta=None,
        z3_result={},
        ok=True,
        issues=[],
    )

    assert early == BLOCKED_SEMANTIC_REPAIR_COMPILE
    assert summary.get("outcome") == BLOCKED_SEMANTIC_REPAIR_COMPILE
