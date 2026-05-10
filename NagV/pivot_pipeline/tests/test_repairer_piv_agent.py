from __future__ import annotations

import json

import pytest

from pivot_pipeline.repairer_piv_agent import (
    repairer_json_parse_retry_count,
    run_repairer_piv_semantic,
    run_repairer_piv_structural,
)


def test_repairer_json_parse_retry_second_llm_succeeds_structural(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"n": 0}
    good = json.dumps(
        {
            "rules": [{"rule_id": "R0001", "template_class": "CONSTANT_RELATIONAL"}],
            "change_summary": [{"rule_id": "R0001", "change": "fix"}],
        }
    )

    def fake_llm(_p: str) -> str:
        calls["n"] += 1
        if calls["n"] == 1:
            return "not json {"
        return good

    monkeypatch.setenv("PIVOT_REPAIRER_JSON_PARSE_RETRIES", "1")
    out, used_retry = run_repairer_piv_structural(
        policy_id="t",
        rules=[{"rule_id": "R0001"}],
        error_text="compile failed",
        llm=fake_llm,
    )
    assert calls["n"] == 2
    assert used_retry is True
    assert len(out.rules) == 1


def test_repairer_json_parse_retry_second_llm_succeeds_semantic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"n": 0}
    good = json.dumps(
        {
            "rules": [{"rule_id": "R0001", "template_class": "CONSTANT_RELATIONAL"}],
            "change_summary": [{"finding_id": "C001", "change": "fix"}],
        }
    )

    def fake_llm(_p: str) -> str:
        calls["n"] += 1
        if calls["n"] == 1:
            return "```broken"
        return good

    monkeypatch.setenv("PIVOT_REPAIRER_JSON_PARSE_RETRIES", "2")
    out, used_retry = run_repairer_piv_semantic(
        policy_id="t",
        rules=[{"rule_id": "R0001"}],
        handoff={"source": "critic", "findings": []},
        effective_nl_excerpt="line",
        synthetic_excerpt="syn",
        llm=fake_llm,
    )
    assert calls["n"] == 2
    assert used_retry is True
    assert out.rules[0]["rule_id"] == "R0001"


def test_repairer_json_parse_retries_exhausted_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PIVOT_REPAIRER_JSON_PARSE_RETRIES", "1")

    def fake_llm(_p: str) -> str:
        return "not json"

    with pytest.raises(ValueError):
        run_repairer_piv_structural(
            policy_id="t",
            rules=[],
            error_text="e",
            llm=fake_llm,
        )


def test_repairer_json_parse_retry_count_zero_no_extra_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PIVOT_REPAIRER_JSON_PARSE_RETRIES", "0")
    calls = {"n": 0}

    def fake_llm(_p: str) -> str:
        calls["n"] += 1
        return "bad"

    with pytest.raises(ValueError):
        run_repairer_piv_structural(policy_id="t", rules=[], error_text="e", llm=fake_llm)
    assert calls["n"] == 1


def test_repairer_json_parse_retry_count_clamp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PIVOT_REPAIRER_JSON_PARSE_RETRIES", "99")
    assert repairer_json_parse_retry_count() == 3
    monkeypatch.setenv("PIVOT_REPAIRER_JSON_PARSE_RETRIES", "-1")
    assert repairer_json_parse_retry_count() == 0


def test_first_parse_ok_no_retry_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PIVOT_REPAIRER_JSON_PARSE_RETRIES", "1")
    calls = {"n": 0}
    body = json.dumps({"rules": [], "change_summary": []})

    def fake_llm(_p: str) -> str:
        calls["n"] += 1
        return body

    out, used_retry = run_repairer_piv_structural(policy_id="t", rules=[], error_text="e", llm=fake_llm)
    assert calls["n"] == 1
    assert used_retry is False
    assert out.rules == []
