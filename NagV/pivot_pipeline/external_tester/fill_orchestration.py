"""v3 fill orchestration: chunked phase 1, phase 2 derive, merge, golden."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from pivot_pipeline.external_tester.api_retry import call_with_api_retries
from pivot_pipeline.external_tester.completeness import check_completeness
from pivot_pipeline.external_tester.fill_batches import (
    catalog_excerpt_for_names,
    plan_grounded_batches,
)
from pivot_pipeline.external_tester.llm import external_llm_complete
from pivot_pipeline.external_tester.rule_glossary import build_rule_glossary
from pivot_pipeline.external_tester.schemas import (
    ExternalSourceEnvelope,
    ExternalWorldFillBatchV1,
    ExternalWorldFillV1,
    VariableAssignment,
)
from pivot_pipeline.external_tester.trace import append_trace
from pivot_pipeline.external_tester.variable_tiers import Tier, tiers_for_meta
from pivot_pipeline.ir import MetaScheme
from pivot_pipeline.json_util import parse_json_object
from pivot_pipeline.paths import PROMPTS_DIR


def _numbered_source_block(source: ExternalSourceEnvelope) -> str:
    return "\n".join(f"L{i}: {text}" for i, text in enumerate(source.lines, start=1))


def _phase1_prompt() -> str:
    return (PROMPTS_DIR / "external_world_fill_phase1.md").read_text(encoding="utf-8")


def _phase2_prompt() -> str:
    return (PROMPTS_DIR / "external_world_fill_phase2_derive.md").read_text(encoding="utf-8")


def _golden_prompt() -> str:
    return (PROMPTS_DIR / "external_world_fill_golden.md").read_text(encoding="utf-8")


def _parse_batch_assignments(
    raw: str,
    *,
    expected: list[str],
    batch_id: str,
    work_dir: Path | None = None,
) -> list[VariableAssignment]:
    obj = parse_json_object(raw)
    batch = ExternalWorldFillBatchV1.model_validate(
        {**obj, "batch_id": obj.get("batch_id", batch_id), "variables_requested": expected}
    )
    exp = set(expected)
    filtered: list[VariableAssignment] = []
    extra_vars: list[str] = []
    for a in batch.assignments:
        if a.variable in exp:
            filtered.append(a)
        else:
            extra_vars.append(a.variable)
    if work_dir is not None and extra_vars:
        append_trace(
            work_dir,
            {"kind": "batch_extra_dropped", "batch_id": batch_id, "variables": extra_vars},
        )
    missing = exp - {a.variable for a in filtered}
    if missing:
        raise ValueError(f"batch {batch_id}: missing {sorted(missing)!r}")
    if len(filtered) != len(exp):
        raise ValueError(f"batch {batch_id}: expected {len(exp)} assignments, got {len(filtered)}")
    return filtered


def _assignments_by_var(assignments: list[VariableAssignment]) -> dict[str, VariableAssignment]:
    return {a.variable: a for a in assignments}


def _load_assignments_file(path: Path) -> dict[str, VariableAssignment]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, VariableAssignment] = {}
    for x in data.get("assignments", []):
        a = VariableAssignment.model_validate(x)
        out[a.variable] = a
    return out


def _grounded_list(p1_by: dict[str, VariableAssignment], tiers: dict[str, Tier]) -> list[VariableAssignment]:
    return [p1_by[k] for k in sorted(p1_by) if tiers.get(k) == "grounded" and k in p1_by]


def _derived_list(p2_by: dict[str, VariableAssignment], tiers: dict[str, Tier]) -> list[VariableAssignment]:
    return [p2_by[k] for k in sorted(p2_by) if tiers.get(k) == "derived" and k in p2_by]


def merge_assignments(
    *parts: list[VariableAssignment],
    sorts: dict[str, str],
) -> list[VariableAssignment]:
    merged: dict[str, VariableAssignment] = {}
    for part in parts:
        merged.update(_assignments_by_var(part))
    missing = sorted(set(sorts.keys()) - set(merged.keys()))
    if missing:
        raise ValueError(f"merge missing variables: {', '.join(missing)}")
    return [merged[k] for k in sorted(sorts.keys())]


def run_phase1_batch(
    *,
    work_dir: Path,
    source: ExternalSourceEnvelope,
    meta: MetaScheme,
    batch_names: list[str],
    batch_id: str,
    tiers: dict[str, Tier],
    feedback: str = "",
) -> list[VariableAssignment]:
    sorts = dict(meta.variable_sorts)
    user_parts = [
        _phase1_prompt(),
        "",
        catalog_excerpt_for_names(batch_names, sorts, tiers=tiers),
        "",
        f"### batch_id\n`{batch_id}`",
        "",
        "### Numbered source document",
        _numbered_source_block(source),
    ]
    if feedback:
        user_parts.extend(["", "### Fix these issues", feedback])
    user_parts.append("")
    prompt = "\n".join(user_parts)

    raw = call_with_api_retries(
        lambda: external_llm_complete(prompt, stage="fill"),
        label=f"external_fill_p1_{batch_id}",
    )
    (work_dir / f"external_world_fill_batch_{batch_id}_raw.txt").write_text(raw, encoding="utf-8")
    append_trace(work_dir, {"kind": "fill_batch", "batch_id": batch_id, "n": len(batch_names)})
    return _parse_batch_assignments(
        raw, expected=batch_names, batch_id=batch_id, work_dir=work_dir
    )


def run_phase1_chunked(
    *,
    work_dir: Path,
    source: ExternalSourceEnvelope,
    meta: MetaScheme,
    tiers: dict[str, Tier],
    only_variables: list[str] | None = None,
    feedback: str = "",
) -> list[VariableAssignment]:
    batches = plan_grounded_batches(tiers=tiers, sorts=dict(meta.variable_sorts))
    all_assignments: list[VariableAssignment] = []
    batch_feedback = feedback
    ran_any = False
    for idx, names in enumerate(batches):
        if only_variables is not None:
            names = [n for n in names if n in only_variables]
            if not names:
                continue
        ran_any = True
        bid = f"p1_{idx:02d}"
        all_assignments.extend(
            run_phase1_batch(
                work_dir=work_dir,
                source=source,
                meta=meta,
                batch_names=names,
                batch_id=bid,
                tiers=tiers,
                feedback=batch_feedback,
            )
        )
        batch_feedback = ""
    if only_variables is not None and not ran_any:
        raise ValueError(f"phase1 refill: none of {only_variables!r} are grounded batch variables")
    return all_assignments


def run_phase2_derive(
    *,
    work_dir: Path,
    meta: MetaScheme,
    rules: list[dict[str, Any]],
    phase1: list[VariableAssignment],
    tiers: dict[str, Tier],
    only_variables: list[str] | None = None,
    work_dir_path: Path | None = None,
    feedback: str = "",
) -> list[VariableAssignment]:
    derived_names = sorted(n for n, t in tiers.items() if t == "derived")
    if only_variables is not None:
        derived_names = [n for n in derived_names if n in only_variables]
    if not derived_names:
        return []

    glossary = build_rule_glossary(rules, work_dir=work_dir_path or work_dir)
    p1_json = json.dumps(
        [a.model_dump(mode="json") for a in phase1 if tiers.get(a.variable) == "grounded"],
        indent=2,
        ensure_ascii=False,
    )
    user_parts = [
        _phase2_prompt(),
        "",
        catalog_excerpt_for_names(derived_names, dict(meta.variable_sorts), tiers=tiers),
        "",
        "### Phase 1 grounded assignments",
        p1_json,
        "",
        "### Rule glossary",
        glossary,
    ]
    if feedback:
        user_parts.extend(["", "### Fix these issues", feedback])
    user_parts.append("")
    prompt = "\n".join(user_parts)

    raw = call_with_api_retries(
        lambda: external_llm_complete(prompt, stage="fill"),
        label="external_fill_p2",
    )
    (work_dir / "external_world_fill_phase2_raw.txt").write_text(raw, encoding="utf-8")
    append_trace(work_dir, {"kind": "fill_phase2", "n": len(derived_names)})
    obj = parse_json_object(raw)
    rows = obj.get("assignments") or obj
    if isinstance(rows, dict):
        rows = rows.get("assignments")
    assignments = [VariableAssignment.model_validate(x) for x in rows]
    got = {a.variable for a in assignments}
    exp = set(derived_names)
    if got != exp:
        raise ValueError(f"phase2 missing {sorted(exp - got)!r} extra {sorted(got - exp)!r}")
    for a in assignments:
        if a.status == "not_found":
            raise ValueError(f"phase2 {a.variable}: not_found not allowed")
    return assignments


def _ensure_all_grounded(p1_by: dict[str, VariableAssignment], tiers: dict[str, Tier]) -> None:
    missing = sorted(n for n, t in tiers.items() if t == "grounded" and n not in p1_by)
    if missing:
        raise ValueError(f"phase1 incomplete, missing grounded: {', '.join(missing)}")


def _ensure_all_derived(p2_by: dict[str, VariableAssignment], tiers: dict[str, Tier]) -> None:
    missing = sorted(n for n, t in tiers.items() if t == "derived" and n not in p2_by)
    if missing:
        raise ValueError(f"phase2 incomplete, missing derived: {', '.join(missing)}")


def run_golden_sat(
    *,
    work_dir: Path,
    assignments: list[VariableAssignment],
    template_kind: str,
) -> dict[str, Any]:
    summary = json.dumps(
        [a.model_dump(mode="json") for a in assignments],
        indent=2,
        ensure_ascii=False,
    )
    prompt = (
        f"{_golden_prompt()}\n\n---\n\n### template_kind\n`{template_kind}`\n\n"
        f"### Merged assignments\n{summary}\n"
    )
    raw = call_with_api_retries(
        lambda: external_llm_complete(prompt, stage="fill"),
        label="external_fill_golden",
    )
    (work_dir / "external_world_fill_golden_raw.txt").write_text(raw, encoding="utf-8")
    obj = parse_json_object(raw)
    golden = obj.get("golden") or obj
    return golden if isinstance(golden, dict) else {"sat": bool(golden.get("sat"))}


def run_fill_orchestration_v3(
    *,
    work_dir: Path,
    source: ExternalSourceEnvelope,
    meta: MetaScheme,
    rules: list[dict[str, Any]],
    instance_id: str,
    template_kind: str = "scenario",
    review_feedback: str | None = None,
    refill_variables: list[str] | None = None,
) -> ExternalWorldFillV1:
    """Full v3 fill: phase1 (+ optional targeted patch) → phase2 → golden → merge."""
    tiers = tiers_for_meta(meta, rules)
    sorts = dict(meta.variable_sorts)
    feedback = review_feedback or ""
    grounded_count = sum(1 for t in tiers.values() if t == "grounded")

    if refill_variables:
        refill_set = set(refill_variables)
        p1_by = _load_assignments_file(work_dir / "external_world_fill_phase1.json")
        p2_by = _load_assignments_file(work_dir / "external_world_fill_phase2.json")
        p1_names = [n for n in refill_set if tiers.get(n) == "grounded"]
        p2_names = [n for n in refill_set if tiers.get(n) == "derived"]
        touched_grounded = bool(p1_names)

        append_trace(
            work_dir,
            {
                "kind": "fill_refill_patch",
                "grounded": p1_names,
                "derived": p2_names,
                "touched_grounded": touched_grounded,
            },
        )

        if p1_names:
            new_p1 = run_phase1_chunked(
                work_dir=work_dir,
                source=source,
                meta=meta,
                tiers=tiers,
                only_variables=p1_names,
                feedback=feedback,
            )
            p1_by.update(_assignments_by_var(new_p1))

        if len(p1_by) < grounded_count:
            raise ValueError(
                "targeted refill: prior phase1 snapshot missing; run full fill first "
                f"(have {len(p1_by)} grounded, need {grounded_count})"
            )
        _ensure_all_grounded(p1_by, tiers)
        phase1 = _grounded_list(p1_by, tiers)

        # Any grounded change can affect derivations — rerun full phase 2 unless only patching into full p2.
        if touched_grounded or len(p2_by) < sum(1 for t in tiers.values() if t == "derived"):
            phase2_list = run_phase2_derive(
                work_dir=work_dir,
                meta=meta,
                rules=rules,
                phase1=phase1,
                tiers=tiers,
                only_variables=None,
                feedback=feedback,
            )
            p2_by = _assignments_by_var(phase2_list)
        elif p2_names:
            patch = run_phase2_derive(
                work_dir=work_dir,
                meta=meta,
                rules=rules,
                phase1=phase1,
                tiers=tiers,
                only_variables=p2_names,
                feedback=feedback,
            )
            p2_by.update(_assignments_by_var(patch))
        _ensure_all_derived(p2_by, tiers)
        phase2 = _derived_list(p2_by, tiers)
    else:
        phase1 = run_phase1_chunked(
            work_dir=work_dir,
            source=source,
            meta=meta,
            tiers=tiers,
            feedback=feedback,
        )
        phase2 = run_phase2_derive(
            work_dir=work_dir,
            meta=meta,
            rules=rules,
            phase1=phase1,
            tiers=tiers,
            feedback="",
        )

    (work_dir / "external_world_fill_phase1.json").write_text(
        json.dumps(
            {"schema_version": "1", "assignments": [a.model_dump(mode="json") for a in phase1]},
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (work_dir / "external_world_fill_phase2.json").write_text(
        json.dumps(
            {"schema_version": "1", "assignments": [a.model_dump(mode="json") for a in phase2]},
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    merged = merge_assignments(phase1, phase2, sorts=sorts)
    golden = run_golden_sat(work_dir=work_dir, assignments=merged, template_kind=template_kind)
    fill = ExternalWorldFillV1(
        instance_id=instance_id,
        template_kind=template_kind,  # type: ignore[arg-type]
        query=None,
        golden=golden,
        assignments=merged,
    )
    errs = check_completeness(fill, meta)
    if errs:
        raise ValueError("; ".join(errs))
    (work_dir / "external_world_fill.json").write_text(
        json.dumps(fill.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return fill


def run_fill_with_orchestration(
    *,
    work_dir: Path,
    source: ExternalSourceEnvelope,
    meta: MetaScheme,
    rules: list[dict[str, Any]],
    rule_ids: list[str],
    instance_id: str,
    template_kind: str = "scenario",
    query_rule_id: str | None = None,
    review_feedback: str | None = None,
    refill_variables: list[str] | None = None,
    orchestration: str | None = None,
) -> ExternalWorldFillV1:
    _ = rule_ids, query_rule_id, orchestration
    if template_kind == "decision_query":
        raise ValueError(
            "decision_query fill removed in v4; use policy case pipeline (full-policy query)"
        )
    return run_fill_orchestration_v3(
        work_dir=work_dir,
        source=source,
        meta=meta,
        rules=rules,
        instance_id=instance_id,
        template_kind=template_kind,
        review_feedback=review_feedback,
        refill_variables=refill_variables,
    )


__all__ = [
    "merge_assignments",
    "run_fill_orchestration_v3",
    "run_fill_with_orchestration",
    "run_phase1_chunked",
    "run_phase2_derive",
]
