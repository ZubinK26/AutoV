from __future__ import annotations

import json

from pivot_pipeline.critic_agent import (
    format_critic_report_terminal,
    parse_critic_response,
    pivot_critic_passed,
)


def test_critic_pass_last_verdict_pass() -> None:
    text = "<audit>\n- ok\n</audit>\n[VERDICT: PASS]"
    assert pivot_critic_passed(text) is True


def test_critic_pass_drifts_on_last_verdict() -> None:
    text = "[VERDICT: PASS]\nLater: [VERDICT: DRIFT]"
    assert pivot_critic_passed(text) is False


def test_critic_pass_missing_verdict() -> None:
    assert pivot_critic_passed("no verdict here") is False


def test_parse_critic_structured_json() -> None:
    payload = {
        "verdict": "DRIFT",
        "compared_against": "effective_nl",
        "findings": [
            {
                "id": "C001",
                "severity": "warn",
                "category": "threshold",
                "nl_pointer": "cost <= 1000",
                "synthetic_pointer": "R0001",
                "explanation": "Threshold mismatch",
            }
        ],
        "audit_trail_bullets": ["Checked pathway"],
        "notes": "",
    }
    raw = json.dumps(payload)
    r = parse_critic_response(raw)
    assert r.verdict == "DRIFT"
    assert r.findings[0].id == "C001"
    assert "DRIFT" in format_critic_report_terminal(r)


def test_parse_critic_pass_json() -> None:
    raw = json.dumps(
        {
            "verdict": "PASS",
            "compared_against": "effective_nl",
            "findings": [],
            "audit_trail_bullets": [],
            "notes": "",
        }
    )
    assert parse_critic_response(raw).verdict == "PASS"
    assert pivot_critic_passed(raw) is True
