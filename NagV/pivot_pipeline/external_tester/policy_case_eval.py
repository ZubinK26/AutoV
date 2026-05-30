"""Post-provenance evaluation: sufficiency gate + tier 1/2/3 + artifacts."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from pivot_pipeline.external_tester.case_narrative_agent import write_case_narrative
from pivot_pipeline.external_tester.explainer import build_explanation, write_explanation
from pivot_pipeline.external_tester.pathway_sufficiency import (
    PathwaySufficiencyReportV1,
    assess_pathway_sufficiency,
    compute_pathway_requirements,
)
from pivot_pipeline.external_tester.policy_query import (
    PolicyQueryResultV1,
    build_query_addendum,
    lenient_query_enabled,
    run_lenient_policy_query,
    run_tier1_policy_query,
)
from pivot_pipeline.external_tester.schemas import (
    ExternalSourceEnvelope,
    PolicyCaseReportV1,
    PolicyCaseWorldV1,
    PolicyQueryResultV1,
)
from pivot_pipeline.external_tester.tier_programmatic import run_tier2_programmatic
from pivot_pipeline.external_tester.tier_speculative import run_tier3_speculative, tier3_enabled
from pivot_pipeline.external_tester.variable_tiers import Tier
from pivot_pipeline.external_tester.world_builder import stated_pin_contradicts_policy
from pivot_pipeline.ir import MetaScheme


class PolicyCaseTierAddendumV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1"] = "1"
    pathway_id: str = "compiled_default"
    tier1_complete: bool = False
    tier1: PolicyQueryResultV1 | None = None
    tier2: dict[str, Any] | None = None
    tier3: dict[str, Any] | None = None
    lenient: PolicyQueryResultV1 | None = None
    summary: str = ""


def tiers_on_block_enabled(explicit: bool | None = None) -> bool:
    if explicit is not None:
        return explicit
    raw = os.getenv("PIVOT_CASE_RUN_TIERS_ON_BLOCK", "on").strip().lower()
    return raw not in ("off", "false", "0", "no")


def run_policy_evaluation(
    *,
    work_dir: Path,
    meta: MetaScheme,
    world: PolicyCaseWorldV1,
    rules: list[dict[str, Any]],
    tiers: dict[str, Tier],
    instance_id: str,
    pathway_id: str = "compiled_default",
    provenance_verdict: str,
    link_warnings: list[str],
    lenient_query: bool | None = None,
    skip_tier2: bool = False,
    skip_tier3: bool = False,
    skip_narrative: bool = False,
    source: ExternalSourceEnvelope | None = None,
    print_fn: Any = print,
) -> dict[str, Any]:
    """
    Sufficiency → tier-1 (if complete) → tier-2/3 → narrative → report fields.
    """
    requirements = compute_pathway_requirements(meta, rules, pathway_id=pathway_id)
    req_path = work_dir / "policy_case_pathway_requirements.json"
    req_path.write_text(
        json.dumps(requirements.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    provenance_ok = {s.variable for s in world.stated}
    sufficiency = assess_pathway_sufficiency(
        world, requirements, provenance_ok_vars=provenance_ok
    )
    suff_path = work_dir / "policy_case_sufficiency.json"
    suff_path.write_text(
        json.dumps(sufficiency.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print_fn(
        f"[policy_case] sufficiency: tier1_complete={sufficiency.tier1_complete} "
        f"missing={len(sufficiency.missing)}",
    )

    tier1_query: PolicyQueryResultV1 | None = None
    complete: dict[str, int | bool] = {}
    explanation_path: str | None = None

    if sufficiency.tier1_complete:
        print_fn("[policy_case] tier-1 strict query (stated + derived eval)")
        if stated_pin_contradicts_policy(meta, list(world.stated)):
            tier1_query = PolicyQueryResultV1(
                query_mode="strict",
                z3_status="unsat",
                compatibility="incompatible",
                defaulted_variables=[],
                default_policy="stated_pin_unsat_v1",
            )
        else:
            try:
                tier1_query, complete = run_tier1_policy_query(meta, world, rules, tiers)
            except ValueError as e:
                return {
                    "blocked": True,
                    "outcome": "blocked_query",
                    "error": str(e),
                    "sufficiency": sufficiency,
                    "pathway_id": pathway_id,
                }
        (work_dir / "policy_case_query.json").write_text(
            json.dumps(tier1_query.model_dump(mode="json"), indent=2, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )
        if tier1_query.compatibility in ("compatible", "incompatible"):
            explanation = build_explanation(
                work_dir=work_dir,
                meta=meta,
                world=world,
                query=tier1_query,
                complete_world=complete,
            )
            expl_path = write_explanation(work_dir, explanation)
            explanation_path = str(expl_path.resolve())
        print_fn(
            f"[policy_case] tier-1: compatibility={tier1_query.compatibility} "
            f"z3={tier1_query.z3_status}",
        )

    tier2_report = None
    tier2_world = world
    if not skip_tier2 and (sufficiency.tier1_complete or tiers_on_block_enabled()):
        print_fn("[policy_case] tier-2 programmatic completion")
        tier2_report, tier2_world = run_tier2_programmatic(
            world=world,
            meta=meta,
            rules=rules,
            tiers=tiers,
            sufficiency=sufficiency,
        )
        (work_dir / "policy_case_programmatic_fill.json").write_text(
            json.dumps(tier2_report.model_dump(mode="json"), indent=2, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )

    tier3_report = None
    if not skip_tier3 and tier3_enabled() and (sufficiency.tier1_complete or tiers_on_block_enabled()):
        tier3_source = source
        if tier3_source is None:
            from pivot_pipeline.external_tester.schemas import load_source_path

            src_path = work_dir / "policy_case_source.json"
            if src_path.is_file():
                tier3_source = load_source_path(src_path)
        if tier3_source is not None:
            print_fn("[policy_case] tier-3 speculative fill")
            tier3_report, _spec_world = run_tier3_speculative(
                work_dir=work_dir,
                source=tier3_source,
                world=world,
                meta=meta,
                rules=rules,
                tiers=tiers,
                sufficiency=sufficiency,
                base_world=tier2_world,
            )
            (work_dir / "policy_case_speculative_audit.json").write_text(
                json.dumps(tier3_report.model_dump(mode="json"), indent=2, ensure_ascii=False)
                + "\n",
                encoding="utf-8",
            )

    lenient_result: PolicyQueryResultV1 | None = None
    if lenient_query_enabled(lenient_query):
        print_fn("[policy_case] lenient query (opt-in existential)")
        lenient_result = run_lenient_policy_query(meta, world, rules)

    addendum = PolicyCaseTierAddendumV1(
        pathway_id=pathway_id,
        tier1_complete=sufficiency.tier1_complete,
        tier1=tier1_query,
        tier2=tier2_report.model_dump(mode="json") if tier2_report else None,
        tier3=tier3_report.model_dump(mode="json") if tier3_report else None,
        lenient=lenient_result,
        summary=_addendum_summary(sufficiency, tier1_query, tier2_report, tier3_report),
    )
    addendum_path = work_dir / "policy_case_tier_addendum.json"
    addendum_path.write_text(
        json.dumps(addendum.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    if lenient_result is not None and tier1_query is not None:
        legacy = build_query_addendum(tier1_query, lenient_result)
        (work_dir / "policy_case_query_addendum.json").write_text(
            json.dumps(legacy.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    narrative_path: str | None = None
    if not skip_narrative:
        nar = write_case_narrative(
            work_dir,
            pathway_id=pathway_id,
            sufficiency=sufficiency,
            tier1=tier1_query,
            tier2=tier2_report,
            tier3=tier3_report,
        )
        narrative_path = str(nar.resolve())

    if sufficiency.tier1_complete and tier1_query is not None:
        outcome: Literal["complete", "blocked_insufficient_evidence"] = "complete"
    else:
        outcome = "blocked_insufficient_evidence"

    cov = dict(world.coverage)
    if tier1_query:
        cov["defaulted_at_query"] = len(tier1_query.defaulted_variables)

    return {
        "outcome": outcome,
        "pathway_id": pathway_id,
        "tier1_complete": sufficiency.tier1_complete,
        "sufficiency": sufficiency,
        "sufficiency_report_path": str(suff_path.resolve()),
        "tier_addendum_path": str(addendum_path.resolve()),
        "tier1_query": tier1_query,
        "complete": complete,
        "explanation_path": explanation_path,
        "narrative_path": narrative_path,
        "world_coverage": cov,
        "lenient_result": lenient_result,
        "addendum": addendum,
        "link_warnings": link_warnings,
        "provenance_verdict": provenance_verdict,
    }


def _addendum_summary(sufficiency, tier1, tier2, tier3) -> str:
    parts = [f"tier1_complete={sufficiency.tier1_complete}"]
    if tier1:
        parts.append(f"tier1={tier1.compatibility}")
    if tier2 and tier2.tier2_query:
        parts.append(f"tier2={tier2.tier2_query.compatibility}")
    if tier3 and tier3.tier3_query:
        parts.append(f"tier3={tier3.tier3_query.compatibility}")
    return "; ".join(parts)


def build_policy_report_from_eval(
    *,
    instance_id: str,
    eval_result: dict[str, Any],
) -> PolicyCaseReportV1:
    sufficiency: PathwaySufficiencyReportV1 = eval_result["sufficiency"]
    tier1: PolicyQueryResultV1 | None = eval_result.get("tier1_query")
    lenient = eval_result.get("lenient_result")
    addendum = eval_result.get("addendum")

    dual_summary = None
    strict_lenient_diverges = None
    if lenient and tier1:
        leg = build_query_addendum(tier1, lenient)
        dual_summary = leg.summary
        strict_lenient_diverges = leg.strict_incompatible_lenient_compatible

    return PolicyCaseReportV1(
        instance_id=instance_id,
        outcome=eval_result["outcome"],
        provenance_verdict=eval_result.get("provenance_verdict"),
        pathway_id=eval_result.get("pathway_id", "compiled_default"),
        tier1_complete=sufficiency.tier1_complete,
        sufficiency_report_path=eval_result.get("sufficiency_report_path"),
        tier_addendum_path=eval_result.get("tier_addendum_path"),
        compatibility=tier1.compatibility if tier1 else None,
        z3_status=tier1.z3_status if tier1 else None,
        world_coverage=eval_result.get("world_coverage", {}),
        explanation_path=eval_result.get("explanation_path"),
        narrative_path=eval_result.get("narrative_path"),
        defaulted_at_query=tier1.defaulted_variables if tier1 else [],
        lenient_compatibility=lenient.compatibility if lenient else None,
        lenient_z3_status=lenient.z3_status if lenient else None,
        query_addendum_path=None,
        dual_query_summary=dual_summary,
        strict_incompatible_lenient_compatible=strict_lenient_diverges,
        link_warnings=eval_result.get("link_warnings", []),
        tier_addendum_summary=addendum.summary if addendum else None,
    )


__all__ = [
    "PolicyCaseTierAddendumV1",
    "build_policy_report_from_eval",
    "run_policy_evaluation",
    "tiers_on_block_enabled",
]
