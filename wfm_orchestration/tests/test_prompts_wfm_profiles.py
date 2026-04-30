"""WFM prompt roots: ASP (`asp/wfm/`) vs SMT (`smt/wfm/`)."""

from __future__ import annotations

from wfm_orchestration.prompts_wfm import load_wfm_prompts, wfm_assets_root, repo_root


def test_wfm_assets_roots_exist() -> None:
    root = repo_root()
    asp = wfm_assets_root("asp", root=root)
    smt = wfm_assets_root("smt", root=root)
    assert (asp / "prompts" / "agent_3_scope_rewrite.md").is_file()
    assert (smt / "prompts" / "agent_3_scope_rewrite.md").is_file()
    assert asp.resolve() != smt.resolve()


def test_load_both_profiles_returns_non_empty_strings() -> None:
    p1a, p2a, p3a, p4a, lima = load_wfm_prompts("asp")
    p1s, p2s, p3s, p4s, lims = load_wfm_prompts("smt")
    for s in (p1a, p2a, p3a, p4a, p1s, p2s, p3s, p4s):
        assert isinstance(s, str)
        assert len(s) > 200
    assert lima == lims
    # Agent 3 scope text diverges between tracks (ClinCon vs many-sorted FOL).
    assert "ClinCon-safe" in p3a
    assert "ClinCon-safe" not in p3s


def test_frozen_smt_agent_3_known_phrase() -> None:
    smt = wfm_assets_root("smt")
    text = (smt / "prompts" / "agent_3_scope_rewrite.md").read_text(encoding="utf-8")
    assert "Finite declared sets" in text or "transitive closure" in text.lower()
