"""M4 automated resolve + validation (mocked LLM)."""

from __future__ import annotations

import json

from registry_stage.line_driver import LineSearchGapsResult
from registry_stage.models import RegistryEntry, StructuredGap
from registry_stage.registry_session import RegistrySession
from registry_stage.resolve_automated import run_automated_resolve
from registry_stage.semantic_index import SearchHit, StubKeywordSemanticIndex


def _session_acme() -> RegistrySession:
    s = RegistrySession(semantic_index=StubKeywordSemanticIndex(), index_preference="stub")
    s.add_or_replace(
        RegistryEntry(
            id="sort_order",
            kind="sort",
            name="PurchaseOrder",
            nl_description="B2B purchase order",
            source_rule=[],
        )
    )
    s.add_or_replace(
        RegistryEntry(
            id="ent_acme_ltd",
            kind="constant",
            name="Acme Ltd",
            parent_sort_id="sort_order",
            nl_description="Customer Acme",
            source_rule=[],
        )
    )
    return s


def _minimal_line_result(
    *,
    statement: str,
    auth: tuple[SearchHit, ...],
    gaps: tuple[str, ...] = (),
) -> LineSearchGapsResult:
    return LineSearchGapsResult(
        line_index=0,
        statement_nl=statement,
        search_query=statement,
        hits=auth,
        authoritative_hits=auth,
        gap_spans=gaps,
        structured_gaps=(),
        authoritative_min_score=0.11,
        semantic_backend_label="stub_x",
    )


def _ok_payload(cand: str, cited: list[str]) -> str:
    return json.dumps(
        {
            "schema_version": "resolve_v1",
            "registry_resolution_candidate_nl": cand,
            "cited_entry_ids": cited,
            "needs_human_review": False,
            "primary_review_reason": "NONE",
            "confidence_tier": "high",
            "llm_rationale_short": "Substituted canonical names.",
        }
    )


def test_resolve_automated_success() -> None:
    session = _session_acme()
    auth = (SearchHit("ent_acme_ltd", 0.9),)
    line = _minimal_line_result(statement="Acme Ltd placed an order.", auth=auth)
    out = _ok_payload("ent_acme_ltd (Acme Ltd) placed a PurchaseOrder.", ["ent_acme_ltd"])

    def llm(system: str, user: str) -> str:
        _ = (system, user)
        return out

    res = run_automated_resolve(
        line_search_gaps=line, session=session, llm_complete=llm, max_validation_retries=2
    )
    assert res.success
    assert res.registry_resolved_nl == "ent_acme_ltd (Acme Ltd) placed a PurchaseOrder."
    assert res.pre_resolved_nl == res.registry_resolved_nl
    assert res.validation_outcome == "passed"
    assert res.attempts_used == 1


def test_resolve_fails_low_confidence() -> None:
    session = _session_acme()
    auth = (SearchHit("ent_acme_ltd", 0.9),)
    line = _minimal_line_result(statement="Acme Ltd placed an order.", auth=auth)
    bad = json.dumps(
        {
            "schema_version": "resolve_v1",
            "registry_resolution_candidate_nl": "Maybe Acme ordered something.",
            "cited_entry_ids": ["ent_acme_ltd"],
            "needs_human_review": False,
            "primary_review_reason": "NONE",
            "confidence_tier": "medium",
            "llm_rationale_short": "unsure",
        }
    )

    def llm(system: str, user: str) -> str:
        _ = (system, user)
        return bad

    res = run_automated_resolve(line_search_gaps=line, session=session, llm_complete=llm)
    assert not res.success
    assert res.registry_resolved_nl is None
    assert "confidence_tier" in " ".join(res.failure_reasons)


def test_resolve_fails_cites_non_authoritative() -> None:
    session = _session_acme()
    auth = (SearchHit("ent_acme_ltd", 0.9),)
    line = _minimal_line_result(statement="Acme Ltd placed an order.", auth=auth)
    bad = json.loads(_ok_payload("x", ["ent_acme_ltd", "sort_order"]))
    # sort_order was not in authoritative_hits
    bad = json.dumps(bad)

    def llm(system: str, user: str) -> str:
        _ = (system, user)
        return bad

    res = run_automated_resolve(line_search_gaps=line, session=session, llm_complete=llm)
    assert not res.success
    assert any("authoritative" in r.lower() for r in res.failure_reasons)


def test_resolve_retries_then_success() -> None:
    session = _session_acme()
    auth = (SearchHit("ent_acme_ltd", 0.9),)
    line = _minimal_line_result(statement="Acme Ltd placed an order.", auth=auth)
    good = _ok_payload("Acme Ltd (customer) placed a PurchaseOrder.", ["ent_acme_ltd"])
    calls: list[int] = []

    def llm(system: str, user: str) -> str:
        calls.append(1)
        if len(calls) == 1:
            return "{ not json"
        return good

    res = run_automated_resolve(line_search_gaps=line, session=session, llm_complete=llm)
    assert res.success
    assert res.attempts_used == 2
    assert len(res.raw_resolver_json) == 2


def test_structured_gaps_passed_through() -> None:
    session = _session_acme()
    auth = (SearchHit("ent_acme_ltd", 0.9),)
    sg = (StructuredGap(surface="PO-12", kind="constant", arity_hint=None),)
    line = LineSearchGapsResult(
        line_index=0,
        statement_nl="Acme Ltd PO-12.",
        search_query="Acme Ltd PO-12.",
        hits=auth,
        authoritative_hits=auth,
        gap_spans=("PO-12",),
        structured_gaps=sg,
        authoritative_min_score=0.11,
        semantic_backend_label="stub_x",
    )
    captured: list[str] = []

    def llm(system: str, user: str) -> str:
        captured.append(user)
        return _ok_payload("Acme Ltd purchase order PO-12.", ["ent_acme_ltd"])

    res = run_automated_resolve(line_search_gaps=line, session=session, llm_complete=llm)
    assert res.success
    assert "PO-12" in captured[0]
    assert "structured_gaps" in captured[0]
