"""Semantic Repairer_Piv compile + registry session (hardened apply path)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from pivot_pipeline.llm import pivot_llm_complete
from pivot_pipeline.post_model_workflow import critic_repair_compile_attempts_max
from pivot_pipeline.post_model_workflow import critic_semantic_repair_count_api_as_attempt
from pivot_pipeline.repair_apply import apply_repaired_rules_and_refresh
from pivot_pipeline.repair_stall import (
    RepairStallTracker,
    semantic_repair_stall_fail_fast,
    semantic_repair_stall_threshold,
    stall_gate_message,
)
from pivot_pipeline.repairer_piv_agent import append_repairer_trace, run_repairer_piv_semantic
from pivot_pipeline.rules_document import envelope_from_summary_or_body
from pivot_pipeline.semantic_repair_registry import (
    run_semantic_repair_registry,
    semantic_repair_registry_attempts_max,
)
from pivot_pipeline.test_repair_registry import is_repairer_api_error
from pivot_pipeline.repair_ir_validation import (
    RepairIrValidationError,
    compile_validation_hint,
    precompile_repaired_rules_validated,
)
from pivot_pipeline.test_repair_rules_payload import (
    MergeRepairerOutputError,
    focus_rule_ids_from_handoff,
)
from pivot_pipeline.tester_repairer_agent import RepairErrorStage


@dataclass
class SemanticRepairSessionResult:
    success: bool
    rules: list[dict[str, Any]]
    meta: Any | None = None
    synth: str | None = None
    z3_result: dict[str, Any] | None = None
    precheck_ok: bool | None = None
    precheck_issues: list[Any] | None = None
    last_stage: str | None = None
    last_error: str | None = None
    stall_detected: bool = False


def run_semantic_repair_session(
    *,
    work_dir: Path,
    policy_id: str,
    rules: list[dict[str, Any]],
    handoff: dict[str, Any],
    repair_session: int,
    nl_text_for_artifacts: str,
    synth: str,
    nl_lines_reg: list[str],
    skip_registry: bool,
    meta_path: Path,
    nl_for_precheck: Path,
    summary: dict[str, Any],
    print_fn: Callable[..., None],
    llm: Callable[..., str] = pivot_llm_complete,
    proceed_token: str = "PROCEED_INCOMPLETE",
) -> SemanticRepairSessionResult:
    """
    Run Repairer_Piv (semantic) with merge, pre-compile, registry sub-loop, artifact refresh.
    """
    compile_cap = critic_repair_compile_attempts_max()
    registry_cap = semantic_repair_registry_attempts_max()
    count_api = critic_semantic_repair_count_api_as_attempt()
    stall = RepairStallTracker(threshold=semantic_repair_stall_threshold())
    fail_fast = semantic_repair_stall_fail_fast()

    compile_feedback: str | None = None
    merge_feedback: str | None = None
    last_error: BaseException | None = None
    last_stage: str | None = None
    last_registry_error: str | None = None
    compile_attempt = 0
    api_retries_no_burn = 0

    while compile_attempt < compile_cap:
        if compile_attempt > 0:
            print_fn(
                f"[policy gate] Retrying semantic Repairer_Piv (attempt "
                f"{compile_attempt + 1}/{compile_cap})...\n"
            )
        if fail_fast and stall.stall_detected:
            print_fn(stall_gate_message(stage=stall.stall_stage or "unknown", proceed_token=proceed_token))
            return SemanticRepairSessionResult(
                success=False,
                rules=rules,
                last_stage=stall.stall_stage,
                last_error=stall.stall_fingerprint,
                stall_detected=True,
            )

        try:
            out, json_parse_retry_used = run_repairer_piv_semantic(
                policy_id=policy_id,
                rules=rules,
                handoff=handoff,
                effective_nl_excerpt=nl_text_for_artifacts,
                synthetic_excerpt=synth,
                compile_validation_error=compile_feedback,
                merge_validation_error=merge_feedback,
                llm=llm,
            )
        except MergeRepairerOutputError as me:
            stage: RepairErrorStage = "rules_merge"
            print_fn(
                f"[policy gate] Repairer_Piv returned incomplete rules "
                f"(attempt {compile_attempt + 1}/{compile_cap}): {me}\n"
            )
            last_error = me
            last_stage = stage
            merge_feedback = str(me)
            compile_feedback = None
            append_repairer_trace(
                work_dir,
                {
                    "repair_session": repair_session,
                    "compile_attempt": compile_attempt + 1,
                    "error_stage": stage,
                    "error": str(me),
                },
                kind="semantic",
            )
            if stall.record(stage, str(me)) and fail_fast:
                print_fn(stall_gate_message(stage=stage, proceed_token=proceed_token))
                return SemanticRepairSessionResult(
                    success=False,
                    rules=rules,
                    last_stage=stage,
                    last_error=str(me),
                    stall_detected=True,
                )
            compile_attempt += 1
            continue
        except Exception as re:
            stage = "repairer_api" if is_repairer_api_error(re) else "repairer_json"
            print_fn(f"[policy gate] Repairer_Piv failed ({stage}): {re}\n")
            last_error = re
            last_stage = stage
            append_repairer_trace(
                work_dir,
                {
                    "repair_session": repair_session,
                    "compile_attempt": compile_attempt + 1,
                    "error_stage": stage,
                    "error": str(re),
                },
                kind="semantic",
            )
            if stall.record(stage, str(re)) and fail_fast:
                print_fn(stall_gate_message(stage=stage, proceed_token=proceed_token))
                return SemanticRepairSessionResult(
                    success=False,
                    rules=rules,
                    last_stage=stage,
                    last_error=str(re),
                    stall_detected=True,
                )
            if stage == "repairer_api" and not count_api:
                api_retries_no_burn += 1
                if api_retries_no_burn < 3:
                    continue
            compile_attempt += 1
            continue

        append_repairer_trace(
            work_dir,
            {
                "repair_session": repair_session,
                "compile_attempt": compile_attempt + 1,
                "compile_attempt_cap": compile_cap,
                "change_summary": [c.model_dump() for c in out.change_summary],
                "json_parse_retry_used": json_parse_retry_used,
            },
            kind="semantic",
        )
        api_retries_no_burn = 0
        merged_rules = out.rules
        rules_before = rules
        focus_ids = focus_rule_ids_from_handoff(handoff)
        cs_dumped = [c.model_dump() for c in out.change_summary]
        dropped_by_id: dict[str, list[str]] = {}

        try:
            compiled_rules, dropped_by_id = precompile_repaired_rules_validated(
                policy_id,
                merged_rules,
                rules_before=rules_before,
                focus_rule_ids=focus_ids,
                change_summary=cs_dumped,
            )
            if dropped_by_id:
                append_repairer_trace(
                    work_dir,
                    {
                        "repair_session": repair_session,
                        "compile_attempt": compile_attempt + 1,
                        "sanitize_dropped_keys": dropped_by_id,
                    },
                    kind="semantic",
                )
        except RepairIrValidationError as ve:
            stage = "rules_compile"
            print_fn(
                f"[policy gate] Repaired rules failed IR validation (attempt "
                f"{compile_attempt + 1}/{compile_cap}): {ve}\n"
            )
            last_error = ve
            last_stage = stage
            compile_feedback = str(ve) + compile_validation_hint(ve)
            merge_feedback = None
            append_repairer_trace(
                work_dir,
                {
                    "repair_session": repair_session,
                    "compile_attempt": compile_attempt + 1,
                    "error_stage": stage,
                    "error": str(ve),
                    "sanitize_dropped_keys": dropped_by_id,
                },
                kind="semantic",
            )
            if stall.record(stage, str(ve)) and fail_fast:
                print_fn(stall_gate_message(stage=stage, proceed_token=proceed_token))
                return SemanticRepairSessionResult(
                    success=False,
                    rules=rules,
                    last_stage=stage,
                    last_error=str(ve),
                    stall_detected=True,
                )
            compile_attempt += 1
            continue
        except Exception as ce:
            stage = "rules_compile"
            print_fn(
                f"[policy gate] Repaired rules did not compile (attempt "
                f"{compile_attempt + 1}/{compile_cap}): {ce}\n"
            )
            last_error = ce
            last_stage = stage
            compile_feedback = str(ce) + compile_validation_hint(ce)
            merge_feedback = None
            append_repairer_trace(
                work_dir,
                {
                    "repair_session": repair_session,
                    "compile_attempt": compile_attempt + 1,
                    "error_stage": stage,
                    "error": str(ce),
                },
                kind="semantic",
            )
            if stall.record(stage, str(ce)) and fail_fast:
                print_fn(stall_gate_message(stage=stage, proceed_token=proceed_token))
                return SemanticRepairSessionResult(
                    success=False,
                    rules=rules,
                    last_stage=stage,
                    last_error=str(ce),
                    stall_detected=True,
                )
            compile_attempt += 1
            continue

        stall.reset_repairer_track()
        new_rules = compiled_rules
        registry_ok = skip_registry

        if not skip_registry:
            for reg_attempt in range(registry_cap):
                try:
                    _reg, new_rules, reused = run_semantic_repair_registry(
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
                    last_registry_error = str(re)
                    last_stage = reg_stage
                    last_error = re
                    print_fn(
                        f"[policy gate] Registry after repair failed ({reg_stage}) "
                        f"(registry attempt {reg_attempt + 1}/{registry_cap}): {re}\n"
                    )
                    append_repairer_trace(
                        work_dir,
                        {
                            "repair_session": repair_session,
                            "compile_attempt": compile_attempt + 1,
                            "registry_attempt": reg_attempt + 1,
                            "error_stage": reg_stage,
                            "error": str(re),
                        },
                        kind="semantic",
                    )
                    if stall.record(reg_stage, str(re)) and fail_fast:
                        print_fn(stall_gate_message(stage=reg_stage, proceed_token=proceed_token))
                        return SemanticRepairSessionResult(
                            success=False,
                            rules=rules,
                            last_stage=reg_stage,
                            last_error=str(re),
                            stall_detected=True,
                        )
            if not registry_ok:
                break

        try:
            rules, meta, synth_out, z3_result, ok, issues, _lin = apply_repaired_rules_and_refresh(
                work_dir=work_dir,
                policy_id=policy_id,
                rules=new_rules,
                meta_path=meta_path,
                nl_for_precheck=nl_for_precheck,
                summary=summary,
                after_rules_basename="rules_after_semantic_repair.json",
                refresh_linearized=False,
                rules_envelope=envelope_from_summary_or_body(summary),
            )
        except Exception as ce:
            stage = "rules_compile"
            print_fn(
                f"[policy gate] Artifact refresh failed after semantic repair "
                f"(attempt {compile_attempt + 1}/{compile_cap}): {ce}\n"
            )
            last_error = ce
            last_stage = stage
            compile_attempt += 1
            continue

        print_fn(
            f"[policy gate] Semantic repair succeeded (Repairer_Piv attempt "
            f"{compile_attempt + 1}/{compile_cap}); artifacts updated.\n"
        )
        return SemanticRepairSessionResult(
            success=True,
            rules=rules,
            meta=meta,
            synth=synth_out,
            z3_result=z3_result,
            precheck_ok=ok,
            precheck_issues=issues,
        )

    err = str(last_error) if last_error is not None else None
    return SemanticRepairSessionResult(
        success=False,
        rules=rules,
        last_stage=last_stage,
        last_error=err or last_registry_error,
        stall_detected=stall.stall_detected,
    )


__all__ = ["SemanticRepairSessionResult", "run_semantic_repair_session"]
