from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pivot_pipeline.cross_repair_apply import run_cross_repair_session
from pivot_pipeline.test_repair_rules_payload import MergeRepairerOutputError


def test_cross_repair_session_precompile_before_registry(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Registry must not run when pre-compile fails."""
    registry_called: list[int] = []

    def fake_registry(**_kwargs):
        registry_called.append(1)
        return None, _kwargs["merged_rules"], True

    monkeypatch.setattr(
        "pivot_pipeline.cross_repair_apply.run_cross_repair_registry",
        fake_registry,
    )

    calls = {"n": 0}

    def fake_repairer(**_kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            out = MagicMock()
            out.rules = [{"rule_id": "R0001", "template_class": "BAD"}]
            out.change_summary = []
            return out, False
        raise MergeRepairerOutputError("missing R0002")

    monkeypatch.setattr(
        "pivot_pipeline.cross_repair_apply.run_cross_repairer",
        fake_repairer,
    )

    def fail_precompile(*_a, **_k):
        raise ValueError("invalid template")

    monkeypatch.setattr(
        "pivot_pipeline.cross_repair_apply.precompile_repaired_rules_validated",
        lambda *_a, **_k: (_ for _ in ()).throw(ValueError("invalid template")),
    )

    result = run_cross_repair_session(
        work_dir=tmp_path,
        policy_id="t",
        rules=[{"rule_id": "R0001"}],
        handoff={"findings": [{"id": "X001", "rule_ids": ["R0001"]}]},
        cross_approved={"X001"},
        cross_ignored=set(),
        cross_repairs_used=1,
        processed_nl_excerpt="",
        linearized_excerpt="",
        nl_lines_reg=[],
        skip_registry=False,
        meta_path=tmp_path / "meta_scheme.json",
        nl_for_precheck=tmp_path / "nl.txt",
        summary={},
        rules_envelope={},
        no_vnext_lowering=False,
        print_fn=lambda *_a, **_k: None,
        llm=lambda _p: "{}",
    )
    assert not result.success
    assert registry_called == []
