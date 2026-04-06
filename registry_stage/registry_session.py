"""In-memory registry session with semantic index (`development_plan_registry_stage_v1.md` M2)."""

from __future__ import annotations

from typing import Iterable, Sequence

import numpy as np

from registry_stage.models import ENTRY_KINDS, ENTRY_STATUS, RegistryEntry
from registry_stage.semantic_index import (
    BgeFaissSemanticIndex,
    SemanticIndex,
    SearchHit,
    StubKeywordSemanticIndex,
    create_semantic_index,
    entry_embed_text,
)


def _validate_id_for_kind(entry_id: str, kind: str) -> None:
    if kind == "sort":
        if not entry_id.startswith("sort_"):
            raise ValueError(f'sort entry id must start with "sort_": {entry_id!r}')
    elif kind == "constant":
        if not entry_id.startswith("ent_"):
            raise ValueError(f'constant entry id must start with "ent_": {entry_id!r}')
    elif kind == "function":
        if not entry_id.startswith("fn_"):
            raise ValueError(f'function entry id must start with "fn_": {entry_id!r}')
    else:
        raise ValueError(f"unknown kind {kind!r}")


def validate_session_entry(entry: RegistryEntry) -> None:
    """Kind, status, id prefix, and required kind-specific fields (session / persistence v1)."""
    if entry.kind not in ENTRY_KINDS:
        raise ValueError(f"kind must be one of {sorted(ENTRY_KINDS)}, got {entry.kind!r}")
    if entry.status not in ENTRY_STATUS:
        raise ValueError(f"status must be one of {sorted(ENTRY_STATUS)}, got {entry.status!r}")
    if not isinstance(entry.id, str) or not entry.id:
        raise ValueError("entry.id must be a non-empty string")
    if not isinstance(entry.name, str):
        raise ValueError("entry.name must be a string")
    if not isinstance(entry.source_rule, list) or not all(isinstance(x, str) for x in entry.source_rule):
        raise ValueError("source_rule must be a list of strings")
    if not isinstance(entry.nl_description, str):
        raise ValueError("nl_description must be a string")

    _validate_id_for_kind(entry.id, entry.kind)

    if entry.members is not None:
        if not isinstance(entry.members, list) or not all(isinstance(x, str) for x in entry.members):
            raise ValueError("members must be a list of strings or None")

    if entry.parent_sort_id is not None and not isinstance(entry.parent_sort_id, str):
        raise ValueError("parent_sort_id must be a string or None")
    if entry.domain_sort_ids is not None:
        if not isinstance(entry.domain_sort_ids, list) or not all(isinstance(x, str) for x in entry.domain_sort_ids):
            raise ValueError("domain_sort_ids must be a list of strings or None")
    if entry.codomain_sort_id is not None and not isinstance(entry.codomain_sort_id, str):
        raise ValueError("codomain_sort_id must be a string or None")

    if entry.kind == "constant":
        if not entry.parent_sort_id:
            raise ValueError("constant entries require parent_sort_id")
    if entry.kind == "function":
        if not entry.domain_sort_ids or len(entry.domain_sort_ids) == 0:
            raise ValueError("function entries require non-empty domain_sort_ids")
        if not entry.codomain_sort_id:
            raise ValueError("function entries require codomain_sort_id")


class RegistrySession:
    """
    CRUD over ``RegistryEntry`` values plus embedding cache and a pluggable semantic index.
    Tombstoned entries are kept in the session but excluded from the search index by default.
    """

    __slots__ = ("_entries", "_index", "_index_tombstoned")

    def __init__(
        self,
        *,
        semantic_index: SemanticIndex | None = None,
        index_preference: str = "faiss",
        include_tombstoned_in_index: bool = False,
    ) -> None:
        self._entries: dict[str, RegistryEntry] = {}
        self._index: SemanticIndex = semantic_index or create_semantic_index(prefer=index_preference)
        self._index_tombstoned = include_tombstoned_in_index

    @property
    def semantic_backend_label(self) -> str:
        return self._index.backend_label

    @property
    def entries(self) -> dict[str, RegistryEntry]:
        return dict(self._entries)

    def get(self, entry_id: str) -> RegistryEntry | None:
        return self._entries.get(entry_id)

    def add_or_replace(self, entry: RegistryEntry) -> None:
        validate_session_entry(entry)
        self._entries[entry.id] = entry
        self._rebuild_index()

    def remove(self, entry_id: str) -> bool:
        if entry_id not in self._entries:
            return False
        del self._entries[entry_id]
        self._rebuild_index()
        return True

    def _iter_indexed_entries(self) -> Iterable[RegistryEntry]:
        for e in self._entries.values():
            if e.status == "tombstoned" and not self._index_tombstoned:
                continue
            yield e

    def _rebuild_index(self) -> None:
        rows = list(self._iter_indexed_entries())
        ids = [e.id for e in rows]
        texts = [entry_embed_text(e.name, e.nl_description) for e in rows]
        self._index.rebuild(ids, texts)
        self._sync_embeddings_from_index(rows)

    def _sync_embeddings_from_index(self, rows: list[RegistryEntry]) -> None:
        """After rebuild: cache BGE vectors on entries; stub clears embeddings."""
        if isinstance(self._index, StubKeywordSemanticIndex):
            for e in rows:
                e.embedding = None
            return
        if isinstance(self._index, BgeFaissSemanticIndex):
            lv = self._index.last_entry_vectors
            if lv is not None and len(rows) == len(lv):
                for e, row in zip(rows, lv, strict=True):
                    e.embedding = np.asarray(row, dtype=np.float32).tolist()
            return
        for e in rows:
            e.embedding = None

    def embed_query(self, text: str) -> np.ndarray:
        return self._index.embed_query(text)

    def search(
        self,
        query_embedding: np.ndarray,
        k: int,
        *,
        query_text: str | None = None,
    ) -> list[SearchHit]:
        if not self._entries:
            return []
        return self._index.search(query_embedding, k, query_text=query_text)

    def search_nl(self, query: str, k: int) -> list[SearchHit]:
        """Embed ``query`` (BGE) or use keyword path (stub), then return top-``k`` hits."""
        if not self._entries:
            return []
        qv = self._index.embed_query(query)
        return self._index.search(qv, k, query_text=query)

    @classmethod
    def from_entries(
        cls,
        entries: Sequence[RegistryEntry],
        *,
        semantic_index: SemanticIndex | None = None,
        index_preference: str = "faiss",
        include_tombstoned_in_index: bool = False,
    ) -> RegistrySession:
        session = cls(
            semantic_index=semantic_index,
            index_preference=index_preference,
            include_tombstoned_in_index=include_tombstoned_in_index,
        )
        for e in entries:
            validate_session_entry(e)
            session._entries[e.id] = e
        session._rebuild_index()
        return session
