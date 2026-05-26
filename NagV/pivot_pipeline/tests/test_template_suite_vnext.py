from __future__ import annotations

import json
from pathlib import Path

from pivot_pipeline.template_suite.run import run_template_suite

FIX = Path(__file__).resolve().parent / "fixtures"
RULES = FIX / "extract_vnext_golden_rules.json"
SUITE = FIX / "template_suite_vnext_suite.json"


def test_vnext_template_suite_all_pass() -> None:
    report = run_template_suite(
        suite_path=SUITE,
        rules_extracted_path=RULES,
        write_report=False,
    )
    assert report["summary"]["failed"] == 0, json.dumps(report["results"], indent=2)
    assert report["summary"]["errors"] == 0
    assert report["summary"]["passed"] == 8
