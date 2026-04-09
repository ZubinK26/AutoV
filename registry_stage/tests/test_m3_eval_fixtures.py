"""Smoke: committed M3 business eval fixtures load and line driver runs (no LLM)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from registry_stage.line_driver import LineDriverConfig, run_search_and_gaps_for_line
from registry_stage.loaders import load_registry
from registry_stage.registry_session import RegistrySession
from registry_stage.semantic_index import StubKeywordSemanticIndex


FIXTURE_DIR = Path(__file__).resolve().parent.parent / "eval_fixtures"


def test_m3_business_fixtures_exist() -> None:
    assert (FIXTURE_DIR / "m3_business_registry.json").is_file()
    assert (FIXTURE_DIR / "m3_business_lines.json").is_file()


def test_m3_retrieval_eval_fixtures_exist() -> None:
    assert (FIXTURE_DIR / "m3_retrieval_eval_registry.json").is_file()
    assert (FIXTURE_DIR / "m3_retrieval_eval_lines.json").is_file()
    assert (FIXTURE_DIR / "m3_retrieval_eval_labels.json").is_file()


def test_m3_retrieval_eval_registry_loads() -> None:
    reg = load_registry(FIXTURE_DIR / "m3_retrieval_eval_registry.json")
    ids = {e.id for e in reg.entries}
    assert "ent_contoso_trading" in ids
    assert "ent_sku_9910" in ids


def test_m3_business_registry_loads() -> None:
    reg = load_registry(FIXTURE_DIR / "m3_business_registry.json")
    assert len(reg.entries) >= 5
    ids = {e.id for e in reg.entries}
    assert "ent_acme_ltd" in ids
    assert "ent_betacorp" in ids


@pytest.mark.parametrize("line_id", ["biz_po_pallets", "biz_betacorp_confirm", "biz_gamma_vendor"])
def test_m3_business_line_runs_stub_index(line_id: str) -> None:
    reg = load_registry(FIXTURE_DIR / "m3_business_registry.json")
    session = RegistrySession.from_entries(
        reg.entries,
        semantic_index=StubKeywordSemanticIndex(),
        index_preference="stub",
    )
    data = json.loads((FIXTURE_DIR / "m3_business_lines.json").read_text(encoding="utf-8"))
    match = next(x for x in data["lines"] if x["id"] == line_id)
    st = match["statement_nl"]
    res = run_search_and_gaps_for_line(
        session,
        int(match["line_index"]),
        st,
        config=LineDriverConfig(enable_llm=False),
    )
    assert res.statement_nl == st
    assert isinstance(res.gap_spans, tuple)
