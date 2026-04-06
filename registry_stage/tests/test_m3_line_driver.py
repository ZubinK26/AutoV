"""M3: line driver search + placeholder gap extraction + logging."""

from __future__ import annotations

import logging

import pytest

import registry_stage
from registry_stage.line_driver import (
    LineDriverConfig,
    build_search_query,
    extract_placeholder_gaps,
    run_search_and_gaps_for_line,
)
from registry_stage.models import RegistryEntry
from registry_stage.registry_session import RegistrySession
from registry_stage.semantic_index import StubKeywordSemanticIndex


def _acme_suite_session() -> RegistrySession:
    session = RegistrySession(semantic_index=StubKeywordSemanticIndex(), index_preference="stub")
    session.add_or_replace(
        RegistryEntry(
            id="sort_co",
            kind="sort",
            name="Company",
            nl_description="Commercial organization customer entities.",
            source_rule=[],
        )
    )
    session.add_or_replace(
        RegistryEntry(
            id="ent_acme",
            kind="constant",
            name="acme",
            parent_sort_id="sort_co",
            nl_description="Customer corporation Acme known for bulk orders.",
            source_rule=[],
        )
    )
    return session


def test_m3_version() -> None:
    assert registry_stage.__version__ == "0.0.m3"


def test_m3_hits_and_gaps_with_fixture(caplog: pytest.LogCaptureFixture) -> None:
    session = _acme_suite_session()
    line = "The team met Acme and BetaCorp about the merger."
    with caplog.at_level(logging.INFO, logger="registry_stage.line_driver"):
        result = run_search_and_gaps_for_line(session, line_index=0, statement_nl=line)

    assert any(h.entry_id == "ent_acme" for h in result.hits)
    assert "BetaCorp" in result.gap_spans
    assert "Acme" not in result.gap_spans

    messages = " ".join(r.getMessage() for r in caplog.records)
    assert "line_driver" in messages
    assert "hits=" in messages
    assert "gaps=" in messages


def test_m3_empty_registry_all_candidates_can_remain_gaps() -> None:
    session = RegistrySession(semantic_index=StubKeywordSemanticIndex(), index_preference="stub")
    line = "Acme talked to BetaCorp."
    result = run_search_and_gaps_for_line(session, line_index=2, statement_nl=line)
    assert result.hits == ()
    assert "BetaCorp" in result.gap_spans
    assert "Acme" in result.gap_spans


def test_m3_extra_search_context_in_query() -> None:
    q = build_search_query("Line only.", "Extra bundle\ncontext here.")
    assert "Line only." in q
    assert "Extra bundle" in q


def test_m3_placeholder_extractor_finds_camelcase() -> None:
    names = extract_placeholder_gaps("No match until BetaCorp appears.")
    assert "BetaCorp" in names


def test_m3_authoritative_threshold_filters_weak_hit() -> None:
    session = RegistrySession(semantic_index=StubKeywordSemanticIndex(), index_preference="stub")
    session.add_or_replace(
        RegistryEntry(
            id="sort_co",
            kind="sort",
            name="Company",
            nl_description="Sort for companies.",
            source_rule=[],
        )
    )
    session.add_or_replace(
        RegistryEntry(
            id="ent_zeta",
            kind="constant",
            name="zeta",
            parent_sort_id="sort_co",
            nl_description="Obscure codename zed zulu.",
            source_rule=[],
        )
    )
    session.add_or_replace(
        RegistryEntry(
            id="ent_acme",
            kind="constant",
            name="acme",
            parent_sort_id="sort_co",
            nl_description="Customer corporation Acme known for bulk orders.",
            source_rule=[],
        )
    )
    line = "Acme ships crates weekly."
    result = run_search_and_gaps_for_line(
        session,
        line_index=0,
        statement_nl=line,
        config=LineDriverConfig(authoritative_min_score=0.5),
    )
    assert result.authoritative_hits == ()
