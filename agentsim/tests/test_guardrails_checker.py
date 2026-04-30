"""Tests for :mod:`agentsim.runtime.guardrails_checker` against policy_model_refined.smt2."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("z3")

from agentsim.runtime.guardrails_checker import (
    GuardrailsPolicyChecker,
    GuardrailsVerdict,
    default_guardrails_policy_path,
    repo_root_from_here,
)
from agentsim.runtime.guardrails_scenario import (
    SPEC_WRITE_TOOL_PRIMARIES,
    GuardrailsScenario,
)


def _policy_path() -> Path:
    return default_guardrails_policy_path()


@pytest.fixture(scope="module")
def checker() -> GuardrailsPolicyChecker:
    path = _policy_path()
    if not path.is_file():
        pytest.skip(f"refined policy missing: {path}")
    return GuardrailsPolicyChecker(policy_path=path)


def test_default_policy_path_under_repo_root():
    root = repo_root_from_here()
    assert (root / "agentsim" / "runtime" / "guardrails_checker.py").is_file()
    p = default_guardrails_policy_path()
    assert p.name == "policy_model_refined.smt2"
    assert "04_agentic_guardrails" in str(p)


def test_escalate_entails_permitted(checker: GuardrailsPolicyChecker):
    s = GuardrailsScenario(primary_tool="escalate")
    d = checker.decide(s)
    assert d.verdict == GuardrailsVerdict.PERMITTED
    assert d.permitted()


def test_missing_entity_entails_denied(checker: GuardrailsPolicyChecker):
    s = GuardrailsScenario(
        primary_tool="apply_refund",
        references_missing_entity=True,
    )
    d = checker.decide(s)
    assert d.verdict == GuardrailsVerdict.DENIED
    assert not d.permitted()


def test_duplicate_prior_entails_denied(checker: GuardrailsPolicyChecker):
    s = GuardrailsScenario(
        primary_tool="apply_refund",
        duplicate_prior_allowed=True,
    )
    d = checker.decide(s)
    assert d.verdict == GuardrailsVerdict.DENIED


def test_closed_account_freeze_entails_denied(checker: GuardrailsPolicyChecker):
    s = GuardrailsScenario(
        primary_tool="freeze_card",
        account_status="CLOSED",
    )
    d = checker.decide(s)
    assert d.verdict == GuardrailsVerdict.DENIED


def test_initiate_unauthorized_permitted_or_ambiguous(checker: GuardrailsPolicyChecker):
    """Happy path initiate dispute: should not be outright denied by default grounding."""

    s = GuardrailsScenario(primary_tool="initiate_dispute", dispute_type="UNAUTHORIZED")
    d = checker.decide(s)
    assert d.verdict in (
        GuardrailsVerdict.PERMITTED,
        GuardrailsVerdict.AMBIGUOUS,
    )


@pytest.mark.parametrize("tool", SPEC_WRITE_TOOL_PRIMARIES)
def test_every_spec_write_tool_grounds_and_decides(checker: GuardrailsPolicyChecker, tool: str):
    """Each 01-surface write tool must emit a fragment that Z3 accepts (no init/parse errors)."""

    s = GuardrailsScenario(primary_tool=tool)
    d = checker.decide(s)
    assert d.verdict in (
        GuardrailsVerdict.PERMITTED,
        GuardrailsVerdict.DENIED,
        GuardrailsVerdict.AMBIGUOUS,
    )
