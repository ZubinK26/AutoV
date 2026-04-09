"""Per-line search → gap extraction (`development_plan_registry_stage_v1.md` M3)."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, Sequence

from registry_stage.models import StructuredGap
from registry_stage.registry_session import RegistrySession
from registry_stage.semantic_index import SearchHit, entry_embed_text

logger = logging.getLogger(__name__)

_GAP_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "not",
        "but",
        "are",
        "was",
        "has",
        "have",
        "had",
        "this",
        "that",
        "with",
        "from",
        "they",
        "will",
        "into",
        "each",
        "such",
        "than",
        "then",
        "there",
        "when",
        "where",
        "which",
        "while",
        "every",
        "can",
        "may",
    }
)

QueryMode = Literal["multi_query_fuse", "single_concat"]
MaskingPreset = Literal["standard", "aggressive", "conservative"]
LlmComplete = Callable[[str, str], str]


@dataclass(frozen=True)
class LineDriverConfig:
    """Tuning for registry search, LLM expansion/extraction, and masking.

    **M3 eval (production-oriented):** ``single_concat`` + ``conservative``; **BGE+FAISS**
    authoritative cutoff **0.35** (``default_authoritative_min_score``) from Protocol B
    on ``m3_retrieval_eval_*`` — **revisit after more empirical runs** (expansion variance,
    new lines, or registry/index changes can require a different cutoff).

    **Dataclass defaults:** ``query_mode`` / ``masking_preset`` remain ``multi_query_fuse`` /
    ``standard`` for historical test fixtures; wire Protocol A choices at the app boundary
    or pass ``LineDriverConfig(...)`` explicitly — see ``REGISTRY_M3_EVAL_DECISIONS.md``.
    """

    search_top_k: int = 8
    extra_search_context: str | None = None

    authoritative_min_score: float | None = None

    enable_llm: bool = False
    """When True, run Gemini expansion + structured gap extraction (two calls) unless ``llm_complete`` errors."""

    query_mode: QueryMode = "multi_query_fuse"
    masking_preset: MaskingPreset = "standard"

    max_expanded_phrases: int = 8
    max_chars_per_expansion: int = 512
    max_concat_query_chars: int = 6000

    llm_complete: LlmComplete | None = None
    """Inject mock ``(system, user) -> str`` for tests; when ``enable_llm`` and None, uses ``gemini_complete``."""


@dataclass(frozen=True)
class LineSearchGapsResult:
    line_index: int
    statement_nl: str
    search_query: str
    """Baseline query (``statement_nl`` + optional context) — primary query string before expansion."""

    hits: tuple[SearchHit, ...]
    authoritative_hits: tuple[SearchHit, ...]
    gap_spans: tuple[str, ...]
    expansion_phrases: tuple[str, ...] = ()
    structured_gaps: tuple[StructuredGap, ...] = ()
    search_queries_used: tuple[str, ...] = ()
    authoritative_min_score: float = 0.0
    """Effective cutoff used to select ``authoritative_hits`` from ``hits``."""

    semantic_backend_label: str = ""
    raw_expansion_phrases: tuple[str, ...] = ()
    """Model expansion phrases before ``max_phrases`` / ``max_chars_per_expansion`` caps."""

    raw_structured_gaps: tuple[StructuredGap, ...] = ()
    """Structured gaps from the extractor **before** coverage masking (Lane A)."""

    single_concat_query_truncated: bool = False
    """True when ``single_concat`` search string was shortened to ``max_concat_query_chars``."""


def build_search_query(statement_nl: str, extra_search_context: str | None) -> str:
    base = statement_nl.strip()
    if not extra_search_context:
        return base
    extra = extra_search_context.strip()
    if not extra:
        return base
    return f"{base}\n{extra[:2000]}"


def default_authoritative_min_score(session: RegistrySession) -> float:
    """Backend-specific cutoff when ``LineDriverConfig.authoritative_min_score`` is None.

    **BGE+FAISS:** ``0.35`` from Protocol B (retrieval eval rerun); not final — adjust
    when you expand the label set, change prompts/expansion, or see systematic misses.
    """
    label = session.semantic_backend_label
    if label.startswith("stub_"):
        return 0.11
    if label.startswith("bge_faiss"):
        return 0.35
    return 0.2


def extract_placeholder_gaps(statement_nl: str) -> list[str]:
    text = statement_nl.strip()
    if not text:
        return []

    seen: set[str] = set()
    ordered: list[str] = []

    def add(raw: str) -> None:
        w = raw.strip()
        if len(w) < 2:
            return
        key = w.lower()
        if key in _GAP_STOPWORDS:
            return
        if key not in seen:
            seen.add(key)
            ordered.append(w)

    for m in re.finditer(r"\b[A-Z][a-z]+[A-Z][a-zA-Z]*\b", text):
        add(m.group(0))
    for m in re.finditer(r"\b[A-Z][a-z]{2,}\b", text):
        add(m.group(0))

    return ordered


def _authoritative_coverage_blob(session: RegistrySession, hits: Sequence[SearchHit]) -> str:
    parts: list[str] = []
    for h in hits:
        e = session.get(h.entry_id)
        if e is None:
            continue
        parts.append(entry_embed_text(e.name, e.nl_description))
    return "\n".join(parts).lower()


def _authoritative_registry_summary(session: RegistrySession, hits: Sequence[SearchHit]) -> str:
    lines: list[str] = []
    for h in hits:
        e = session.get(h.entry_id)
        if e is None:
            continue
        lines.append(
            f"id={e.id} kind={e.kind} name={e.name!r} nl_description={e.nl_description!r}"
        )
    return "\n".join(lines)


def authoritative_hits_context_nl(session: RegistrySession, hits: Sequence[SearchHit]) -> str:
    """Same lines as M3 gap/resolve LLM context: one line per hit with id, kind, name, description."""
    return _authoritative_registry_summary(session, hits)


def _candidate_covered_standard(candidate: str, coverage_lower: str) -> bool:
    c = candidate.lower().strip()
    if not c:
        return True
    if c in coverage_lower:
        return True
    for sep in ("_", "-", " "):
        if sep in c:
            for piece in re.split(r"[\s_\-]+", c):
                if len(piece) >= 2 and piece.lower() not in _GAP_STOPWORDS and piece.lower() in coverage_lower:
                    return True
    return False


def candidate_covered(
    candidate: str,
    coverage_lower: str,
    preset: MaskingPreset = "standard",
) -> bool:
    """
    Whether a gap surface is already explained by authoritative registry text.

    * **aggressive** — treat as covered on weak token overlap (fewer gaps).
    * **conservative** — require stronger match for single-token entities (more gaps).
    """
    base = _candidate_covered_standard(candidate, coverage_lower)
    if preset == "aggressive":
        if base:
            return True
        c = candidate.lower().strip()
        for w in re.findall(r"[a-z0-9]{3,}", c):
            if w in coverage_lower:
                return True
        return False
    if preset == "conservative":
        if not base:
            return False
        c = candidate.lower().strip()
        if " " not in c and len(c) >= 4:
            return bool(re.search(r"\b" + re.escape(c) + r"\b", coverage_lower))
        return base
    return base


def _fuse_search_hits(groups: list[list[SearchHit]], top_k: int) -> list[SearchHit]:
    scores: dict[str, float] = {}
    for group in groups:
        for h in group:
            scores[h.entry_id] = max(scores.get(h.entry_id, float("-inf")), float(h.score))
    ordered = sorted(scores.items(), key=lambda x: (-x[1], x[0]))[:top_k]
    return [SearchHit(eid, sc) for eid, sc in ordered]


def _dedupe_queries(queries: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for q in queries:
        s = q.strip()
        k = s.lower()
        if k and k not in seen:
            seen.add(k)
            out.append(s)
    return out


def run_search_and_gaps_for_line(
    session: RegistrySession,
    line_index: int,
    statement_nl: str,
    *,
    config: LineDriverConfig | None = None,
) -> LineSearchGapsResult:
    """
    Search the registry, then emit gaps (heuristic ± LLM structured). Authoritative hits mask coverage.

    Callers should **not** invoke this for ``OUT_OF_SCOPE`` lines (orchestration skips formalization).
    """
    cfg = config or LineDriverConfig()
    baseline = build_search_query(statement_nl, cfg.extra_search_context)

    expansion_phrases: tuple[str, ...] = ()
    raw_expansion_phrases: tuple[str, ...] = ()
    llm_fn: LlmComplete | None = None
    single_concat_truncated = False
    if cfg.enable_llm:
        llm_fn = cfg.llm_complete
        if llm_fn is None:
            from registry_stage.llm.gemini_call import gemini_complete

            def _wrap(sys: str, usr: str) -> str:
                return gemini_complete(system_instruction=sys, user_text=usr)

            llm_fn = _wrap

        try:
            from registry_stage.llm.agents import expand_search_phrases_with_raw

            raw_list, capped_list = expand_search_phrases_with_raw(
                statement_nl=statement_nl,
                extra_context=cfg.extra_search_context,
                llm_complete=llm_fn,
                max_phrases=cfg.max_expanded_phrases,
                max_chars=cfg.max_chars_per_expansion,
            )
            raw_expansion_phrases = tuple(raw_list)
            expansion_phrases = tuple(capped_list)
        except Exception as exc:
            logger.warning("LLM search expansion failed: %s", exc)
            expansion_phrases = ()
            raw_expansion_phrases = ()

    if cfg.enable_llm and expansion_phrases:
        if cfg.query_mode == "multi_query_fuse":
            queries = _dedupe_queries([baseline, *list(expansion_phrases)])
            groups = [list(session.search_nl(q, cfg.search_top_k)) for q in queries]
            hits_list = _fuse_search_hits(groups, cfg.search_top_k)
            hits = tuple(hits_list)
            search_queries_used = tuple(queries)
        else:
            body_full = baseline + "\n" + "\n".join(expansion_phrases)
            body = body_full
            if len(body) > cfg.max_concat_query_chars:
                logger.warning(
                    "concatenated query truncated from %s to %s chars",
                    len(body),
                    cfg.max_concat_query_chars,
                )
                body = body[: cfg.max_concat_query_chars]
                single_concat_truncated = True
            hits = tuple(session.search_nl(body, cfg.search_top_k))
            search_queries_used = (body,)
    else:
        hits = tuple(session.search_nl(baseline, cfg.search_top_k))
        search_queries_used = (baseline,)

    min_score = cfg.authoritative_min_score
    if min_score is None:
        min_score = default_authoritative_min_score(session)
    authoritative = tuple(h for h in hits if h.score >= min_score)

    coverage = _authoritative_coverage_blob(session, authoritative)
    # When structured gap extraction runs (live LLM), omit Title-Case heuristic gaps so
    # gap_spans come from the model only — avoids token shards merged alongside full spans.
    # When ``enable_llm`` is False (CI / stub), keep heuristic gaps as the fallback.
    use_llm_structured = cfg.enable_llm and llm_fn is not None
    if use_llm_structured:
        heuristic: list[str] = []
    else:
        heuristic = [
            c
            for c in extract_placeholder_gaps(statement_nl)
            if not candidate_covered(c, coverage, cfg.masking_preset)
        ]

    structured: list[StructuredGap] = []
    if use_llm_structured:
        try:
            from registry_stage.llm.agents import extract_structured_gaps

            summary = _authoritative_registry_summary(session, authoritative)
            structured = extract_structured_gaps(
                statement_nl=statement_nl,
                authoritative_registry_summary=summary,
                llm_complete=llm_fn,
            )
        except Exception as exc:
            logger.warning("LLM structured gap extraction failed: %s", exc)
            structured = []

    raw_structured_gaps = tuple(structured)

    structured_kept = tuple(
        g
        for g in structured
        if not candidate_covered(g.surface, coverage, cfg.masking_preset)
    )
    struct_surfaces = [g.surface for g in structured_kept]

    merged: list[str] = []
    seen_l: set[str] = set()
    for s in struct_surfaces + heuristic:
        k = s.strip()
        if not k:
            continue
        lk = k.lower()
        if lk not in seen_l:
            seen_l.add(lk)
            merged.append(k)
    gaps = tuple(merged)

    logger.info(
        "line_driver line_index=%s hits=%s authoritative=%s gaps=%s expansion=%s queries_used=%s snippet=%r",
        line_index,
        [(h.entry_id, round(float(h.score), 4)) for h in hits],
        [(h.entry_id, round(float(h.score), 4)) for h in authoritative],
        list(gaps),
        list(expansion_phrases),
        [q[:120] + ("…" if len(q) > 120 else "") for q in search_queries_used],
        baseline[:240],
    )

    return LineSearchGapsResult(
        line_index=line_index,
        statement_nl=statement_nl,
        search_query=baseline,
        hits=hits,
        authoritative_hits=authoritative,
        gap_spans=gaps,
        expansion_phrases=expansion_phrases,
        structured_gaps=structured_kept,
        search_queries_used=search_queries_used,
        authoritative_min_score=float(min_score),
        semantic_backend_label=session.semantic_backend_label,
        raw_expansion_phrases=raw_expansion_phrases,
        raw_structured_gaps=raw_structured_gaps,
        single_concat_query_truncated=single_concat_truncated,
    )
