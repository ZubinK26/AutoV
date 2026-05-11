"""Pre-deployment consistency (slice 7)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from cpmpy_wfm_policy.pipeline.ast_validator import global_constraints_from_namespace, load_signature_namespace
from cpmpy_wfm_policy.pipeline.consistency import ConsistencyError, run_pre_deploy_consistency
from cpmpy_wfm_policy.wfm_import.adapter import materialize_domain_bundle_from_handoff


def _root() -> Path:
    r = Path(__file__).resolve().parents[1]
    if str(r) not in sys.path:
        sys.path.insert(0, str(r))
    return r


def test_consistency_refund_handwritten():
    from domains.refund_example import handwritten_rules as hr

    sig = str(_root() / "domains" / "refund_example" / "signature.py")
    gc = global_constraints_from_namespace(load_signature_namespace(sig))
    rmap = hr.all_rules()
    rep = run_pre_deploy_consistency(
        rule_exprs=list(rmap.values()),
        rule_ids=list(rmap.keys()),
        global_constraints=gc,
        gated_tools=["apply_refund"],
    )
    assert rep["joint_sat"]
    assert rep["coverage"]["apply_refund"]["legal_exists"]
    assert rep["coverage"]["apply_refund"]["illegal_exists"]


def test_consistency_inventory_second_domain():
    from domains.inventory_alldiff import handwritten_rules as hr

    sig = str(_root() / "domains" / "inventory_alldiff" / "signature.py")
    gc = global_constraints_from_namespace(load_signature_namespace(sig))
    rmap = hr.all_rules()
    rep = run_pre_deploy_consistency(
        rule_exprs=list(rmap.values()),
        rule_ids=list(rmap.keys()),
        global_constraints=gc,
        gated_tools=["apply_refund"],
    )
    assert rep["joint_sat"]


def test_consistency_joint_unsat_raises():
    import cpmpy as cp

    x = cp.boolvar(name="b")
    with pytest.raises(ConsistencyError, match="UNSAT"):
        run_pre_deploy_consistency(
            rule_exprs=[x, ~x],
            rule_ids=["rule_1", "rule_2"],
            global_constraints=None,
            gated_tools=["t"],
        )


def test_wfm_materialize_handoff(tmp_path: Path):
    handoff = {
        "schema_version": "registry_persistence_v1",
        "lines": [
            {"statement_nl": "First policy line.", "agent3_verdict": "PASS"},
            {"statement_nl": "Skip me.", "agent3_verdict": "FAIL"},
        ],
    }
    p = tmp_path / "h.json"
    p.write_text(json.dumps(handoff), encoding="utf-8")
    out = tmp_path / "bundle"
    materialize_domain_bundle_from_handoff(
        handoff_path=p, out_dir=out, warn_stderr=False
    )
    text = (out / "rules.txt").read_text(encoding="utf-8").strip()
    assert text.splitlines() == ["First policy line."]
    assert json.loads((out / "tools.json").read_text(encoding="utf-8"))["tools"]


def test_cli_validate_domain_refund_example():
    from cpmpy_wfm_policy.cli import cmd_validate_domain

    d = Path(__file__).resolve().parents[1] / "domains" / "refund_example"
    assert cmd_validate_domain(d) == 0


def test_inventory_signature_has_vector_and_global():
    root = _root()
    sigp = root / "domains" / "inventory_alldiff" / "signature.py"
    ns = load_signature_namespace(str(sigp))
    assert ns.get("GLOBAL_CONSTRAINTS")
    bc = ns.get("bin_counts")
    assert bc is not None and getattr(bc, "shape", None) is not None
