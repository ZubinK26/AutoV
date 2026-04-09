"""M5 — handoff bundle through search → resolve → populate + trace assembly."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, replace

from registry_stage.line_driver import LineDriverConfig, LineSearchGapsResult, run_search_and_gaps_for_line
from registry_stage.models import DevSessionSnapshot, HandoffBundle, RegistryFile, SCHEMA_VERSION, StructuredGap
from registry_stage.populate_session import populate_provisional_from_gaps
from registry_stage.registry_session import RegistrySession
from registry_stage.resolve_automated import ResolveAutomatedOutcome, run_automated_resolve

LlmComplete = Callable[[str, str], str]


def structured_gaps_to_jsonable(gaps: tuple[StructuredGap, ...]) -> list[dict]:
    out: list[dict] = []
    for g in gaps:
        d = asdict(g)
        d["domain_hints"] = list(d["domain_hints"])
        out.append(d)
    return out


def registry_session_to_registry_file(
    session: RegistrySession,
    *,
    strip_embeddings: bool = True,
) -> RegistryFile:
    """Snapshot active session entries into a ``RegistryFile`` for dev export."""
    from dataclasses import replace

    entries: list = []
    for e in sorted(session.entries.values(), key=lambda x: x.id):
        if strip_embeddings and e.embedding is not None:
            entries.append(replace(e, embedding=None))
        else:
            entries.append(e)
    return RegistryFile(schema_version=SCHEMA_VERSION, entries=entries, entry_edges=[])


def _hits_json(hits: LineSearchGapsResult) -> list[dict]:
    return [{"entry_id": h.entry_id, "score": float(h.score)} for h in hits.hits]


def _auth_json(hits: LineSearchGapsResult) -> list[dict]:
    return [{"entry_id": h.entry_id, "score": float(h.score)} for h in hits.authoritative_hits]


def run_bundle_through_registry(
    bundle: HandoffBundle,
    session: RegistrySession,
    *,
    llm_complete: LlmComplete,
    line_config: LineDriverConfig | None = None,
    max_validation_retries: int = 2,
) -> DevSessionSnapshot:
    """
    For each handoff line: **OUT_OF_SCOPE** → trace only; else M3 → M4 → M5 populate.
    Mutates ``session`` (index rebuilt on each add). Returns a ``DevSessionSnapshot``
    with ``line_traces`` and terminal ``registry`` view.
    """
    cfg = line_config or LineDriverConfig(enable_llm=False)
    if cfg.enable_llm and cfg.llm_complete is None:
        cfg = replace(cfg, llm_complete=llm_complete)

    traces: list[dict] = []
    lines_sorted = sorted(bundle.lines, key=lambda ln: ln.line_index)

    for line in lines_sorted:
        if line.agent3_verdict == "OUT_OF_SCOPE":
            traces.append(
                {
                    "bundle_id": bundle.bundle_id,
                    "line_index": line.line_index,
                    "statement_nl": line.statement_nl,
                    "agent3_verdict": line.agent3_verdict,
                    "skipped_reason": "agent3_verdict_OUT_OF_SCOPE",
                    "hits": [],
                    "authoritative_hits": [],
                    "gap_spans": [],
                    "structured_gaps": [],
                    "expansion_phrases": [],
                    "search_queries_used": [],
                    "authoritative_min_score": None,
                    "semantic_backend_label": session.semantic_backend_label,
                    "pre_resolved_nl": None,
                    "registry_resolution_candidate_nl": None,
                    "registry_resolved_nl": None,
                    "resolve_mode": None,
                    "validation_outcome": "skipped",
                    "failure_reasons": [],
                    "new_entry_ids": [],
                    "raw_resolver_json": [],
                    "attempts_used": 0,
                    "llm_rationale_short": None,
                }
            )
            continue

        sg_result = run_search_and_gaps_for_line(
            session,
            line.line_index,
            line.statement_nl.strip(),
            config=cfg,
        )
        resolve_out = run_automated_resolve(
            line_search_gaps=sg_result,
            session=session,
            llm_complete=llm_complete,
            max_validation_retries=max_validation_retries,
        )
        new_ids = populate_provisional_from_gaps(session, sg_result, bundle_id=bundle.bundle_id)
        traces.append(_trace_for_processed_line(bundle.bundle_id, line.statement_nl, line.agent3_verdict, sg_result, resolve_out, new_ids))

    reg = registry_session_to_registry_file(session)
    return DevSessionSnapshot(registry=reg, bundle=bundle, line_traces=traces, notes="")


def _trace_for_processed_line(
    bundle_id: str,
    statement_nl: str,
    agent3_verdict: str,
    sg: LineSearchGapsResult,
    resolve_out: ResolveAutomatedOutcome,
    new_entry_ids: list[str],
) -> dict:
    return {
        "bundle_id": bundle_id,
        "line_index": sg.line_index,
        "statement_nl": statement_nl,
        "agent3_verdict": agent3_verdict,
        "hits": _hits_json(sg),
        "authoritative_hits": _auth_json(sg),
        "gap_spans": list(sg.gap_spans),
        "structured_gaps": structured_gaps_to_jsonable(sg.structured_gaps),
        "raw_structured_gaps": structured_gaps_to_jsonable(sg.raw_structured_gaps),
        "expansion_phrases": list(sg.expansion_phrases),
        "search_queries_used": list(sg.search_queries_used),
        "authoritative_min_score": float(sg.authoritative_min_score),
        "semantic_backend_label": sg.semantic_backend_label,
        "single_concat_query_truncated": sg.single_concat_query_truncated,
        "pre_resolved_nl": resolve_out.pre_resolved_nl,
        "registry_resolution_candidate_nl": resolve_out.registry_resolution_candidate_nl,
        "registry_resolved_nl": resolve_out.registry_resolved_nl,
        "resolve_mode": resolve_out.resolve_mode,
        "validation_outcome": resolve_out.validation_outcome,
        "failure_reasons": list(resolve_out.failure_reasons),
        "new_entry_ids": list(new_entry_ids),
        "raw_resolver_json": resolve_out.raw_resolver_json,
        "attempts_used": resolve_out.attempts_used,
        "llm_rationale_short": resolve_out.llm_rationale_short,
    }
