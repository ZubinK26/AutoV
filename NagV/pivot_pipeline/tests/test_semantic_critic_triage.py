from pivot_pipeline.critic_agent import CriticFinding, CriticReport
from pivot_pipeline.semantic_critic_triage import run_critic_finding_triage


def test_triage_disagree_one() -> None:
    report = CriticReport(
        verdict="DRIFT",
        findings=[
            CriticFinding(id="C001", severity="warn", category="other", explanation="a"),
            CriticFinding(id="C002", severity="warn", category="other", explanation="b"),
            CriticFinding(id="C003", severity="warn", category="other", explanation="c"),
        ],
    )
    inputs = iter(["n", "2", ""])
    approved, ignored = run_critic_finding_triage(
        report,
        input_fn=lambda _p: next(inputs),
        print_fn=lambda *_a, **_k: None,
    )
    assert approved == {"C001", "C003"}
    assert ignored == {"C002"}
