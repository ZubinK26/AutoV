from __future__ import annotations

import json
from pathlib import Path

from pivot_pipeline.extract import validate_rule_dict

FIX = Path(__file__).resolve().parent / "fixtures"
GOLDEN = FIX / "extract_temporal_nl_golden.json"


def test_extract_temporal_nl_golden_validate() -> None:
    data = json.loads(GOLDEN.read_text(encoding="utf-8"))
    for i, case in enumerate(data["cases"], start=1):
        rule = dict(case["expected_rule"])
        rule.setdefault("rule_id", f"R{i:04d}")
        rule.setdefault("applies_to", "GLOBAL")
        rule.setdefault("overrides", None)
        out = validate_rule_dict(rule, line_index=i)
        assert out["template_class"] == case["expected_rule"]["template_class"]
