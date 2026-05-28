"""CrossRepairer compile + registry loop (hardened apply path)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from pivot_pipeline.cross_critic_interactive_loop import warn_change_summary_outside_approved
from pivot_pipeline.cross_repair_registry import (
    cross_repair_count_api_as_attempt,
    cross_repair_registry_attempts_max,
    run_cross_repair_registry,
)
from pivot_pipeline.cross_repairer_agent import (
    MergeRepairerOutputError,
    append_cross_repairer_trace,
    cross_repair_compile_attempts_max,
    run_cross_repairer,
)
from pivot_pipeline.llm import pivot_llm_complete
from pivot_pipeline.repair_apply import apply_repaired_rules_and_refresh
from pivot_pipeline.test_repair_registry import is_repairer_api_error
from pivot_pipeline.repair_ir_validation import (
    RepairIrValidationError,
    compile_validation_hint,
    precompile_repaired_rules_validated,
)
from pivot_pipeline.test_repair_rules_payload import focus_rule_ids_from_handoff
from pivot_pipeline.tester_repairer_agent import RepairErrorStage


@dataclass
class CrossRepairSessionResult:
    success: bool
    rules: list[dict[str, Any]]
    meta: Any | None = None
    synth: str | None = None
    z3_result: dict[str, Any] | None = None
    precheck_ok: bool | None = None
    precheck_issues: list[Any] | None = None
    linearized: str | None = None


def run_cross_repair_session(
    *,
    work_dir: Path,
    policy_id: str,
    rules: list[dict[str, Any]],
    handoff: dict[str, Any],
    cross_approved: set[str],
    cross_ignored: set[str],
    cross_repairs_used: int,
    processed_nl_excerpt: str,
    linearized_excerpt: str,
    nl_lines_reg: list[str],
    skip_registry: bool,
    meta_path: Path,
    nl_for_precheck: Path,
    summary: dict[str, Any],
    rules_envelope: dict[str, Any],
    no_vnext_lowering: bool,
    print_fn: Callable[..., None],
    llm: Callable[..., str] = pivot_llm_complete,
) -> CrossRepairSessionResult:
    """
    Run CrossRepairer with merge, pre-compile, registry (with repair/skip), artifact refresh.

    Returns ``success=True`` only when rules are written and artifacts refreshed.
    """
    compile_cap = cross_repair_compile_attempts_max()
    registry_cap = cross_repair_registry_attempts_max()
    count_api = cross_repair_count_api_as_attempt()
    compile_feedback: str | None = None
    merge_feedback: str | None = None
    api_retries_no_burn = 0

    for compile_attempt in range(compile_cap):
        if compile_attempt > 0:
            print_fn(
                f"[policy gate] Retrying CrossRepairer (compile attempt "
                f"{compile_attempt + 1}/{compile_cap})...\n"
            )
        try:
            out, json_parse_retry_used = run_cross_repairer(
                policy_id=policy_id,
                rules=rules,
                handoff=handoff,
                processed_nl_excerpt=processed_nl_excerpt,
                linearized_excerpt=linearized_excerpt,
                compile_validation_error=compile_feedback,
                merge_validation_error=merge_feedback,
                llm=llm,
            )
        except MergeRepairerOutputError as me:
            print_fn(
                f"[policy gate] CrossRepairer returned incomplete rules "
                f"(attempt {compile_attempt + 1}/{compile_cap}): {me}\n"
            )
            merge_feedback = str(me)
            compile_feedback = None
            append_cross_repairer_trace(
                work_dir,
                {
                    "round": cross_repairs_used,
                    "compile_attempt": compile_attempt + 1,
                    "error_stage": "rules_merge",
                    "error": str(me),
                    "approved_finding_ids": sorted(cross_approved),
                    "ignored_finding_ids": sorted(cross_ignored),
                },
            )
            continue
        except Exception as re:
            stage: RepairErrorStage = (
                "repairer_api" if is_repairer_api_error(re) else "repairer_json"
            )
            print_fn(f"[policy gate] CrossRepairer failed ({stage}): {re}\n")
            append_cross_repairer_trace(
                work_dir,
                {
                    "round": cross_repairs_used,
                    "compile_attempt": compile_attempt + 1,
                    "error_stage": stage,
                    "error": str(re),
                    "approved_finding_ids": sorted(cross_approved),
                    "ignored_finding_ids": sorted(cross_ignored),
                },
            )
            if stage == "repairer_api" and not count_api:
                api_retries_no_burn += 1
                if api_retries_no_burn < 3:
                    continue
            return CrossRepairSessionResult(success=False, rules=rules)

        cs_dumped = [c.model_dump() for c in out.change_summary]
        warn_change_summary_outside_approved(cs_dumped, cross_approved, print_fn=print_fn)
        append_cross_repairer_trace(
            work_dir,
            {
                "round": cross_repairs_used,
                "compile_attempt": compile_attempt + 1,
                "compile_attempt_cap": compile_cap,
                "change_summary": cs_dumped,
                "json_parse_retry_used": json_parse_retry_used,
                "approved_finding_ids": sorted(cross_approved),
                "ignored_finding_ids": sorted(cross_ignored),
            },
        )
        merged_rules = out.rules
        rules_before = rules
        focus_ids = focus_rule_ids_from_handoff(handoff)
        dropped_by_id: dict[str, list[str]] = {}

        try:
            compiled, dropped_by_id = precompile_repaired_rules_validated(
                policy_id,
                merged_rules,
                rules_before=rules_before,
                focus_rule_ids=focus_ids,
                change_summary=cs_dumped,
                skip_vnext_lowering=no_vnext_lowering,
                policy_semantics_version=rules_envelope.get("policy_semantics_version"),
            )
            if dropped_by_id:
                append_cross_repairer_trace(
                    work_dir,
                    {
                        "round": cross_repairs_used,
                        "compile_attempt": compile_attempt + 1,
                        "sanitize_dropped_keys": dropped_by_id,
                        "approved_finding_ids": sorted(cross_approved),
                        "ignored_finding_ids": sorted(cross_ignored),
                    },
                )
        except RepairIrValidationError as ve:
            print_fn(
                f"[policy gate] Cross-repaired rules failed IR validation (attempt "
                f"{compile_attempt + 1}/{compile_cap}): {ve}\n"
            )
            compile_feedback = str(ve) + compile_validation_hint(ve)
            merge_feedback = None
            append_cross_repairer_trace(
                work_dir,
                {
                    "round": cross_repairs_used,
                    "compile_attempt": compile_attempt + 1,
                    "error_stage": "rules_compile",
                    "compile_validation_error": str(ve),
                    "sanitize_dropped_keys": dropped_by_id,
                    "approved_finding_ids": sorted(cross_approved),
                    "ignored_finding_ids": sorted(cross_ignored),
                },
            )
            continue
        except Exception as ce:
            print_fn(
                f"[policy gate] Cross-repaired rules did not compile (attempt "
                f"{compile_attempt + 1}/{compile_cap}): {ce}\n"
            )
            compile_feedback = str(ce) + compile_validation_hint(ce)
            merge_feedback = None
            append_cross_repairer_trace(
                work_dir,
                {
                    "round": cross_repairs_used,
                    "compile_attempt": compile_attempt + 1,
                    "error_stage": "rules_compile",
                    "compile_validation_error": str(ce),
                    "approved_finding_ids": sorted(cross_approved),
                    "ignored_finding_ids": sorted(cross_ignored),
                },
            )
            continue

        new_rules = compiled
        registry_ok = False
        if skip_registry:
            registry_ok = True
        else:
            for reg_attempt in range(registry_cap):
                try:
                    _reg, new_rules, reused = run_cross_repair_registry(
                        work_dir=work_dir,
                        nl_lines_reg=nl_lines_reg,
                        rules_before=rules_before,
                        merged_rules=new_rules,
                        cli_skip_registry=False,
                        llm=llm,
                    )
                    if reused:
                        print_fn(
                            "[policy gate] Registry skipped (slug set unchanged); "
                            "reusing identifier_registry.json.\n"
                        )
                    registry_ok = True
                    break
                except Exception as re:
                    reg_stage: RepairErrorStage = (
                        "registry_api" if is_repairer_api_error(re) else "registry_json"
                    )
                    print_fn(
                        f"[policy gate] Registry pass failed ({reg_stage}) "
                        f"(registry attempt {reg_attempt + 1}/{registry_cap}): {re}\n"
                    )
                    append_cross_repairer_trace(
                        work_dir,
                        {
                            "round": cross_repairs_used,
                            "compile_attempt": compile_attempt + 1,
                            "registry_attempt": reg_attempt + 1,
                            "error_stage": reg_stage,
                            "error": str(re),
                            "approved_finding_ids": sorted(cross_approved),
                            "ignored_finding_ids": sorted(cross_ignored),
                        },
                    )
            if not registry_ok:
                return CrossRepairSessionResult(success=False, rules=rules)

        try:
            rules, meta, synth, z3_result, ok, issues, linearized = apply_repaired_rules_and_refresh(
                work_dir=work_dir,
                policy_id=policy_id,
                rules=new_rules,
                meta_path=meta_path,
                nl_for_precheck=nl_for_precheck,
                summary=summary,
                after_rules_basename="rules_after_cross_repair.json",
                refresh_linearized=True,
                rules_envelope=rules_envelope,
                skip_vnext_lowering=no_vnext_lowering,
            )
        except Exception as ce:
            print_fn(
                f"[policy gate] Artifact refresh failed after cross repair "
                f"(attempt {compile_attempt + 1}/{compile_cap}): {ce}\n"
            )
            append_cross_repairer_trace(
                work_dir,
                {
                    "round": cross_repairs_used,
                    "compile_attempt": compile_attempt + 1,
                    "error_stage": "rules_compile",
                    "error": str(ce),
                    "approved_finding_ids": sorted(cross_approved),
                },
            )
            compile_feedback = str(ce)
            continue

        return CrossRepairSessionResult(
            success=True,
            rules=rules,
            meta=meta,
            synth=synth,
            z3_result=z3_result,
            precheck_ok=ok,
            precheck_issues=issues,
            linearized=linearized,
        )

    print_fn(
        f"[policy gate] CrossRepairer compile/registry budget exhausted ({compile_cap} attempts).\n"
    )
    return CrossRepairSessionResult(success=False, rules=rules)


__all__ = ["CrossRepairSessionResult", "run_cross_repair_session"]
