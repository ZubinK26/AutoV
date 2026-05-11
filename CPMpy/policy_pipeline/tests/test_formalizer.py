"""Formalizer envelope + AST validation (mocked LLM)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cpmpy_wfm_policy.pipeline.formalizer import (
    FormalizerError,
    FormalizerOutput,
    formalize_one_rule,
    materialize_rule_expression,
)
from cpmpy_wfm_policy.pipeline.ast_validator import load_signature_namespace


def _domain_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "domains" / "refund_example"


def test_formalize_mock_transaction_posted():
    sig = _domain_dir() / "signature.py"
    gloss = _domain_dir() / "glossary.md"

    payload = {
        "rule_module": "import cpmpy as cp\nrule_1 = transaction_is_posted\n",
        "used_symbols": ["transaction_is_posted"],
        "uses_global_constraints": False,
        "uses_vector_variables": False,
    }

    def llm(*, system_instruction: str, user_text: str) -> str:
        return json.dumps(payload)

    out = formalize_one_rule(
        nl_rule="Transaction must be POSTED.",
        rule_index=1,
        signature_path=str(sig),
        glossary_path=str(gloss),
        llm=llm,
    )
    assert isinstance(out, FormalizerOutput)
    assert out.rule_name == "rule_1"
    expr = materialize_rule_expression(out, str(sig))
    ns = load_signature_namespace(str(sig))
    from cpmpy.transformations.get_variables import get_variables

    assert {v.name for v in get_variables(expr)} == {
        v.name for v in get_variables(ns["transaction_is_posted"])
    }


def test_formalize_rejects_wrong_rule_index():
    sig = _domain_dir() / "signature.py"
    gloss = _domain_dir() / "glossary.md"
    payload = {
        "rule_module": "import cpmpy as cp\nrule_9 = transaction_is_posted\n",
        "used_symbols": ["transaction_is_posted"],
        "uses_global_constraints": False,
        "uses_vector_variables": False,
    }

    def llm(*, system_instruction: str, user_text: str) -> str:
        return json.dumps(payload)

    with pytest.raises(FormalizerError, match="rule name"):
        formalize_one_rule(
            nl_rule="dummy",
            rule_index=1,
            signature_path=str(sig),
            glossary_path=str(gloss),
            llm=llm,
        )


def test_formalize_rules_file_mock(tmp_path: Path):
    rules = tmp_path / "rules.txt"
    rules.write_text("First NL line.\nSecond NL line.\n", encoding="utf-8")

    def llm(*, system_instruction: str, user_text: str) -> str:
        import re

        m = re.search(r"Variable name to assign to:\s*rule_(\d+)", user_text)
        assert m is not None
        idx = int(m.group(1))
        if idx == 1:
            mod = "import cpmpy as cp\nrule_1 = transaction_is_posted\n"
            syms = ["transaction_is_posted"]
        else:
            mod = "import cpmpy as cp\nrule_2 = ~customer_kyc_failed\n"
            syms = ["customer_kyc_failed"]
        return json.dumps(
            {
                "rule_module": mod,
                "used_symbols": syms,
                "uses_global_constraints": False,
                "uses_vector_variables": False,
            }
        )

    from cpmpy_wfm_policy.pipeline.formalizer import formalize_rules_file

    outs = formalize_rules_file(
        rules_txt_path=str(rules),
        signature_path=str(_domain_dir() / "signature.py"),
        glossary_path=str(_domain_dir() / "glossary.md"),
        llm=llm,
    )
    assert len(outs) == 2
    assert outs[0].rule_name == "rule_1"
    assert outs[1].rule_name == "rule_2"


def test_formalize_rejects_bad_json():
    def llm(*, system_instruction: str, user_text: str) -> str:
        return "not json"

    with pytest.raises(FormalizerError, match="invalid_json"):
        formalize_one_rule(
            nl_rule="dummy",
            rule_index=1,
            signature_path=str(_domain_dir() / "signature.py"),
            glossary_path=str(_domain_dir() / "glossary.md"),
            llm=llm,
        )


def test_formalize_metadata_mismatch_caught():
    sig = _domain_dir() / "signature.py"
    gloss = _domain_dir() / "glossary.md"
    payload = {
        "rule_module": "import cpmpy as cp\nrule_1 = transaction_is_posted\n",
        "used_symbols": ["wrong"],
        "uses_global_constraints": False,
        "uses_vector_variables": False,
    }

    def llm(*, system_instruction: str, user_text: str) -> str:
        return json.dumps(payload)

    with pytest.raises(FormalizerError, match="ast_validation"):
        formalize_one_rule(
            nl_rule="dummy",
            rule_index=1,
            signature_path=str(sig),
            glossary_path=str(gloss),
            llm=llm,
        )
