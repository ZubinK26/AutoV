"""M2: in-memory session, semantic search, id/kind validation."""

from __future__ import annotations

import os

import pytest

from registry_stage.models import RegistryEntry
from registry_stage.registry_session import RegistrySession, validate_session_entry
from registry_stage.semantic_index import BgeFaissSemanticIndex, StubKeywordSemanticIndex


def _three_demo_entries() -> list[RegistryEntry]:
    return [
        RegistryEntry(
            id="sort_taxa",
            kind="sort",
            name="Mammalia",
            nl_description="Warm-blooded vertebrates; includes cats, dogs, and bats.",
            source_rule=[],
        ),
        RegistryEntry(
            id="ent_whiskers",
            kind="constant",
            name="whiskers",
            parent_sort_id="sort_taxa",
            nl_description="A domestic cat who drinks milk and naps indoors.",
            source_rule=[],
        ),
        RegistryEntry(
            id="fn_purr",
            kind="function",
            name="purr_loudly",
            domain_sort_ids=["sort_taxa"],
            codomain_sort_id="sort_bool",
            nl_description="True when the animal is purring contentedly.",
            source_rule=[],
        ),
    ]


def test_m2_stub_search_finds_relevant_entry() -> None:
    stub = StubKeywordSemanticIndex()
    session = RegistrySession(semantic_index=stub, index_preference="stub")
    for e in _three_demo_entries():
        session.add_or_replace(e)

    assert session.semantic_backend_label == "stub_keyword_fallback"
    hits = session.search_nl("domestic cat milk indoor nap", k=3)
    assert len(hits) >= 1
    assert hits[0].entry_id == "ent_whiskers"


def test_m2_empty_session_search_returns_empty() -> None:
    session = RegistrySession(
        semantic_index=StubKeywordSemanticIndex(),
        index_preference="stub",
    )
    assert session.search_nl("anything", k=5) == []


def test_m2_wrong_id_prefix_rejected() -> None:
    bad = RegistryEntry(
        id="wrong_prefix",
        kind="sort",
        name="x",
        nl_description="y",
        source_rule=[],
    )
    with pytest.raises(ValueError, match="sort_"):
        validate_session_entry(bad)


def test_m2_tombstone_excluded_from_index_by_default() -> None:
    session = RegistrySession(semantic_index=StubKeywordSemanticIndex(), index_preference="stub")
    visible = _three_demo_entries()[0]
    session.add_or_replace(visible)
    hidden = RegistryEntry(
        id="sort_hidden",
        kind="sort",
        name="HiddenSort",
        nl_description="cats kittens felines",
        status="tombstoned",
        source_rule=[],
    )
    session.add_or_replace(hidden)

    hits = session.search_nl("cats felines kittens", k=5)
    ids = {h.entry_id for h in hits}
    assert "sort_hidden" not in ids


def test_m2_search_vector_api_stub() -> None:
    session = RegistrySession(semantic_index=StubKeywordSemanticIndex(), index_preference="stub")
    for e in _three_demo_entries():
        session.add_or_replace(e)
    q = session.embed_query("cat milk")
    out = session.search(q, k=2, query_text="cat milk")
    assert len(out) >= 1


@pytest.mark.skipif(
    bool(os.environ.get("REGISTRY_M2_SKIP_HEAVY")),
    reason="REGISTRY_M2_SKIP_HEAVY=1 skips BGE+FAISS (slow / may download model on first run).",
)
def test_m2_bge_faiss_neighbors() -> None:
    """Validates spec-default retrieval; requires full `requirements.txt` (PyTorch + model cache)."""
    pytest.importorskip("faiss")
    pytest.importorskip("sentence_transformers")
    index = BgeFaissSemanticIndex()
    session = RegistrySession(semantic_index=index, index_preference="faiss")
    for e in _three_demo_entries():
        session.add_or_replace(e)

    assert session.semantic_backend_label.startswith("bge_faiss:")
    hits = session.search_nl("house cat that drinks milk", k=2)
    assert len(hits) >= 1
    top_ids = [h.entry_id for h in hits]
    assert "ent_whiskers" in top_ids
    cat = session.get("ent_whiskers")
    assert cat is not None
    assert cat.embedding is not None
    assert len(cat.embedding) == 768  # BAAI/bge-base-en-v1.5
