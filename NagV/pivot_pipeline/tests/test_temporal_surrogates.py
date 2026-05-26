from __future__ import annotations

import json
from pathlib import Path

import pytest

from pivot_pipeline.extract import validate_rule_dict
from pivot_pipeline.ir import load_rules_and_compile
from pivot_pipeline.rules_document import parse_rules_document

FIX = Path(__file__).resolve().parent / "fixtures" / "temporal_surrogates"
MANIFEST = FIX / "temporal_surrogates_manifest.json"
IMPROVED_SCOPE = Path(__file__).resolve().parents[3] / "improved-scope.md"


def _manifest_entries() -> list[dict]:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return list(data["patterns"])


@pytest.mark.parametrize("entry", _manifest_entries(), ids=lambda e: e["pattern_id"])
def test_temporal_golden_validate_and_compile(entry: dict) -> None:
    body = json.loads((FIX / entry["rules_file"]).read_text(encoding="utf-8"))
    policy_id, rules, envelope = parse_rules_document(body)
    for i, rule in enumerate(rules, start=1):
        validate_rule_dict(rule, line_index=i)
    meta = load_rules_and_compile(
        policy_id,
        rules,
        policy_semantics_version=envelope.get("policy_semantics_version"),
    )
    assert meta.policy_id == policy_id


@pytest.mark.parametrize("entry", _manifest_entries(), ids=lambda e: e["pattern_id"])
def test_temporal_z3_smoke(entry: dict) -> None:
    from pivot_pipeline.z3_compile import run_z3_check

    body = json.loads((FIX / entry["rules_file"]).read_text(encoding="utf-8"))
    policy_id, rules, envelope = parse_rules_document(body)
    meta = load_rules_and_compile(
        policy_id,
        rules,
        policy_semantics_version=envelope.get("policy_semantics_version"),
    )
    assert run_z3_check(meta)["status"] == "sat"


def test_temporal_manifest_covers_eight_patterns() -> None:
    ids = {e["pattern_id"] for e in _manifest_entries()}
    assert ids == {f"T{i}" for i in range(1, 9)}


def test_improved_scope_mentions_all_pattern_ids() -> None:
    text = IMPROVED_SCOPE.read_text(encoding="utf-8")
    for i in range(1, 9):
        assert f"**T{i}**" in text
