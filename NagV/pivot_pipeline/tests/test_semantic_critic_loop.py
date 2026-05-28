from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pivot_pipeline.critic_agent import CriticFinding, CriticReport
from pivot_pipeline.policy_gates import REPAIR_CRITIC_DRIFT_TOKEN
from pivot_pipeline.semantic_repair_apply import SemanticRepairSessionResult
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
        "pivot_pipeline.semantic_repair_apply.run_repairer_piv_semantic",
        lambda **_k: (fake_out, False),
    )

    def boom(_policy_id: str, _rules: object):
        msg = "did not compile"
        raise ValueError(msg)

    monkeypatch.setattr(
        "pivot_pipeline.semantic_repair_apply.precompile_repaired_rules_validated",
        lambda *_a, **_k: boom("p", []),
    )

    inputs = iter(["y", REPAIR_CRITIC_DRIFT_TOKEN, ""])

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
    monkeypatch.setattr(
        "pivot_pipeline.semantic_critic_loop.critic_repair_max_rounds",
        lambda: 1,
    )

    def fake_critic(*_a, **_k):
        return "{}", CriticReport(
            verdict="DRIFT",
            findings=[
                CriticFinding(
                    id="C001",
                    severity="warn",
                    category="omission",
                    explanation="synthetic index missing detail",
                )
            ],
        )

    monkeypatch.setattr(
        "pivot_pipeline.semantic_critic_loop.run_pivot_critic_parsed",
        fake_critic,
    )

    session_calls: list[int] = []

    def fake_session(**_k):
        session_calls.append(1)
        return SemanticRepairSessionResult(
            success=False,
            rules=[],
            last_stage="rules_compile",
            last_error="compile failed",
        )

    monkeypatch.setattr(
        "pivot_pipeline.semantic_repair_apply.run_semantic_repair_session",
        fake_session,
    )
    monkeypatch.setattr(
        "pivot_pipeline.semantic_critic_loop.run_semantic_repair_session",
        fake_session,
    )

    inputs = iter(["y", REPAIR_CRITIC_DRIFT_TOKEN, ""])
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
        with_cross_repair=False,
        print_fn=lambda *_a, **_k: None,
        input_fn=lambda _p: next(inputs),
        summary=summary,
        synth="synthetic",
        meta=None,
        z3_result={},
        ok=True,
        issues=[],
    )

    assert len(session_calls) == 1, f"early={early!r} outcome={summary.get('outcome')!r}"
    assert early == BLOCKED_SEMANTIC_REPAIR_COMPILE
    assert summary.get("outcome") == BLOCKED_SEMANTIC_REPAIR_COMPILE


def test_api_503_does_not_burn_compile_attempt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("PIVOT_CRITIC_SEMANTIC_REPAIR_MAX", "0")
    monkeypatch.setenv("PIVOT_CRITIC_SEMANTIC_REPAIR_COMPILE_ATTEMPTS", "2")

    def fake_critic(*_a, **_k):
        return "{}", CriticReport(
            verdict="DRIFT",
            findings=[
                CriticFinding(
                    id="C001",
                    severity="warn",
                    category="omission",
                    explanation="synthetic index gap",
                )
            ],
        )

    monkeypatch.setattr(
        "pivot_pipeline.semantic_critic_loop.run_pivot_critic_parsed",
        fake_critic,
    )

    calls = {"n": 0}

    def flaky_repairer(**_k):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("503 UNAVAILABLE")
        fake_out = MagicMock()
        fake_out.change_summary = []
        fake_out.rules = [{"rule_id": "R0001"}]
        return fake_out, False

    monkeypatch.setattr(
        "pivot_pipeline.semantic_repair_apply.run_repairer_piv_semantic",
        flaky_repairer,
    )
    monkeypatch.setattr(
        "pivot_pipeline.semantic_repair_apply.precompile_repaired_rules_validated",
        lambda _p, rules, **_k: (rules, {}),
    )

    def fake_refresh(**_kw):
        return ([], MagicMock(), "synth", {}, True, [], None)

    monkeypatch.setattr(
        "pivot_pipeline.semantic_repair_apply.apply_repaired_rules_and_refresh",
        fake_refresh,
    )

    inputs = iter(["y", REPAIR_CRITIC_DRIFT_TOKEN, "y", ""])

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
        with_cross_repair=False,
        print_fn=lambda *_a, **_k: None,
        input_fn=lambda _p: next(inputs),
        summary={},
        synth="synthetic",
        meta=None,
        z3_result={},
        ok=True,
        issues=[],
    )

    assert calls["n"] == 2
    assert early == "blocked_critic"


def test_unlimited_sessions_return_to_gate_after_failed_repair(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("PIVOT_CRITIC_SEMANTIC_REPAIR_MAX", "0")
    monkeypatch.setenv("PIVOT_CRITIC_SEMANTIC_REPAIR_COMPILE_ATTEMPTS", "1")

    critic_calls = 0

    def fake_critic(*_a, **_k):
        nonlocal critic_calls
        critic_calls += 1
        return "{}", CriticReport(
            verdict="DRIFT",
            findings=[
                CriticFinding(
                    id="C001",
                    severity="warn",
                    category="omission",
                    explanation="synthetic index gap",
                )
            ],
        )

    monkeypatch.setattr(
        "pivot_pipeline.semantic_critic_loop.run_pivot_critic_parsed",
        fake_critic,
    )

    fake_out = MagicMock()
    fake_out.change_summary = []
    fake_out.rules = []

    monkeypatch.setattr(
        "pivot_pipeline.semantic_repair_apply.run_repairer_piv_semantic",
        lambda **_k: (fake_out, False),
    )
    monkeypatch.setattr(
        "pivot_pipeline.semantic_repair_apply.precompile_repaired_rules_validated",
        lambda *_a, **_k: (_ for _ in ()).throw(ValueError("compile failed")),
    )

    inputs = iter(["y", REPAIR_CRITIC_DRIFT_TOKEN, REPAIR_CRITIC_DRIFT_TOKEN, ""])

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
    assert (tmp_path / "critic_drift_handoff.json").is_file()
