"""M5 — populate + per-line traces + bundle orchestration."""

from __future__ import annotations

import json

from registry_stage.bundle_workflow import (
    registry_session_to_registry_file,
    run_bundle_through_registry,
    structured_gaps_to_jsonable,
)
from registry_stage.line_driver import LineDriverConfig
from registry_stage.models import HandoffBundle, HandoffLine, SCHEMA_VERSION, StructuredGap
from registry_stage.populate_session import populate_provisional_from_gaps
from registry_stage.registry_session import RegistrySession
from registry_stage.semantic_index import SearchHit, StubKeywordSemanticIndex


def _ok_resolve(statement: str) -> str:
    return json.dumps(
        {
            "schema_version": "resolve_v1",
            "registry_resolution_candidate_nl": f"{statement} (resolved)",
            "cited_entry_ids": [],
            "needs_human_review": False,
            "primary_review_reason": "NONE",
            "confidence_tier": "high",
            "llm_rationale_short": "ok",
        }
    )


def test_structured_gaps_to_jsonable_roundtrip() -> None:
    g = StructuredGap(surface="X", kind="sort", arity_hint=2, domain_hints=("a",), notes="n")
    out = structured_gaps_to_jsonable((g,))
    assert out[0]["surface"] == "X"
    assert out[0]["domain_hints"] == ["a"]


def test_populate_provisional_creates_sort() -> None:
    from registry_stage.line_driver import LineSearchGapsResult

    session = RegistrySession(semantic_index=StubKeywordSemanticIndex(), index_preference="stub")
    sg = (
        StructuredGap(surface="ZetaSort", kind="sort", notes="n"),
        StructuredGap(surface="ignored_dup", kind="sort"),
    )
    res = LineSearchGapsResult(
        line_index=3,
        statement_nl="s",
        search_query="s",
        hits=(),
        authoritative_hits=(),
        gap_spans=("ZetaSort", "ignored_dup"),
        structured_gaps=sg,
        authoritative_min_score=0.1,
        semantic_backend_label="stub",
    )
    created = populate_provisional_from_gaps(session, res, bundle_id="bu_x")
    assert created
    names = [e.name for e in session.entries.values()]
    assert "ZetaSort" in names
    # second gap same iteration would duplicate name if not skipped — different idx so different id
    assert "ignored_dup" in names


def test_run_bundle_skips_out_of_scope_and_traces_pass() -> None:
    bundle = HandoffBundle(
        schema_version=SCHEMA_VERSION,
        bundle_id="m5_test_bundle",
        user_original_input="u",
        lines=[
            HandoffLine(0, "Only line for registry.", "PASS"),
            HandoffLine(1, "Out of scope line.", "OUT_OF_SCOPE"),
        ],
    )
    session = RegistrySession(semantic_index=StubKeywordSemanticIndex(), index_preference="stub")

    responses = iter(
        [
            '{"phrases": []}',
            json.dumps(
                {
                    "gaps": [
                        {
                            "surface": "WidgetKind",
                            "kind": "sort",
                            "arity_hint": None,
                            "domain_hints": [],
                            "notes": "",
                        }
                    ]
                }
            ),
            _ok_resolve("Only line for registry."),
        ]
    )

    def llm(_s: str, _u: str) -> str:
        return next(responses)

    snap = run_bundle_through_registry(
        bundle,
        session,
        llm_complete=llm,
        line_config=LineDriverConfig(
            enable_llm=True,
            query_mode="single_concat",
            masking_preset="conservative",
            llm_complete=llm,
        ),
    )

    assert len(snap.line_traces) == 2
    assert snap.line_traces[0]["validation_outcome"] == "passed"
    assert snap.line_traces[0]["registry_resolved_nl"] == "Only line for registry. (resolved)"
    assert snap.line_traces[0]["new_entry_ids"]
    assert snap.line_traces[1]["skipped_reason"] == "agent3_verdict_OUT_OF_SCOPE"
    assert snap.line_traces[1]["validation_outcome"] == "skipped"

    reg = snap.registry
    assert reg is not None
    assert any(e.name == "WidgetKind" for e in reg.entries)


def test_registry_session_to_file_strips_embeddings() -> None:
    from registry_stage.models import RegistryEntry

    session = RegistrySession(semantic_index=StubKeywordSemanticIndex(), index_preference="stub")
    session.add_or_replace(
        RegistryEntry(
            id="sort_x",
            kind="sort",
            name="X",
            nl_description="d",
            source_rule=[],
            embedding=[0.1, 0.2],
        )
    )
    rf = registry_session_to_registry_file(session, strip_embeddings=True)
    assert rf.entries[0].embedding is None
