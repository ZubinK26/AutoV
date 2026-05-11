"""Roundtrip back-translate ↔ re-formalize ↔ equivalence."""

from __future__ import annotations

import json

import cpmpy as cp

from cpmpy_wfm_policy.pipeline.formalizer import FormalizerOutput
from cpmpy_wfm_policy.verification.roundtrip import (
    expressions_equivalent,
    parse_back_translator_json,
    run_roundtrip_one_rule,
)


def test_expressions_equivalent_same():
    x = cp.intvar(0, 9, name="n")
    assert expressions_equivalent(x >= 3, x >= 3)


def test_expressions_equivalent_differ():
    x = cp.intvar(0, 9, name="n")
    assert not expressions_equivalent(x >= 3, x >= 4)


def test_parse_back_translator_json_legacy_nl_rule():
    r = parse_back_translator_json('{"nl_rule": "Amount must be at least 5."}')
    assert r.sentence == "Amount must be at least 5."
    assert r.confidence == "medium"


def test_parse_back_translator_json_spec_shape():
    r = parse_back_translator_json(
        '{"back_translation": "The amount must be at least five.", "confidence": "high", "ambiguity_notes": ""}'
    )
    assert r.sentence == "The amount must be at least five."
    assert r.confidence == "high"


def test_run_roundtrip_one_rule_mocked_ok(tmp_path):
    sig = tmp_path / "signature.py"
    gloss = tmp_path / "glossary.md"
    sig.write_text(
        "import cpmpy as cp\namount_cents = cp.intvar(0, 1_000_000, name='amount_cents')\n",
        encoding="utf-8",
    )
    gloss.write_text("# test", encoding="utf-8")

    payload = {
        "rule_module": "import cpmpy as cp\nrule_1 = amount_cents >= 500\n",
        "used_symbols": ["amount_cents"],
        "uses_global_constraints": False,
        "uses_vector_variables": False,
    }

    def formalizer(*, system_instruction: str, user_text: str) -> str:
        return json.dumps(payload)

    def backTranslator(*, system_instruction: str, user_text: str) -> str:
        return json.dumps(
            {
                "back_translation": "Paraphrase of the threshold rule.",
                "confidence": "high",
                "ambiguity_notes": "",
            }
        )

    orig = FormalizerOutput(
        rule_index=1,
        rule_name="rule_1",
        rule_module=payload["rule_module"],
        used_symbols=frozenset(payload["used_symbols"]),
        uses_global_constraints=False,
        uses_vector_variables=False,
        raw_response="",
    )
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "rt_sig", sig, submodule_search_locations=[]
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    setattr(mod, "rule_1", mod.amount_cents >= 500)
    orig_expr = mod.rule_1

    res = run_roundtrip_one_rule(
        orig_out=orig,
        orig_expr=orig_expr,
        nl_original="Refund amount must be at least five dollars.",
        formalizer_llm=formalizer,
        back_translator_llm=backTranslator,
        signature_path=str(sig),
        glossary_path=str(gloss),
    )
    assert res.equivalent
    assert res.detail == "ok"
