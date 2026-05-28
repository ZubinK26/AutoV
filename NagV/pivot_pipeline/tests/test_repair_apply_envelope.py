from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pivot_pipeline.constants import PIVOT_IR_EXTENSIONS_MANIFEST, POLICY_SEMANTICS_VERSION_VNEXT
from pivot_pipeline.repair_apply import apply_repaired_rules_and_refresh


def test_apply_repaired_writes_vnext_envelope(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rules = [
        {
            "rule_id": "R1",
            "template_class": "K_OF_N",
            "k": 1,
            "clauses": [{"kind": "atom", "variable": "a", "operator": "EQ", "value": 1}],
        }
    ]
    meta = MagicMock()
    meta.model_dump_json = lambda indent=2: "{}"
    monkeypatch.setattr("pivot_pipeline.repair_apply.load_rules_and_compile", lambda *_a, **_k: meta)
    monkeypatch.setattr("pivot_pipeline.repair_apply.run_z3_check", lambda _m: {"status": "sat"})
    monkeypatch.setattr("pivot_pipeline.repair_apply.meta_scheme_to_markdown", lambda _m: "s")
    monkeypatch.setattr("pivot_pipeline.repair_apply.run_precheck", lambda **_k: (True, []))
    monkeypatch.setattr(
        "pivot_pipeline.repair_apply.build_and_write_assessment_artifacts",
        lambda **_k: "lin",
    )

    summary: dict = {
        "policy_semantics_version": POLICY_SEMANTICS_VERSION_VNEXT,
        "pivot_ir_extensions": [PIVOT_IR_EXTENSIONS_MANIFEST],
    }
    apply_repaired_rules_and_refresh(
        work_dir=tmp_path,
        policy_id="p",
        rules=rules,
        meta_path=tmp_path / "meta_scheme.json",
        nl_for_precheck=tmp_path / "n.txt",
        summary=summary,
        after_rules_basename="rules_after_test_repair.json",
        rules_envelope=summary,
    )
    body = json.loads((tmp_path / "rules_extracted.json").read_text(encoding="utf-8"))
    assert body["policy_semantics_version"] == POLICY_SEMANTICS_VERSION_VNEXT
    assert body["pivot_ir_extensions"] == [PIVOT_IR_EXTENSIONS_MANIFEST]

    stripped = {"policy_id": "p", "rules": rules}
    (tmp_path / "rules_extracted.json").write_text(json.dumps(stripped), encoding="utf-8")
    from pivot_pipeline.rules_document import parse_rules_document

    _pid, _rules, meta_out = parse_rules_document(stripped)
    assert meta_out["policy_semantics_version"] == POLICY_SEMANTICS_VERSION_VNEXT
