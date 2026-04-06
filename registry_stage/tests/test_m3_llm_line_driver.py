"""M3 LLM path: mocked Gemini (expansion + structured gaps), fusion / concat modes."""

from __future__ import annotations

import json

from registry_stage.line_driver import LineDriverConfig, candidate_covered, run_search_and_gaps_for_line
from registry_stage.models import RegistryEntry, StructuredGap
from registry_stage.registry_session import RegistrySession
from registry_stage.semantic_index import StubKeywordSemanticIndex


def _session_acme() -> RegistrySession:
    s = RegistrySession(semantic_index=StubKeywordSemanticIndex(), index_preference="stub")
    s.add_or_replace(
        RegistryEntry(
            id="sort_co",
            kind="sort",
            name="Company",
            nl_description="Commercial organizations.",
            source_rule=[],
        )
    )
    s.add_or_replace(
        RegistryEntry(
            id="ent_acme",
            kind="constant",
            name="acme",
            parent_sort_id="sort_co",
            nl_description="Customer corporation Acme known for bulk orders.",
            source_rule=[],
        )
    )
    return s


def _fake_llm_factory() -> tuple[list[tuple[str, str]], object]:
    log: list[tuple[str, str]] = []

    def fake(system: str, user: str) -> str:
        log.append((system[:40], user[:80]))
        if '"authoritative_registry_coverage"' in user:
            return json.dumps(
                {
                    "gaps": [
                        {
                            "surface": "BetaCorp",
                            "kind": "constant",
                            "arity_hint": None,
                            "domain_hints": [],
                            "notes": "Second company",
                        }
                    ]
                }
            )
        return json.dumps({"phrases": ["bulk customer orders", "commercial contracts"]})

    return log, fake


def test_m3_llm_mock_expansion_and_structured_gaps() -> None:
    _, llm = _fake_llm_factory()
    session = _session_acme()
    line = "The team met Acme and BetaCorp about contracts."
    res = run_search_and_gaps_for_line(
        session,
        line_index=1,
        statement_nl=line,
        config=LineDriverConfig(
            enable_llm=True,
            llm_complete=llm,
            query_mode="multi_query_fuse",
        ),
    )
    assert res.expansion_phrases
    assert len(res.search_queries_used) >= 2
    assert any("BetaCorp" in g for g in res.gap_spans)
    assert res.structured_gaps and res.structured_gaps[0].surface == "BetaCorp"
    assert isinstance(res.structured_gaps[0], StructuredGap)


def test_m3_llm_single_concat_mode_one_query_string() -> None:
    _, llm = _fake_llm_factory()
    session = _session_acme()
    line = "Acme and BetaCorp met."
    res = run_search_and_gaps_for_line(
        session,
        0,
        line,
        config=LineDriverConfig(
            enable_llm=True,
            llm_complete=llm,
            query_mode="single_concat",
        ),
    )
    assert len(res.search_queries_used) == 1
    assert "bulk customer" in res.search_queries_used[0] or "commercial" in res.search_queries_used[0]


def test_masking_conservative_stricter_on_substring_acme() -> None:
    coverage = "the acmecorp holding company"
    assert candidate_covered("Acme", coverage, "standard") is True
    assert candidate_covered("Acme", coverage, "conservative") is False


def test_llm_logs_calls_for_observability() -> None:
    log, llm = _fake_llm_factory()
    session = _session_acme()
    run_search_and_gaps_for_line(
        session,
        0,
        "Line",
        config=LineDriverConfig(enable_llm=True, llm_complete=llm),
    )
    assert len(log) == 2

