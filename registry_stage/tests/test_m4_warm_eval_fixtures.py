"""M4 warm-registry eval fixtures load without error."""

from __future__ import annotations

from pathlib import Path

from registry_stage.loaders import load_handoff_bundle


def _fixture_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "eval_fixtures"


def test_m4_warm_seed_and_reuse_bundles_parse() -> None:
    d = _fixture_dir()
    seed = load_handoff_bundle(d / "m4_warm_seed_bundle.json")
    reuse = load_handoff_bundle(d / "m4_warm_reuse_bundle.json")
    assert seed.bundle_id == "m4_eval_seed_bu"
    assert reuse.bundle_id == "m4_eval_reuse_bu"
    assert len(seed.lines) == 2
    assert len(reuse.lines) == 2
    assert all(ln.agent3_verdict == "PASS" for ln in seed.lines)
    assert all(ln.agent3_verdict == "PASS" for ln in reuse.lines)
