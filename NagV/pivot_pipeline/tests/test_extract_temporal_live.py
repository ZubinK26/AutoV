from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from pivot_pipeline.extract import extract_one_line_with_repairs, validate_rule_dict

FIX = Path(__file__).resolve().parent / "fixtures"
GOLDEN = FIX / "extract_temporal_nl_golden.json"


@pytest.mark.skipif(
    not os.getenv("PIVOT_RUN_LLM_EXTRACT"),
    reason="set PIVOT_RUN_LLM_EXTRACT=1 to run live temporal extract smoke",
)
@pytest.mark.parametrize(
    "case",
    json.loads(GOLDEN.read_text(encoding="utf-8"))["cases"],
    ids=lambda c: c["pattern_id"],
)
def test_extract_temporal_live_smoke(case: dict) -> None:
    from pivot_pipeline.extract import _extract_prompt_template

    out = extract_one_line_with_repairs(
        case["nl_line"],
        line_index=1,
        tmpl=_extract_prompt_template(),
    )
    exp = dict(case["expected_rule"])
    got = validate_rule_dict(out, line_index=1)
    assert got["template_class"] == exp["template_class"]
