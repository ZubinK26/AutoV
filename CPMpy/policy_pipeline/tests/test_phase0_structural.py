"""Phase 0 structural self-checks (Slice 0.1) and JSON parsing helpers."""

from __future__ import annotations

import json
from pathlib import Path

from cpmpy_wfm_policy.pipeline.drafting.glossary_drafter import parse_glossary_drafter_response
from cpmpy_wfm_policy.pipeline.drafting.phase0_models import SignatureCritique, critique_finding_count
from cpmpy_wfm_policy.pipeline.drafting.signature_critic import parse_signature_critic_response
from cpmpy_wfm_policy.pipeline.drafting.signature_refiner import parse_signature_refiner_response
from cpmpy_wfm_policy.pipeline.drafting.structural_check_glossary import (
    check_glossary_structure,
    required_glossary_symbols_from_signature,
)
from cpmpy_wfm_policy.pipeline.drafting.structural_check_signature import check_signature_file, check_signature_structure


def _domains(name: str) -> Path:
    return Path(__file__).resolve().parent.parent / "domains" / name


def test_refund_signature_structural_ok():
    dom = _domains("refund_example")
    rep = check_signature_file(
        dom / "signature.py",
        tools_json_path=dom / "tools.json",
        require_tools_json_alignment=True,
    )
    assert rep.pass_, [f.to_jsonable() for f in rep.findings]


def test_inventory_signature_structural_ok():
    dom = _domains("inventory_alldiff")
    rep = check_signature_file(
        dom / "signature.py",
        tools_json_path=dom / "tools.json",
        require_tools_json_alignment=True,
    )
    assert rep.pass_, [f.to_jsonable() for f in rep.findings]


def test_syntax_error_reported():
    rep = check_signature_structure(
        "def incomplete_fn(\n",
        tools_json_path=None,
        require_tools_json_alignment=False,
    )
    assert not rep.pass_
    assert any(f.code == "syntax_error" for f in rep.findings)


def test_forbidden_toplevel():
    src = "import cpmpy as cp\ndef foo():\n    pass\n"
    rep = check_signature_structure(src, tools_json_path=None, require_tools_json_alignment=False)
    assert not rep.pass_
    assert any(f.code == "forbidden_toplevel" for f in rep.findings)


def test_required_glossary_symbols_refund():
    sig = (_domains("refund_example") / "signature.py").read_text(encoding="utf-8")
    syms = required_glossary_symbols_from_signature(sig)
    assert "customer_kyc_status" in syms
    assert "KYC_STATUS" in syms
    assert "TOOL_DEPENDENCIES" not in syms


def test_glossary_check_minimal_yaml():
    yaml_text = """
KYC_STATUS:
  type: enum
  description: Enumeration used to classify customer verification states for the model.
  value_meanings:
    0: verified customer state
    1: failed verification state
  example_nl_phrases:
    - customer KYC must be verified before we approve any goodwill credit
    - refunds are blocked when the customer has failed verification checks
x:
  type: scalar_field
  description: Placeholder scalar used only for this structural unit test example.
  example_nl_phrases:
    - this is a phrase with at least five words for the glossary checker
    - another phrase with at least five words included here for validation
"""
    rep = check_glossary_structure(yaml_text, required_symbols=["KYC_STATUS", "x"])
    assert rep.pass_, [f.to_jsonable() for f in rep.findings]


def test_critic_json_roundtrip():
    raw = json.dumps(
        {
            "missing_fields": [
                {
                    "detail": "need field foo",
                    "confidence": "high",
                    "motivating_rule_text": "Rule line that appears in rules.txt for grounding.",
                }
            ],
            "surplus_fields": [],
            "suspicious_bounds": [{"motivating_rule_text": "no rule"}],
            "incomplete_enums": [],
            "naming_violations": [],
            "helper_concerns": [],
            "tools_signature_mismatch": [],
            "cross_section_inconsistencies": [],
        }
    )
    c = parse_signature_critic_response(raw)
    assert isinstance(c, SignatureCritique)
    assert len(c.missing_fields) == 1
    assert critique_finding_count(c) == 2


def test_refiner_json_with_decisions_list():
    raw = json.dumps(
        {
            "signature_py": "import cpmpy as cp\nTOOL_DEPENDENCIES = {}\n",
            "decisions": [
                {
                    "critic_section": "missing_fields",
                    "concern_index": 0,
                    "disposition": "accept",
                    "reasoning": "added foo",
                }
            ],
        }
    )
    out = parse_signature_refiner_response(raw)
    assert "TOOL_DEPENDENCIES" in out.signature_py
    assert len(out.decisions) == 1


def test_refiner_json_accepts_refiner_decisions_alias():
    raw = json.dumps(
        {
            "signature_py": "x = 1\n",
            "refiner_decisions": [
                {"critic_section": "missing_fields", "concern_index": 0, "disposition": "reject", "reasoning": "n/a"},
            ],
        }
    )
    out = parse_signature_refiner_response(raw)
    assert len(out.decisions) == 1


def test_glossary_phrase_grounding_in_rules():
    rules = (
        "The customer KYC must be verified before we approve any goodwill"
        " credit in this program. Refunds are blocked when the customer has failed verification checks."
    )
    yaml_text = """
KYC_STATUS:
  type: enum
  description: Enumeration used to classify customer verification states for the model.
  value_meanings:
    0: verified customer state
    1: failed verification state
  example_nl_phrases:
    - customer KYC must be verified before we approve any goodwill credit
    - refunds are blocked when the customer has failed verification checks
"""
    ok = check_glossary_structure(
        yaml_text, required_symbols=["KYC_STATUS"], rules_text=rules, inferred_phrase_symbols=frozenset()
    )
    assert ok.pass_, [f.to_jsonable() for f in ok.findings]

    bad = check_glossary_structure(
        yaml_text.replace(
            "refunds are blocked when the customer has failed verification checks",
            "completely fabricated phrase not in the rules text at all here",
        ),
        required_symbols=["KYC_STATUS"],
        rules_text=rules,
        inferred_phrase_symbols=frozenset(),
    )
    assert not bad.pass_
    assert any(f.code == "glossary_phrase_not_in_rules" for f in bad.findings)


def test_glossary_inferred_symbol_skips_phrase_grounding():
    rules = "Only the first phrase appears in rules for this test scenario here."
    yaml_text = """
KYC_STATUS:
  type: enum
  description: Enumeration used to classify customer verification states for the model.
  value_meanings:
    0: verified customer state
    1: failed verification state
  example_nl_phrases:
    - only the first phrase appears in rules for this test scenario here
    - this second phrase is invented but entry is marked inferred
"""
    rep = check_glossary_structure(
        yaml_text,
        required_symbols=["KYC_STATUS"],
        rules_text=rules,
        inferred_phrase_symbols=frozenset({"KYC_STATUS"}),
    )
    assert rep.pass_, [f.to_jsonable() for f in rep.findings]


def test_glossary_drafter_parse():
    y = (
        "a:\n  type: helper\n  description: "
        + ("word " * 5)
        + "\n  derives_from: [b]\n  example_nl_phrases:\n"
        "    - one two three four five six\n"
        "    - alpha beta gamma delta epsilon zeta\n"
    )
    raw = json.dumps({"glossary_yaml": y})
    o = parse_glossary_drafter_response(raw)
    assert "a:" in o.glossary_yaml
