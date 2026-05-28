from pivot_pipeline.critic_agent import CriticFinding, CriticReport
from pivot_pipeline.critic_finding_router import (
    classify_critic_finding,
    should_defer_semantic_repair,
)


def test_contradiction_routes_cross() -> None:
    f = CriticFinding(
        id="C001",
        severity="critical",
        category="contradiction",
        explanation="R0034 and R0036 application_status inconsistency",
    )
    assert classify_critic_finding(f) == "cross_coherence"


def test_omission_routes_semantic() -> None:
    f = CriticFinding(
        id="C002",
        severity="warn",
        category="omission",
        explanation="Synthetic index omits pathway description for refund policy",
    )
    assert classify_critic_finding(f) == "semantic_drift"


def test_defer_when_all_cross_and_cross_repair_enabled() -> None:
    report = CriticReport(
        verdict="DRIFT",
        findings=[
            CriticFinding(
                id="C001",
                severity="critical",
                category="contradiction",
                explanation="aggregate gate R0036 escalation",
            )
        ],
    )
    defer, _ = should_defer_semantic_repair(
        approved_ids={"C001"},
        report=report,
        with_cross_repair=True,
    )
    assert defer
