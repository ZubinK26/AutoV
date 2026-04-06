"""Semantic search: BGE embeddings + FAISS (spec default) or stub keyword fallback."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, NamedTuple, Protocol, Sequence, runtime_checkable

import numpy as np

if TYPE_CHECKING:
    pass


class SearchHit(NamedTuple):
    entry_id: str
    score: float


def entry_embed_text(name: str, nl_description: str) -> str:
    """Single string to embed per `pipeline_spec.md` (name + NL description)."""
    n = name.strip()
    d = nl_description.strip()
    if n and d:
        return f"{n}\n{d}"
    return n or d


def _tokenize(text: str) -> set[str]:
    return {t for t in re.split(r"[^\w]+", text.lower()) if len(t) > 1}


@runtime_checkable
class SemanticIndex(Protocol):
    @property
    def backend_label(self) -> str: ...

    def rebuild(self, entry_ids: Sequence[str], texts: Sequence[str]) -> None: ...

    def embed_query(self, text: str) -> np.ndarray: ...

    def search(
        self,
        query_embedding: np.ndarray,
        k: int,
        *,
        query_text: str | None = None,
    ) -> list[SearchHit]: ...


class StubKeywordSemanticIndex:
    """
    Keyword overlap fallback when BGE/FAISS is unavailable or for fast tests.
    **Not** spec-default for demos — see `backend_label`.
    """

    __slots__ = ("_rows", "_dim")

    def __init__(self, *, vector_dim: int = 768) -> None:
        self._rows: list[tuple[str, set[str]]] = []
        self._dim = vector_dim

    @property
    def backend_label(self) -> str:
        return "stub_keyword_fallback"

    def rebuild(self, entry_ids: Sequence[str], texts: Sequence[str]) -> None:
        if len(entry_ids) != len(texts):
            raise ValueError("entry_ids and texts must have the same length")
        self._rows = [(eid, _tokenize(txt)) for eid, txt in zip(entry_ids, texts, strict=True)]

    def embed_query(self, text: str) -> np.ndarray:
        # Unused for keyword search; shape matches BGE base (`bge-base-en-v1.5`) for API symmetry.
        return np.zeros((self._dim,), dtype=np.float32)

    def search(
        self,
        query_embedding: np.ndarray,
        k: int,
        *,
        query_text: str | None = None,
    ) -> list[SearchHit]:
        _ = query_embedding
        if k <= 0 or not self._rows:
            return []
        if query_text is None:
            return []
        qset = set(_tokenize(query_text))
        if not qset:
            return []
        scored: list[tuple[str, float]] = []
        for eid, toks in self._rows:
            inter = len(qset & toks)
            if inter == 0:
                continue
            # Reward overlap; slight preference when entry covers more of the query.
            score = float(inter) / float(len(qset))
            scored.append((eid, score))
        scored.sort(key=lambda x: (-x[1], x[0]))
        return [SearchHit(eid, sc) for eid, sc in scored[:k]]


class BgeFaissSemanticIndex:
    """
    Spec-accurate path: `BAAI/bge-base-en-v1.5` + inner-product index on L2-normalized vectors
    (cosine similarity).
    """

    __slots__ = ("_model_name", "_model", "_index", "_id_for_row", "_dim", "_last_vectors")

    def __init__(self, model_name: str = "BAAI/bge-base-en-v1.5") -> None:
        import faiss  # noqa: PLC0415
        from sentence_transformers import SentenceTransformer  # noqa: PLC0415

        self._model_name = model_name
        self._model = SentenceTransformer(model_name)
        self._dim = int(self._model.get_sentence_embedding_dimension())
        self._index = faiss.IndexFlatIP(self._dim)
        self._id_for_row: list[str] = []
        self._last_vectors: np.ndarray | None = None

    @property
    def backend_label(self) -> str:
        return f"bge_faiss:{self._model_name}"

    def rebuild(self, entry_ids: Sequence[str], texts: Sequence[str]) -> None:
        import faiss  # noqa: PLC0415

        if len(entry_ids) != len(texts):
            raise ValueError("entry_ids and texts must have the same length")
        self._id_for_row = list(entry_ids)
        if not entry_ids:
            self._index = faiss.IndexFlatIP(self._dim)
            self._last_vectors = None
            return
        emb = self._model.encode(
            list(texts),
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        vectors = np.asarray(emb, dtype=np.float32)
        self._last_vectors = vectors
        self._index = faiss.IndexFlatIP(self._dim)
        self._index.add(vectors)

    def embed_query(self, text: str) -> np.ndarray:
        v = self._model.encode(
            [text],
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        out = np.asarray(v, dtype=np.float32)[0]
        return out

    def search(
        self,
        query_embedding: np.ndarray,
        k: int,
        *,
        query_text: str | None = None,
    ) -> list[SearchHit]:
        _ = query_text
        if k <= 0 or self._index.ntotal == 0:
            return []
        q = np.asarray(query_embedding, dtype=np.float32).reshape(1, -1)
        scores, idxs = self._index.search(q, min(k, self._index.ntotal))
        hits: list[SearchHit] = []
        for sc, ix in zip(scores[0], idxs[0], strict=True):
            if ix < 0:
                continue
            hits.append(SearchHit(self._id_for_row[ix], float(sc)))
        return hits

    @property
    def last_entry_vectors(self) -> np.ndarray | None:
        """Row-aligned with the last `rebuild` ``entry_ids`` order; optional embedding cache."""
        return self._last_vectors


def create_semantic_index(*, prefer: str = "faiss") -> SemanticIndex:
    """
    `prefer="faiss"`: use BGE + FAISS when imports succeed; else stub with label.
    `prefer="stub"`: always stub.
    """
    if prefer == "stub":
        return StubKeywordSemanticIndex()
    try:
        return BgeFaissSemanticIndex()
    except Exception:
        return StubKeywordSemanticIndex()
