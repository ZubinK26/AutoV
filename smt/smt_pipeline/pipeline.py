"""NL→SMT-LIB orchestration (`control_flow_v3.md`)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from registry_stage.loaders import parse_handoff_bundle
from registry_stage.models import handoff_bundle_to_dict

from .commit import atomic_write_text
from .config import SmtPipelineConfig, smt_config_from_env
from .ids import new_bundle_id, new_rule_id
from .json_utils import extract_first_json_object
from .models import CriticContext, FormalizerContext, PipelineRunResult
from .rule_count import rule_count
from .smt_parse import parse_smt2_string_check
from .unsat_core import analyze_policy_sat_and_core, report_to_jsonable


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _merged_policy_text(existing: str, new_block: str, bundle_id: str) -> tuple[str, str]:
    committed_iso = _utc_now_iso()
    header = (
        f"; ============================================================\n"
        f"; Bundle: {bundle_id}  |  Committed: {committed_iso}\n"
        f"; ============================================================\n"
    )
    block_out = new_block if "; Bundle:" in new_block[:800] else header + new_block
    full = existing + "\n\n" + block_out if existing.strip() else block_out
    return full, committed_iso


def _log_line(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _is_in_scope(verdict: str) -> bool:
    return verdict != "OUT_OF_SCOPE"


def _load_handoff_json(path: Path) -> Any:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and (not data.get("bundle_id")):
        data["bundle_id"] = new_bundle_id()
    return data


def _context_size_bytes(policy_text: str, handoff_dict: dict[str, Any]) -> int:
    return len(policy_text.encode("utf-8")) + len(json.dumps(handoff_dict, ensure_ascii=False).encode("utf-8"))


def _failure_record(category: str, detail: str) -> dict[str, Any]:
    return {"category": category, "detail": detail}


def _write_bundle_json(
    path: Path,
    *,
    bundle_id: str,
    accepted_at: str,
    committed_at: Optional[str],
    pipeline_status: str,
    rule_ids: list[str],
    out_of_scope_line_indices: list[int],
    wfm_payload: dict[str, Any],
    failure_reason: Optional[dict[str, Any]],
    policy_model_path: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "bundle_id": bundle_id,
        "accepted_at": accepted_at,
        "committed_at": committed_at,
        "pipeline_status": pipeline_status,
        "rule_ids": rule_ids,
        "out_of_scope_line_indices": out_of_scope_line_indices,
        "wfm_payload": wfm_payload,
        "failure_reason": failure_reason,
        "policy_model_path": policy_model_path,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run_smt_pipeline(
    *,
    handoff_path: Path,
    policy_model_path: Path,
    bundle_out_dir: Path,
    cfg: Optional[SmtPipelineConfig] = None,
    formalizer_fn: Optional[Callable[[FormalizerContext], str]] = None,
    critic_fn: Optional[Callable[[CriticContext], dict[str, Any]]] = None,
) -> PipelineRunResult:
    """
    Run the v3 pipeline. If ``formalizer_fn`` / ``critic_fn`` are None, uses Gemini
    (requires GEMINI_API_KEY). Tests inject mocks.
    """
    cfg = cfg or smt_config_from_env()
    accepted_at = _utc_now_iso()

    raw = _load_handoff_json(handoff_path)
    handoff_dict = raw if isinstance(raw, dict) else {}
    bundle = parse_handoff_bundle(raw)

    bundle_id = bundle.bundle_id
    bundle_json_path = bundle_out_dir / f"{bundle_id}.json"
    log_path = bundle_out_dir / f"{bundle_id}.log.jsonl"

    def finalize(
        status: str,
        *,
        failure: Optional[dict[str, Any]] = None,
        committed_at: Optional[str] = None,
        rule_ids: Optional[list[str]] = None,
    ) -> PipelineRunResult:
        _write_bundle_json(
            bundle_json_path,
            bundle_id=bundle_id,
            accepted_at=accepted_at,
            committed_at=committed_at,
            pipeline_status="committed" if status == "success" else "failed",
            rule_ids=rule_ids or [],
            out_of_scope_line_indices=out_indices,
            wfm_payload=wfm_payload,
            failure_reason=failure,
            policy_model_path=str(policy_model_path.resolve()),
        )
        return PipelineRunResult(
            bundle_id=bundle_id,
            policy_model_path=str(policy_model_path.resolve()),
            bundle_record_path=str(bundle_json_path.resolve()),
            log_path=str(log_path.resolve()),
            status="success" if status == "success" else "failed",
            failure_reason=failure["category"] if failure else None,
            rule_ids=rule_ids or [],
        )

    wfm_payload = handoff_bundle_to_dict(bundle)

    out_indices = [ln.line_index for ln in bundle.lines if not _is_in_scope(ln.agent3_verdict)]
    in_scope_lines_struct = [ln for ln in bundle.lines if _is_in_scope(ln.agent3_verdict)]
    in_scope_sorted = sorted(in_scope_lines_struct, key=lambda x: x.line_index)

    policy_path_str = str(policy_model_path)
    existing = ""
    if policy_model_path.is_file():
        existing = policy_model_path.read_text(encoding="utf-8")

    if _context_size_bytes(existing, handoff_dict) > cfg.context_char_limit:
        return finalize(
            "failed",
            failure=_failure_record("CONTEXT_LIMIT_EXCEEDED", "handoff + policy exceeds context_char_limit"),
            rule_ids=[],
        )

    # Corrupt / unreadable existing policy (non-empty must parse alone)
    if existing.strip():
        ok, err = parse_smt2_string_check(existing, timeout_sec=cfg.parse_timeout_sec)
        if not ok:
            return finalize(
                "failed",
                failure=_failure_record("POLICY_MODEL_CORRUPT", err),
                rule_ids=[],
            )

    n_existing = rule_count(existing)

    if n_existing + len(in_scope_sorted) > cfg.rule_cap:
        pre_rules = [new_rule_id() for _ in in_scope_sorted]
        return finalize(
            "failed",
            failure=_failure_record(
                "SIZE_CAP_REACHED",
                f"current_rules={n_existing} in_scope_lines={len(in_scope_sorted)} cap={cfg.rule_cap}",
            ),
            rule_ids=pre_rules,
        )

    if not in_scope_sorted:
        return finalize("success", committed_at=_utc_now_iso(), rule_ids=[])

    rule_ids = [new_rule_id() for _ in in_scope_sorted]
    in_scope_text_lines: list[str] = []
    for rid, ln in zip(rule_ids, in_scope_sorted, strict=True):
        in_scope_text_lines.append(
            f"rule_id={rid} line_index={ln.line_index} statement_nl={json.dumps(ln.statement_nl, ensure_ascii=False)}"
        )

    if formalizer_fn is None:
        from .llm_steps import formalizer_smt2_block_gemini

        def formalizer_fn_impl(ctx: FormalizerContext) -> str:
            return formalizer_smt2_block_gemini(ctx, cfg=cfg)

        formalizer_fn = formalizer_fn_impl

    if critic_fn is None:
        from .llm_steps import critic_json_gemini

        def critic_fn_impl(ctx: CriticContext) -> dict[str, Any]:
            raw_txt = critic_json_gemini(ctx, cfg=cfg)
            return extract_first_json_object(raw_txt)

        critic_fn = critic_fn_impl

    def parse_concat(new_block: str) -> tuple[bool, str]:
        concat = existing + "\n\n" + new_block if existing.strip() else new_block
        return parse_smt2_string_check(concat, timeout_sec=cfg.parse_timeout_sec)

    # --- Loop 1: syntax ---
    syntax_feedback: Optional[str] = None
    block: str = ""
    loop1_left = cfg.syntax_repair_cap
    prev_formalizer_block: Optional[str] = None

    while loop1_left > 0:
        attempt = cfg.syntax_repair_cap - loop1_left + 1
        ctx = FormalizerContext(
            bundle_id=bundle_id,
            policy_path=policy_path_str,
            policy_text=existing,
            existing_rule_count=n_existing,
            in_scope_lines=in_scope_text_lines,
            attempt_index=attempt,
            critic_objections=syntax_feedback,
            previous_smt2_block=prev_formalizer_block,
        )
        exc_fb: Optional[str] = None
        try:
            block = formalizer_fn(ctx).strip()
        except Exception as e:
            block = ""
            exc_fb = f"formalizer_exception: {e}"
        ok, err = parse_concat(block)
        _log_line(
            log_path,
            {
                "bundle_id": bundle_id,
                "timestamp": _utc_now_iso(),
                "loop": "syntax",
                "iteration": attempt,
                "input_to_formalizer": {"error_or_objections": syntax_feedback or "(initial)"},
                "formalizer_output_smtlib": block[:8000] + ("..." if len(block) > 8000 else ""),
                "check_result": "pass" if ok else "fail",
                "check_detail": err if not ok else "",
            },
        )
        if ok:
            break
        loop1_left -= 1
        if block.strip():
            prev_formalizer_block = block
        if exc_fb is None:
            syntax_feedback = err
        else:
            syntax_feedback = f"{exc_fb}\nparse_error: {err}"
        if loop1_left == 0:
            return finalize(
                "failed",
                failure=_failure_record("SYNTAX_FAIL", err),
                rule_ids=rule_ids,
            )

    # --- Loop 2: semantic ---
    wfm_summary = "\n".join(in_scope_text_lines)

    def run_critic(proposed: str) -> dict[str, Any]:
        cctx = CriticContext(
            bundle_id=bundle_id,
            proposed_smt2_block=proposed,
            policy_path=policy_path_str,
            policy_text=existing,
            in_scope_wfm_summary=wfm_summary,
        )
        return critic_fn(cctx)

    def commit_after_sat(proposed_block: str) -> PipelineRunResult:
        full, committed_iso = _merged_policy_text(existing, proposed_block, bundle_id)
        if not cfg.skip_global_sat_check:
            try:
                sat_rep = analyze_policy_sat_and_core(full)
            except Exception as e:
                _log_line(
                    log_path,
                    {
                        "bundle_id": bundle_id,
                        "timestamp": _utc_now_iso(),
                        "loop": "global_sat",
                        "iteration": 1,
                        "input_to_formalizer": {},
                        "formalizer_output_smtlib": "",
                        "check_result": "fail",
                        "check_detail": str(e),
                    },
                )
                return finalize(
                    "failed",
                    failure=_failure_record("POLICY_SAT_CHECK_ERROR", str(e)),
                    rule_ids=rule_ids,
                )
            sat_json = report_to_jsonable(sat_rep)
            if sat_rep.sat_result != "sat":
                detail = json.dumps(sat_json, ensure_ascii=False)
                cat = "POLICY_UNSAT" if sat_rep.sat_result == "unsat" else "POLICY_SAT_UNKNOWN"
                _log_line(
                    log_path,
                    {
                        "bundle_id": bundle_id,
                        "timestamp": _utc_now_iso(),
                        "loop": "global_sat",
                        "iteration": 1,
                        "input_to_formalizer": {},
                        "formalizer_output_smtlib": "",
                        "check_result": "fail",
                        "check_detail": detail[:8000] + ("..." if len(detail) > 8000 else ""),
                        "sat_report": sat_json,
                    },
                )
                return finalize("failed", failure=_failure_record(cat, detail), rule_ids=rule_ids)
            _log_line(
                log_path,
                {
                    "bundle_id": bundle_id,
                    "timestamp": _utc_now_iso(),
                    "loop": "global_sat",
                    "iteration": 1,
                    "input_to_formalizer": {},
                    "formalizer_output_smtlib": "",
                    "check_result": "pass",
                    "check_detail": sat_rep.sat_result,
                    "sat_report": sat_json,
                },
            )
        atomic_write_text(policy_model_path, full)
        return finalize("success", committed_at=committed_iso, rule_ids=rule_ids)

    try:
        cr0 = run_critic(block)
    except Exception as e:
        return finalize(
            "failed",
            failure=_failure_record("SEMANTIC_FAIL", f"critic_exception: {e}"),
            rule_ids=rule_ids,
        )

    approved = bool(cr0.get("approved"))
    if approved:
        return commit_after_sat(block)

    objections_txt = json.dumps(cr0.get("objections", []), ensure_ascii=False)
    loop2_left = cfg.semantic_repair_cap
    parse_err: Optional[str] = None
    prev_formalizer_block: str = block

    while loop2_left > 0:
        sem_attempt = cfg.semantic_repair_cap - loop2_left + 1
        feedback = objections_txt if not parse_err else f"{objections_txt}\n\nparse_error:\n{parse_err}"
        ctx = FormalizerContext(
            bundle_id=bundle_id,
            policy_path=policy_path_str,
            policy_text=existing,
            existing_rule_count=n_existing,
            in_scope_lines=in_scope_text_lines,
            attempt_index=cfg.syntax_repair_cap + sem_attempt,
            critic_objections=feedback,
            previous_smt2_block=prev_formalizer_block,
        )
        try:
            block = formalizer_fn(ctx).strip()
        except Exception as e:
            block = ""
            parse_err = f"formalizer_exception: {e}"
            _log_line(
                log_path,
                {
                    "bundle_id": bundle_id,
                    "timestamp": _utc_now_iso(),
                    "loop": "semantic",
                    "iteration": sem_attempt,
                    "input_to_formalizer": {"error_or_objections": feedback},
                    "formalizer_output_smtlib": "",
                    "check_result": "fail",
                    "check_detail": parse_err,
                },
            )
            loop2_left -= 1
            if loop2_left == 0:
                return finalize(
                    "failed",
                    failure=_failure_record("SEMANTIC_FAIL", parse_err),
                    rule_ids=rule_ids,
                )
            continue

        prev_formalizer_block = block
        ok, err = parse_concat(block)
        _log_line(
            log_path,
            {
                "bundle_id": bundle_id,
                "timestamp": _utc_now_iso(),
                "loop": "semantic",
                "iteration": sem_attempt,
                "input_to_formalizer": {"error_or_objections": feedback},
                "formalizer_output_smtlib": block[:8000] + ("..." if len(block) > 8000 else ""),
                "check_result": "pass" if ok else "fail",
                "check_detail": err if not ok else "",
            },
        )
        if not ok:
            loop2_left -= 1
            parse_err = err
            if loop2_left == 0:
                return finalize(
                    "failed",
                    failure=_failure_record("SEMANTIC_FAIL", err),
                    rule_ids=rule_ids,
                )
            continue

        parse_err = None
        try:
            cr = run_critic(block)
        except Exception as e:
            loop2_left -= 1
            if loop2_left == 0:
                return finalize(
                    "failed",
                    failure=_failure_record("SEMANTIC_FAIL", f"critic_exception: {e}"),
                    rule_ids=rule_ids,
                )
            objections_txt = json.dumps([{"issue": "critic_crash", "detail": str(e)}], ensure_ascii=False)
            continue

        if bool(cr.get("approved")):
            return commit_after_sat(block)

        loop2_left -= 1
        objections_txt = json.dumps(cr.get("objections", []), ensure_ascii=False)
        if loop2_left == 0:
            return finalize(
                "failed",
                failure=_failure_record("SEMANTIC_FAIL", objections_txt),
                rule_ids=rule_ids,
            )

    return finalize(
        "failed",
        failure=_failure_record("SEMANTIC_FAIL", "exhausted semantic repair budget"),
        rule_ids=rule_ids,
    )

