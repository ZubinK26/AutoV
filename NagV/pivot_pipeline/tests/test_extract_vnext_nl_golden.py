from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from pivot_pipeline.extract import validate_rule_dict
from pivot_pipeline.ir import load_rules_and_compile

FIX = Path(__file__).resolve().parent / "fixtures"
GOLDEN = FIX / "extract_vnext_nl_golden.json"


@pytest.mark.parametrize("case", json.loads(GOLDEN.read_text(encoding="utf-8"))["cases"])
def test_nl_golden_expected_rule_validates(case: dict) -> None:
    rule = dict(case["expected_rule"])
    rule["rule_id"] = "R0001"
    out = validate_rule_dict(rule, line_index=1)
    assert out["template_class"] == case["template_class"]
    load_rules_and_compile("golden", [out], policy_semantics_version="1.1")


@pytest.mark.skipif(
    not os.environ.get("PIVOT_RUN_LLM_EXTRACT"),
    reason="Set PIVOT_RUN_LLM_EXTRACT=1 to run live extract e2e (uses Gemini).",
)
def test_extract_vnext_k_of_n_live_llm() -> None:
    """Optional live extract: one NL line → K_OF_N JSON (operator/CI only)."""
    from pivot_pipeline.extract import extract_one_line_with_repairs, _extract_prompt_template

    line = "At least 2 of: score at least 10, risk at most 5."
    rule = extract_one_line_with_repairs(
        1,
        line,
        tmpl=_extract_prompt_template(),
        prior_rules=[],
        max_repairs=2,
    )
    assert rule.get("template_class") in ("K_OF_N", "LOGICAL_IMPLICATION")
