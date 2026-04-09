"""M5 — provisional registry rows from structured gaps (`development_plan_registry_stage_v1.md`)."""

from __future__ import annotations

import re
from collections.abc import Sequence

from registry_stage.line_driver import LineSearchGapsResult
from registry_stage.models import StructuredGap
from registry_stage.registry_session import RegistrySession
from registry_stage.semantic_index import SearchHit


def _bundle_slug(bundle_id: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", bundle_id.strip()).strip("_").lower()
    return (s[:20] or "bundle").rstrip("_")


def _provisional_carrier_sort_id(bundle_slug: str) -> str:
    return f"sort_{bundle_slug}_prov_carrier"


def _existing_name_fold(session: RegistrySession) -> set[str]:
    return {
        e.name.casefold()
        for e in session.entries.values()
        if e.status != "tombstoned" and e.name.strip()
    }


def _authoritative_name_fold(session: RegistrySession, hits: Sequence[SearchHit]) -> set[str]:
    out: set[str] = set()
    for h in hits:
        e = session.get(h.entry_id)
        if e and e.status != "tombstoned" and e.name.strip():
            out.add(e.name.casefold())
    return out


def _should_skip_gap(
    gap: StructuredGap,
    *,
    session: RegistrySession,
    authoritative_hits: Sequence[SearchHit],
) -> bool:
    surf = gap.surface.strip()
    if not surf:
        return True
    cf = surf.casefold()
    if cf in _existing_name_fold(session):
        return True
    if cf in _authoritative_name_fold(session, authoritative_hits):
        return True
    return False


def _ensure_carrier_sort(session: RegistrySession, bundle_slug: str) -> tuple[str, bool]:
    sid = _provisional_carrier_sort_id(bundle_slug)
    if session.get(sid) is not None:
        return sid, False
    from registry_stage.models import RegistryEntry

    session.add_or_replace(
        RegistryEntry(
            id=sid,
            kind="sort",
            name=f"ProvisionalCarrier_{bundle_slug}",
            source_rule=[],
            nl_description="Phase 1 provisional carrier sort for constants lacking a typed parent in-session.",
            status="active",
        )
    )
    return sid, True


def _add_sort(
    session: RegistrySession,
    *,
    entry_id: str,
    surface: str,
    bundle_id: str,
    line_index: int,
    gap: StructuredGap,
) -> None:
    from registry_stage.models import RegistryEntry

    notes = gap.notes.strip()
    nl = (
        f"Provisional sort from bundle {bundle_id!r} line {line_index}: {surface!r}."
        + (f" Notes: {notes}" if notes else "")
    )
    session.add_or_replace(
        RegistryEntry(
            id=entry_id,
            kind="sort",
            name=surface,
            source_rule=[f"provisional:{bundle_id}:{line_index}"],
            nl_description=nl[:4000],
            status="active",
        )
    )


def _add_constant(
    session: RegistrySession,
    *,
    entry_id: str,
    surface: str,
    parent_sort_id: str,
    bundle_id: str,
    line_index: int,
    gap: StructuredGap,
) -> None:
    from registry_stage.models import RegistryEntry

    notes = gap.notes.strip()
    nl = (
        f"Provisional constant from bundle {bundle_id!r} line {line_index}: {surface!r}."
        + (f" Notes: {notes}" if notes else "")
    )
    session.add_or_replace(
        RegistryEntry(
            id=entry_id,
            kind="constant",
            name=surface,
            parent_sort_id=parent_sort_id,
            source_rule=[f"provisional:{bundle_id}:{line_index}"],
            nl_description=nl[:4000],
            status="active",
        )
    )


def _add_function_provisional(
    session: RegistrySession,
    *,
    fn_id: str,
    dom_id: str,
    cod_id: str,
    surface: str,
    bundle_id: str,
    line_index: int,
    gap: StructuredGap,
) -> None:
    from registry_stage.models import RegistryEntry

    notes = gap.notes.strip()
    nl = (
        f"Provisional function from bundle {bundle_id!r} line {line_index}: {surface!r}."
        + (f" Notes: {notes}" if notes else "")
    )
    session.add_or_replace(
        RegistryEntry(
            id=dom_id,
            kind="sort",
            name=f"{surface}_arg_sort",
            source_rule=[f"provisional:{bundle_id}:{line_index}"],
            nl_description=f"Provisional domain placeholder for {surface!r}.",
            status="active",
        )
    )
    session.add_or_replace(
        RegistryEntry(
            id=cod_id,
            kind="sort",
            name=f"{surface}_ret_sort",
            source_rule=[f"provisional:{bundle_id}:{line_index}"],
            nl_description=f"Provisional codomain placeholder for {surface!r}.",
            status="active",
        )
    )
    session.add_or_replace(
        RegistryEntry(
            id=fn_id,
            kind="function",
            name=surface,
            domain_sort_ids=[dom_id],
            codomain_sort_id=cod_id,
            source_rule=[f"provisional:{bundle_id}:{line_index}"],
            nl_description=nl[:4000],
            status="active",
        )
    )


def populate_provisional_from_gaps(
    session: RegistrySession,
    line_search_gaps: LineSearchGapsResult,
    *,
    bundle_id: str,
) -> list[str]:
    """
    Add tentative ``sort_`` / ``ent_`` / ``fn_`` rows for structured gaps not already
    represented by name in the session or authoritative hits. Returns new entry ids
    (all ids created in this call, including placeholder sorts for functions).
    """
    bs = _bundle_slug(bundle_id)
    li = line_search_gaps.line_index
    created: list[str] = []

    for idx, gap in enumerate(line_search_gaps.structured_gaps):
        if _should_skip_gap(gap, session=session, authoritative_hits=line_search_gaps.authoritative_hits):
            continue
        if gap.kind == "sort":
            eid = f"sort_{bs}_l{li}_g{idx}"
            if session.get(eid) is None:
                _add_sort(session, entry_id=eid, surface=gap.surface.strip(), bundle_id=bundle_id, line_index=li, gap=gap)
                created.append(eid)
        elif gap.kind == "constant":
            parent, parent_new = _ensure_carrier_sort(session, bs)
            if parent_new:
                created.append(parent)
            eid = f"ent_{bs}_l{li}_g{idx}"
            if session.get(eid) is None:
                _add_constant(
                    session,
                    entry_id=eid,
                    surface=gap.surface.strip(),
                    parent_sort_id=parent,
                    bundle_id=bundle_id,
                    line_index=li,
                    gap=gap,
                )
                created.append(eid)
        elif gap.kind == "function":
            dom_id = f"sort_{bs}_l{li}_g{idx}_d"
            cod_id = f"sort_{bs}_l{li}_g{idx}_c"
            fn_id = f"fn_{bs}_l{li}_g{idx}"
            if session.get(fn_id) is None:
                _add_function_provisional(
                    session,
                    fn_id=fn_id,
                    dom_id=dom_id,
                    cod_id=cod_id,
                    surface=gap.surface.strip(),
                    bundle_id=bundle_id,
                    line_index=li,
                    gap=gap,
                )
                created.extend([dom_id, cod_id, fn_id])
        else:
            continue

    return created
