"""Policy case pipeline: World → Trust → Query → Explain."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

from pivot_pipeline.external_tester.link_consistency import check_link_consistency
from pivot_pipeline.external_tester.policy_case_eval import (
    build_policy_report_from_eval,
    run_policy_evaluation,
)
from pivot_pipeline.external_tester.policy_query import lenient_query_enabled
from pivot_pipeline.external_tester.schemas import (
    ExternalSourceEnvelope,
    ExternalWorldFillV1,
    PolicyCaseReportV1,
    PolicyCaseWorldV1,
    VariableAssignment,
    load_source_path,
)
from pivot_pipeline.external_tester.trace import append_trace
from pivot_pipeline.external_tester.trust import _provenance_max_rounds, run_trust_review
from pivot_pipeline.external_tester.variable_catalog import (
    ensure_meta_variable_sorts,
    write_variable_catalog,
)
from pivot_pipeline.external_tester.variable_tiers import tiers_for_meta
from pivot_pipeline.external_tester.world_builder import (
    build_policy_case_world,
    resolve_derive_mode,
)
from pivot_pipeline.external_tester.world_to_z3 import resolve_unknown_policy
from pivot_pipeline.ir import MetaScheme
from pivot_pipeline.template_suite.run import load_meta_from_rules_path


def _active_rule_ids(meta: MetaScheme) -> list[str]:
    from pivot_pipeline.ir import Preemption
    from pivot_pipeline.pathway_compiler import resolve_active_rule_ids

    active = resolve_active_rule_ids(list(meta.rules))
    return sorted(
        r.rule_id for r in meta.rules if r.rule_id in active and not isinstance(r, Preemption)
    )


def check_prior_critics(work_dir: Path) -> list[str]:
    """Return blocking reasons if --require-prior-critics and gates not clean."""
    reasons: list[str] = []
    cc = work_dir / "cross_critic_report.json"
    if cc.is_file():
        try:
            data = json.loads(cc.read_text(encoding="utf-8"))
            if str(data.get("verdict", "")).upper() != "PASS":
                reasons.append("cross_critic not PASS")
        except json.JSONDecodeError:
            reasons.append("cross_critic_report.json invalid")
    cr = work_dir / "critic_report.json"
    if cr.is_file():
        try:
            data = json.loads(cr.read_text(encoding="utf-8"))
            if str(data.get("verdict", "")).upper() == "DRIFT":
                reasons.append("pivot critic DRIFT")
        except json.JSONDecodeError:
            reasons.append("critic_report.json invalid")
    tr = work_dir / "tester_report.json"
    if tr.is_file():
        try:
            data = json.loads(tr.read_text(encoding="utf-8"))
            if str(data.get("verdict", "")).lower() == "issues":
                reasons.append("tester issues")
        except json.JSONDecodeError:
            reasons.append("tester_report.json invalid")
    return reasons


def persist_meta_scheme(work_dir: Path, meta: MetaScheme) -> None:
    path = work_dir / "meta_scheme.json"
    payload = meta.model_dump(mode="json")
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _world_to_link_fill(world: PolicyCaseWorldV1, meta: MetaScheme) -> ExternalWorldFillV1:
    sorts = dict(meta.variable_sorts)
    assignments: list[VariableAssignment] = []
    for s in world.stated:
        assignments.append(
            VariableAssignment(
                variable=s.variable,
                sort=s.sort,
                status=s.status,
                value=s.value,
                provenance=s.provenance,
                rationale=s.rationale,
            )
        )
    for name in world.unknown:
        st = sorts.get(name, "int")
        assignments.append(
            VariableAssignment(
                variable=name,
                sort=st,  # type: ignore[arg-type]
                status="not_found",
                rationale="unknown grounded (no cite)",
            )
        )
    # Derived vars come from Z3 witness, not document rows — omit from link fill.
    return ExternalWorldFillV1(
        instance_id=world.instance_id,
        template_kind="scenario",
        golden={"sat": True},
        assignments=assignments,
    )


def _write_policy_report(work_dir: Path, report: PolicyCaseReportV1) -> None:
    payload = report.model_dump(mode="json")
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    (work_dir / "policy_case_report.json").write_text(text, encoding="utf-8")
    (work_dir / "external_tester_run_report.json").write_text(text, encoding="utf-8")


def run_policy_case_pipeline(
    *,
    work_dir: Path,
    source_path: Path,
    rules_extracted_path: Path | None = None,
    instance_id: str = "ext_001",
    require_prior_critics: bool = False,
    derive_mode: str | None = None,
    unknown_policy: str | None = None,
    lenient_query: bool | None = None,
    pathway_id: str = "compiled_default",
    skip_tier2: bool = False,
    skip_tier3: bool = False,
    skip_narrative: bool = False,
    print_fn: Callable[..., None] = print,
) -> dict[str, Any]:
    """
    v4 pipeline: extract world → provenance (stated) → Z3 compatibility → explanation.
    """
    work_dir = work_dir.resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    rules_path = rules_extracted_path or (work_dir / "rules_extracted.json")
    if not rules_path.is_file():
        raise FileNotFoundError(f"missing rules_extracted: {rules_path}")

    summary: dict[str, Any] = {
        "policy_case_ok": False,
        "instance_id": instance_id,
        "derive_mode": resolve_derive_mode(derive_mode),
        "unknown_policy": resolve_unknown_policy(unknown_policy),
        "lenient_query": lenient_query_enabled(lenient_query),
        "pathway_id": pathway_id,
    }

    if require_prior_critics:
        blockers = check_prior_critics(work_dir)
        if blockers:
            summary["policy_case_blocked"] = blockers
            summary["outcome"] = "blocked_policy_case_prerequisites"
            return summary

    source = load_source_path(source_path.resolve())
    (work_dir / "policy_case_source.json").write_text(
        json.dumps(source.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (work_dir / "external_tester_source.json").write_text(
        json.dumps(source.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    raw_rules = json.loads(rules_path.read_text(encoding="utf-8"))
    rules_list = raw_rules.get("rules") or []
    meta = load_meta_from_rules_path(rules_path)
    meta = ensure_meta_variable_sorts(meta, rules_list)
    persist_meta_scheme(work_dir, meta)
    write_variable_catalog(work_dir, meta, rules=rules_list)
    tiers = tiers_for_meta(meta, rules_list)
    _active_rule_ids(meta)

    max_rounds = _provenance_max_rounds()
    fill_feedback: str | None = None
    refill_vars: list[str] | None = None
    link_warnings: list[str] = []

    for round_idx in range(1, max_rounds + 1):
        reason = (
            f"provenance refill ({len(refill_vars)} vars)"
            if refill_vars
            else ("retry" if fill_feedback else "initial world build")
        )
        print_fn(f"[policy_case] round {round_idx}/{max_rounds} — {reason}")

        try:
            world = build_policy_case_world(
                work_dir=work_dir,
                source=source,
                meta=meta,
                rules=rules_list,
                instance_id=instance_id,
                derive_mode=derive_mode,
                refill_variables=refill_vars,
                feedback=fill_feedback or "",
            )
        except (ValueError, RuntimeError) as e:
            fill_feedback = str(e)
            append_trace(work_dir, {"kind": "world_build_error", "error": fill_feedback})
            print_fn(f"[policy_case] world build failed: {fill_feedback[:240]}")
            refill_vars = None
            continue

        link = check_link_consistency(
            _world_to_link_fill(world, meta),
            meta,
            rules_list,
            tiers=tiers,
            warn_only=True,
        )
        if link.errors:
            link_warnings = link.errors
            append_trace(work_dir, {"kind": "link_warn", "errors": link.errors})
            print_fn(f"[policy_case] link warnings ({len(link.errors)})")

        print_fn("[policy_case] provenance review (stated only)")
        review = run_trust_review(work_dir=work_dir, source=source, world=world, meta=meta)
        summary["provenance_verdict"] = review.verdict
        summary["blocking_variables"] = review.blocking_variables

        if review.verdict != "PASS":
            notes = [
                f"{fr.variable}: {fr.verdict} — {fr.notes}"
                for fr in review.field_reviews
                if fr.variable in review.blocking_variables
            ]
            fill_feedback = "Provenance reviewer rejected:\n" + "\n".join(notes)
            refill_vars = list(review.blocking_variables)
            append_trace(
                work_dir,
                {"kind": "provenance_fail", "blocking": review.blocking_variables},
            )
            continue

        (work_dir / "policy_case_world.json").write_text(
            json.dumps(world.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        eval_result = run_policy_evaluation(
            work_dir=work_dir,
            meta=meta,
            world=world,
            rules=rules_list,
            tiers=tiers,
            instance_id=instance_id,
            pathway_id=pathway_id,
            provenance_verdict=review.verdict,
            link_warnings=link_warnings,
            lenient_query=lenient_query,
            skip_tier2=skip_tier2,
            skip_tier3=skip_tier3,
            skip_narrative=skip_narrative,
            source=source,
            print_fn=print_fn,
        )

        if eval_result.get("blocked"):
            report = PolicyCaseReportV1(
                instance_id=instance_id,
                outcome="blocked_query",
                provenance_verdict=review.verdict,
                pathway_id=pathway_id,
                tier1_complete=eval_result.get("sufficiency").tier1_complete
                if eval_result.get("sufficiency")
                else None,
                error=eval_result.get("error"),
                link_warnings=link_warnings,
            )
            _write_policy_report(work_dir, report)
            summary["outcome"] = "blocked_query"
            summary["error"] = eval_result.get("error")
            return summary

        report = build_policy_report_from_eval(
            instance_id=instance_id,
            eval_result=eval_result,
        )
        _write_policy_report(work_dir, report)

        tier1 = eval_result.get("tier1_query")
        append_trace(
            work_dir,
            {
                "kind": "pathway_sufficiency",
                "tier1_complete": eval_result.get("tier1_complete"),
                "missing_n": len(eval_result["sufficiency"].missing),
            },
        )
        if tier1:
            append_trace(
                work_dir,
                {
                    "kind": "policy_query_tier1",
                    "compatibility": tier1.compatibility,
                    "z3_status": tier1.z3_status,
                },
            )

        cov = eval_result.get("world_coverage", {})
        summary["policy_case_report"] = str((work_dir / "policy_case_report.json").resolve())
        summary["tier1_complete"] = eval_result.get("tier1_complete")
        summary["tier_addendum_summary"] = report.tier_addendum_summary
        if tier1:
            summary["compatibility"] = tier1.compatibility
            summary["z3_status"] = tier1.z3_status
        summary["world_coverage"] = cov
        summary["policy_case_ok"] = True
        outcome = eval_result["outcome"]
        summary["outcome"] = (
            "policy_case_complete"
            if outcome == "complete"
            else "policy_case_blocked_insufficient_evidence"
        )
        if report.dual_query_summary:
            summary["dual_query_summary"] = report.dual_query_summary
        lenient = eval_result.get("lenient_result")
        if lenient:
            summary["lenient_compatibility"] = lenient.compatibility
        return summary

    report = PolicyCaseReportV1(
        instance_id=instance_id,
        outcome="blocked_provenance",
        provenance_verdict=summary.get("provenance_verdict"),
        error="exhausted provenance refill rounds",
        link_warnings=link_warnings,
    )
    _write_policy_report(work_dir, report)
    summary["outcome"] = "blocked_provenance"
    summary["policy_case_error"] = report.error
    return summary


def execute_after_review(
    *,
    work_dir: Path,
    meta: MetaScheme,
    fill: ExternalWorldFillV1,
    review_verdict: str,
    test_mode: str | None = None,
    rules: list[dict[str, Any]] | None = None,
    tiers: dict | None = None,
    fill_orchestration: str = "v4",
) -> dict[str, Any]:
    """Legacy v2/v3 lower + Z3 + diff (tests only)."""
    from pivot_pipeline.external_tester.lower import to_template_instance, world_coverage
    from pivot_pipeline.external_tester.syntax_repair_agent import repair_fill_json
    from pivot_pipeline.external_tester.variable_tiers import tiers_for_meta
    from pivot_pipeline.external_tester.world_defaults import (
        WORLD_SEMANTICS,
        DerivedIncompleteError,
        derived_not_found_policy,
        not_found_defaults,
    )
    from pivot_pipeline.template_suite.diff import diff_instance
    from pivot_pipeline.template_suite.execute_z3 import execute_instance
    from pivot_pipeline.template_suite.validate import validate_instance

    if review_verdict != "PASS":
        return {
            "skipped": True,
            "reason": "provenance_review not PASS",
            "provenance_review_verdict": review_verdict,
        }

    mode = test_mode or fill.template_kind
    closed_world = mode == "scenario"
    tier_map = tiers
    if tier_map is None and rules is not None:
        tier_map = tiers_for_meta(meta, rules)

    row: dict[str, Any] = {
        "instance_id": fill.instance_id,
        "template_kind": fill.template_kind,
        "test_mode": mode,
        "fill_orchestration_version": fill_orchestration,
        "provenance_review_verdict": review_verdict,
        "world_coverage": world_coverage(
            fill, len(meta.variable_sorts), closed_world=closed_world
        ),
        "verdict": "error",
        "actual": None,
        "golden": fill.golden,
        "diff": None,
        "error": None,
    }
    if closed_world:
        row["world_semantics"] = WORLD_SEMANTICS
        row["not_found_defaults"] = not_found_defaults()
        row["derived_execute_policy"] = derived_not_found_policy()

    try:
        inst = to_template_instance(fill, meta, rules=rules, tiers=tier_map)
    except DerivedIncompleteError as e:
        row["verdict"] = "blocked_derived_incomplete"
        row["derived_incomplete"] = e.variables
        row["error"] = str(e)
        return row

    try:
        validate_instance(meta, inst)
    except Exception as e:
        raw_fill = (work_dir / "external_world_fill.json").read_text(encoding="utf-8")
        try:
            fill = repair_fill_json(work_dir=work_dir, invalid_raw=raw_fill, error=str(e))
            inst = to_template_instance(fill, meta, rules=rules, tiers=tier_map)
            validate_instance(meta, inst)
        except Exception as e2:
            row["error"] = f"validate: {e}; syntax_repair: {e2}"
            return row

    try:
        actual = execute_instance(meta, inst)
        row["actual"] = actual
        verdict, diff = diff_instance(inst, actual)
        row["verdict"] = verdict
        row["diff"] = diff
    except Exception as e:
        row["error"] = f"{type(e).__name__}: {e}"
    return row


def run_external_tester_pipeline(**kwargs: Any) -> dict[str, Any]:
    """Backward-compatible alias for v4 policy case pipeline."""
    kwargs.pop("test_mode", None)
    kwargs.pop("fill_orchestration", None)
    kwargs.pop("query_rule_id", None)
    summary = run_policy_case_pipeline(**kwargs)
    summary["external_tester_ok"] = summary.get("policy_case_ok", False)
    oc = summary.get("outcome")
    if oc == "policy_case_complete":
        summary["outcome"] = "external_tester_complete"
    elif oc == "policy_case_blocked_insufficient_evidence":
        summary["outcome"] = "external_tester_blocked_insufficient_evidence"
    summary["external_instance_id"] = summary.get("instance_id")
    summary["external_test_verdict"] = summary.get("compatibility")
    return summary


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    from registry_stage.llm.gemini_call import load_repo_dotenv

    load_repo_dotenv()
    p = argparse.ArgumentParser(description="Policy case pipeline (world → trust → Z3 → explain)")
    p.add_argument("--work-dir", type=Path, required=True)
    p.add_argument("--external-source", type=Path, required=True)
    p.add_argument("--rules-json", type=Path, default=None)
    p.add_argument("--external-instance-id", default="ext_001")
    p.add_argument("--case-instance-id", default=None, help="Alias for --external-instance-id")
    p.add_argument(
        "--case-unknown-policy",
        choices=("cwa", "block"),
        default=None,
        help="cwa: false/0 at query; block: skip Z3 if unknown grounded",
    )
    p.add_argument(
        "--case-derive-mode",
        choices=("z3_witness", "llm_glossary"),
        default=None,
    )
    p.add_argument("--require-prior-critics", action="store_true")
    p.add_argument("--pathway-id", default="compiled_default", help="Evaluation pathway for sufficiency")
    p.add_argument("--skip-tier2", action="store_true", help="Skip tier-2 programmatic completion")
    p.add_argument("--skip-tier3", action="store_true", help="Skip tier-3 speculative LLM")
    p.add_argument("--skip-narrative", action="store_true", help="Skip policy_case_narrative.md")
    p.add_argument(
        "--enable-lenient-query",
        action="store_true",
        help="Opt-in existential lenient Z3 query (default off)",
    )
    p.add_argument(
        "--no-case-lenient-query",
        action="store_true",
        help="Deprecated alias: keep lenient off",
    )
    p.add_argument(
        "--external-test-mode",
        default=None,
        help="Deprecated; ignored (v4 always uses full-policy query)",
    )
    p.add_argument(
        "--external-fill-orchestration",
        default=None,
        help="Deprecated; ignored",
    )
    args = p.parse_args(argv)

    instance_id = args.case_instance_id or args.external_instance_id

    try:
        summary = run_policy_case_pipeline(
            work_dir=args.work_dir,
            source_path=args.external_source,
            rules_extracted_path=args.rules_json,
            instance_id=instance_id,
            require_prior_critics=args.require_prior_critics,
            derive_mode=args.case_derive_mode,
            unknown_policy=args.case_unknown_policy,
            lenient_query=True if args.enable_lenient_query else None,
            pathway_id=args.pathway_id,
            skip_tier2=args.skip_tier2,
            skip_tier3=args.skip_tier3,
            skip_narrative=args.skip_narrative,
        )
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        out = str(summary.get("outcome", ""))
        if out.startswith("blocked") or "insufficient_evidence" in out:
            return 1
        return 0
    except Exception as e:
        print(f"[policy_case] failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "check_prior_critics",
    "execute_after_review",
    "persist_meta_scheme",
    "run_external_tester_pipeline",
    "run_policy_case_pipeline",
]
