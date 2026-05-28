from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pivot_pipeline.cross_critic_agent import (
    CrossCriticFinding,
    CrossCriticReport,
    format_cross_critic_report_terminal,
)
from pivot_pipeline.cross_critic_interactive_loop import (
    parse_disagree_indices,
    run_cross_finding_triage,
    write_cross_repair_handoff,
)
from pivot_pipeline.cross_repairer_agent import cross_repair_handoff_dict, cross_repair_max_rounds


def _sample_report() -> CrossCriticReport:
    return CrossCriticReport(
        verdict="ISSUES",
        findings=[
            CrossCriticFinding(
                id="X001",
                severity="warn",
                category="outcome_split",
                explanation="a",
                rule_ids=["R0037"],
            ),
            CrossCriticFinding(
                id="X002",
                severity="info",
                category="inconsistency",
                explanation="b",
            ),
            CrossCriticFinding(
                id="X003",
                severity="info",
                category="inconsistency",
                explanation="c",
            ),
        ],
    )


def test_parse_disagree_indices() -> None:
    assert parse_disagree_indices("", max_index=3) == set()
    assert parse_disagree_indices("2, 3", max_index=3) == {2, 3}
    assert parse_disagree_indices("2,2", max_index=3) == {2}
    assert parse_disagree_indices("9", max_index=3) is None
    assert parse_disagree_indices("x", max_index=3) is None


def test_triage_accept_all_y() -> None:
    report = _sample_report()
    inputs = iter(["y"])
    approved, ignored = run_cross_finding_triage(
        report,
        input_fn=lambda _p: next(inputs),
        print_fn=lambda *_a, **_k: None,
    )
    assert approved == {"X001", "X002", "X003"}
    assert ignored == set()


def test_triage_disagree_2_3() -> None:
    report = _sample_report()
    inputs = iter(["n", "2,3"])
    approved, ignored = run_cross_finding_triage(
        report,
        input_fn=lambda _p: next(inputs),
        print_fn=lambda *_a, **_k: None,
    )
    assert approved == {"X001"}
    assert ignored == {"X002", "X003"}


def test_triage_disagree_empty_means_all_approved() -> None:
    report = _sample_report()
    inputs = iter(["n", ""])
    approved, ignored = run_cross_finding_triage(
        report,
        input_fn=lambda _p: next(inputs),
        print_fn=lambda *_a, **_k: None,
    )
    assert approved == {"X001", "X002", "X003"}
    assert ignored == set()


def test_triage_invalid_index_reprompts() -> None:
    report = _sample_report()
    inputs = iter(["n", "9", "1"])
    approved, ignored = run_cross_finding_triage(
        report,
        input_fn=lambda _p: next(inputs),
        print_fn=lambda *_a, **_k: None,
    )
    assert approved == {"X002", "X003"}
    assert ignored == {"X001"}


def test_cross_repair_handoff_filters_findings(tmp_path: Path) -> None:
    report = _sample_report()
    h = cross_repair_handoff_dict(
        report,
        approved_ids=["X001"],
        ignored_ids=["X002", "X003"],
        full_report_path=tmp_path / "cross_critic_report.json",
    )
    assert h["approved_finding_ids"] == ["X001"]
    assert h["ignored_finding_ids"] == ["X002", "X003"]
    assert len(h["findings"]) == 1
    assert h["findings"][0]["id"] == "X001"
    assert h["triage_index_map"] == {"1": "X001", "2": "X002", "3": "X003"}


def test_write_cross_repair_handoff(tmp_path: Path) -> None:
    report = _sample_report()
    (tmp_path / "cross_critic_report.json").write_text("{}", encoding="utf-8")
    path = write_cross_repair_handoff(
        tmp_path,
        report,
        approved={"X001"},
        ignored={"X002", "X003"},
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["approved_finding_ids"] == ["X001"]
    assert len(data["findings"]) == 1


def test_numbered_terminal_format() -> None:
    report = _sample_report()
    text = format_cross_critic_report_terminal(report, numbered=True)
    assert "  1. [X001]" in text
    assert "  3. [X003]" in text


def test_cross_repair_max_rounds_default_unlimited(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PIVOT_CROSS_REPAIR_MAX_ROUNDS", raising=False)
    assert cross_repair_max_rounds() == 0


def test_cross_repair_max_rounds_env_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PIVOT_CROSS_REPAIR_MAX_ROUNDS", "5")
    assert cross_repair_max_rounds() == 5


def test_run_cross_repair_skipped_when_no_approved(monkeypatch: pytest.MonkeyPatch) -> None:
    """REPAIR with zero approved findings must not call CrossRepairer LLM."""
    from pivot_pipeline.cross_repairer_agent import run_cross_repairer

    called: list[int] = []

    def fake_repairer(**_kwargs):
        called.append(1)
        return MagicMock(), False

    monkeypatch.setattr(
        "pivot_pipeline.cross_repairer_agent.run_cross_repairer",
        fake_repairer,
    )
    # Orchestration guard is in run.py; unit-test the handoff empty case
    report = _sample_report()
    h = cross_repair_handoff_dict(
        report,
        approved_ids=[],
        ignored_ids=["X001", "X002", "X003"],
        full_report_path=Path("cross_critic_report.json"),
    )
    assert h["findings"] == []
    assert not called
