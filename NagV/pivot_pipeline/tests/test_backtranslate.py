from __future__ import annotations

from pivot_pipeline.backtranslate import meta_scheme_to_markdown
from pivot_pipeline.ir import (
    ConditionAtom,
    LogicalImplication,
    Preemption,
    PreemptionAction,
    RelationalOperator,
)
from pivot_pipeline.pathway_compiler import build_meta_scheme


def test_synthetic_mentions_preemption_pathway_note() -> None:
    trig = ConditionAtom(variable="ip_verified", operator=RelationalOperator.EQ, value=False)
    rules = [
        Preemption(
            rule_id="R0005",
            preempting_condition=trig,
            action=PreemptionAction.FORCE_UNSATISFIED,
            target_rule_id=None,
        ),
    ]
    meta = build_meta_scheme(policy_id="p", rules=rules)
    md = meta_scheme_to_markdown(meta)
    assert "Pathway note (v1)" in md
    assert "non-PREEMPTION" in md
    assert "PREEMPTION detail" in md
    assert "R0005" in md
