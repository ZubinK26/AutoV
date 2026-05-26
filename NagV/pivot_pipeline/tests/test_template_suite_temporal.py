from __future__ import annotations

import json
from pathlib import Path

from pivot_pipeline.template_suite.run import run_template_suite

FIX = Path(__file__).resolve().parent / "fixtures"
SUITE = FIX / "template_suite_temporal_smoke.json"


def _combined_rules_path(tmp_path: Path) -> Path:
    """Merge eight temporal fixture policies into one rules file for suite run."""
    manifest = json.loads(
        (FIX / "temporal_surrogates" / "temporal_surrogates_manifest.json").read_text(encoding="utf-8")
    )
    rules: list[dict] = []
    rid = 1
    for entry in manifest["patterns"]:
        body = json.loads(
            (FIX / "temporal_surrogates" / entry["rules_file"]).read_text(encoding="utf-8")
        )
        for r in body["rules"]:
            row = dict(r)
            row["rule_id"] = f"R{rid:04d}"
            rules.append(row)
            rid += 1
    out = {
        "policy_id": "temporal_combined_smoke",
        "policy_semantics_version": "1.1",
        "pivot_ir_extensions": ["vnext_8"],
        "rules": rules,
    }
    p = tmp_path / "rules_extracted.json"
    p.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return p


def test_temporal_template_suite_smoke(tmp_path: Path) -> None:
    rules_path = _combined_rules_path(tmp_path)
    report = run_template_suite(
        suite_path=SUITE,
        rules_extracted_path=rules_path,
        write_report=False,
    )
    assert report["summary"]["failed"] == 0, json.dumps(report["results"], indent=2)
    assert report["summary"]["errors"] == 0
    assert report["summary"]["passed"] == 8
