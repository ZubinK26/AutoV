import json
from importlib import resources
from pathlib import Path

import pytest

pytest.importorskip("z3")

from agentsim.runtime.policy_consistency import (
    build_consistency_report,
    deployment_should_fail,
)
from agentsim.runtime.snapshot import policy_v0_text
from agentsim.runtime.validate_policy import main as validate_policy_main


def test_consistency_report_policy_v0_matches_golden():
    report = build_consistency_report(policy_v0_text())
    golden_raw = resources.files("agentsim.runtime.data").joinpath(
        "consistency_report_policy_v0_golden.json",
    ).read_text(encoding="utf-8")
    golden = json.loads(golden_raw)
    assert report.to_json_obj() == golden
    assert not deployment_should_fail(report)


def test_contradictory_policy_unsat_and_cli_exit(tmp_path: Path):
    bad_text = resources.files("agentsim.runtime.data").joinpath(
        "policy_contradictory.smt2",
    ).read_text(encoding="utf-8")
    bad_path = tmp_path / "policy_contradictory.smt2"
    bad_path.write_text(bad_text, encoding="utf-8")

    report = build_consistency_report(bad_text)
    assert report.satisfiable is False
    assert len(report.contradictions) == 1
    assert deployment_should_fail(report)

    out = tmp_path / "report_bad.json"
    code = validate_policy_main([str(bad_path), "-o", str(out)])
    assert code == 1
    assert out.is_file()
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["satisfiable"] is False
