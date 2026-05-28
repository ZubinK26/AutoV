from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pivot_pipeline.repairer_piv_agent import RepairerPivOutput, RepairerChangeSummaryItem
from pivot_pipeline.semantic_repair_apply import run_semantic_repair_session


def test_registry_failure_does_not_recall_repairer(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repairer_calls = {"n": 0}
    registry_calls = {"n": 0}

    def fake_repairer(**_k):
        repairer_calls["n"] += 1
        return (
            RepairerPivOutput(
                rules=[{"rule_id": "R0001", "template_class": "CONSTANT_RELATIONAL", "variable": "x", "relational_operator": "EQ", "constant_value": 1, "yields": "SATISFIED", "applies_to": "GLOBAL"}],
                change_summary=[RepairerChangeSummaryItem(rule_id="R0001", change="fix")],
            ),
            False,
        )

    def fake_registry(**_k):
        registry_calls["n"] += 1
        if registry_calls["n"] < 2:
            raise ValueError("Expecting ',' delimiter: line 66 column 24 (char 2131)")
        return None, _k["merged_rules"], False

    monkeypatch.setattr(
        "pivot_pipeline.semantic_repair_apply.run_repairer_piv_semantic",
        fake_repairer,
    )
    monkeypatch.setattr(
        "pivot_pipeline.semantic_repair_apply.precompile_repaired_rules_validated",
        lambda _p, rules, **_k: (rules, {}),
    )
    monkeypatch.setattr(
        "pivot_pipeline.semantic_repair_apply.run_semantic_repair_registry",
        fake_registry,
    )
    monkeypatch.setattr(
        "pivot_pipeline.semantic_repair_apply.apply_repaired_rules_and_refresh",
        lambda **_k: ([], MagicMock(), "s", {}, True, [], None),
    )
    monkeypatch.setenv("PIVOT_CRITIC_SEMANTIC_REPAIR_REGISTRY_ATTEMPTS", "3")

    result = run_semantic_repair_session(
        work_dir=tmp_path,
        policy_id="p",
        rules=[],
        handoff={"findings": [{"id": "C001", "rule_ids": ["R0001"]}]},
        repair_session=1,
        nl_text_for_artifacts="nl",
        synth="syn",
        nl_lines_reg=[],
        skip_registry=False,
        meta_path=tmp_path / "m.json",
        nl_for_precheck=tmp_path / "n.md",
        summary={},
        print_fn=lambda *_a, **_k: None,
        llm=MagicMock(),
    )

    assert result.success
    assert repairer_calls["n"] == 1
    assert registry_calls["n"] == 2
