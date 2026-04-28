"""WFM handoff -> ClinCon / Clingo policy commit (`docs/pipeline_wfm_to_asp.md`)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from registry_stage.loaders import parse_handoff_bundle
from registry_stage.models import handoff_bundle_to_dict
from smt_pipeline.commit import atomic_write_text
from smt_pipeline.ids import new_bundle_id, new_rule_id
from smt_pipeline.json_utils import extract_first_json_object

from asp_pipeline.clingo_check import check_ground, check_parse_and_ground, check_parse_only, strip_lp_fences
from asp_pipeline.config import AspPipelineConfig, asp_config_from_env
from asp_pipeline.llm_steps import formalizer_prompt_fingerprint
from asp_pipeline.models import AspCriticContext, AspFormalizerContext, AspPipelineRunResult
from asp_pipeline.rule_count import rule_count as lp_rule_count


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _log_line(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _is_in_scope(verdict: str) -> bool:
    return (verdict or "").strip() != "OUT_OF_SCOPE"


def _load_handoff_json(path: Path) -> Any:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and (not data.get("bundle_id")):
        data["bundle_id"] = new_bundle_id()
    return data


def _failure_record(category: str, detail: str) -> dict[str, Any]:
    return {"category": category, "detail": detail}


def _context_size_bytes(policy_text: str, handoff_dict: dict[str, Any]) -> int:
    return len(policy_text.encode("utf-8")) + len(json.dumps(handoff_dict, ensure_ascii=False).encode("utf-8"))


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
    formalizer_prompt: str,
    formalizer_prompt_sha256: str,
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
        "pipeline_kind": "asp_clincon",
        "formalizer_prompt": formalizer_prompt,
        "formalizer_prompt_sha256": formalizer_prompt_sha256,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _validate_existing_lp(existing: str, cfg: AspPipelineConfig) -> tuple[bool, str]:
    if not existing.strip():
        return True, ""
    ok, err = check_parse_only(existing, timeout_sec=cfg.clingo_parse_timeout_sec)
    if not ok:
        return False, err
    okg, errg = check_ground(
        existing,
        "",
        timeout_sec=cfg.clingo_ground_timeout_sec,
    )
    if not okg:
        return False, errg
    return True, ""


def _critic_approved(c: dict[str, Any]) -> bool:
    if not bool(c.get("approved")):
        return False
    for v in c.get("verdicts") or []:
        if isinstance(v, dict) and v.get("approved") is False:
            return False
    return True


def _critic_feedback_text(c: dict[str, Any]) -> str:
    oi = (c.get("overall_issue") or "").strip()
    rest = json.dumps(
        {
            "verdicts": c.get("verdicts", []),
            "overall_issue": c.get("overall_issue", ""),
        },
        ensure_ascii=False,
    )
    return f"semantic_critic_json:\n{rest}\n" + (f"summary: {oi}\n" if oi else "")


def _commit_asp(
    policy_model_path: Path,
    existing: str,
    new_block: str,
    bundle_id: str,
) -> str:
    committed_iso = _utc_now_iso()
    head = (new_block or "").lstrip()[:500]
    if "% Bundle:" in head:
        block_out = new_block
    else:
        block_out = (
            f"% ============================================================\n"
            f"% Bundle: {bundle_id}  |  Committed: {committed_iso}\n"
            f"% ============================================================\n"
            f"{new_block or ''}"
        )
    if existing.strip():
        full = existing.rstrip() + "\n\n" + block_out
    else:
        full = block_out
    atomic_write_text(policy_model_path, full)
    return committed_iso


def run_asp_pipeline(
    *,
    handoff_path: Path,
    policy_model_path: Path,
    bundle_out_dir: Path,
    cfg: Optional[AspPipelineConfig] = None,
    formalizer_fn: Optional[Callable[[AspFormalizerContext], str]] = None,
    critic_fn: Optional[Callable[[AspCriticContext], dict[str, Any]]] = None,
) -> AspPipelineRunResult:
    """
    Steps 1-6: load handoff, context guard, formalizer, parse+ground, critic, commit.
    Injected callables (tests) default to None -> Gemini.
    """
    cfg = cfg or asp_config_from_env()
    accepted_at = _utc_now_iso()

    raw = _load_handoff_json(handoff_path)
    handoff_dict = raw if isinstance(raw, dict) else {}
    bundle = parse_handoff_bundle(raw)
    bundle_id = bundle.bundle_id
    bundle_json_path = bundle_out_dir / f"{bundle_id}.json"
    log_path = bundle_out_dir / f"{bundle_id}.log.jsonl"

    wfm_payload = handoff_bundle_to_dict(bundle)
    out_indices = [ln.line_index for ln in bundle.lines if not _is_in_scope(ln.agent3_verdict)]
    in_scope_struct = [ln for ln in bundle.lines if _is_in_scope(ln.agent3_verdict)]
    in_scope_sorted = sorted(in_scope_struct, key=lambda x: x.line_index)

    try:
        fp_name, fp_sha = formalizer_prompt_fingerprint(cfg)
    except (OSError, ValueError) as e:
        _write_bundle_json(
            bundle_json_path,
            bundle_id=bundle_id,
            accepted_at=accepted_at,
            committed_at=None,
            pipeline_status="failed",
            rule_ids=[],
            out_of_scope_line_indices=out_indices,
            wfm_payload=wfm_payload,
            failure_reason=_failure_record("FORMALIZER_PROMPT", str(e)),
            policy_model_path=str(policy_model_path),
            formalizer_prompt=(cfg.formalizer_prompt or "formalizer_new.md").strip() or "formalizer_new.md",
            formalizer_prompt_sha256="",
        )
        return AspPipelineRunResult(
            bundle_id=bundle_id,
            policy_model_path=str(policy_model_path),
            bundle_record_path=str(bundle_json_path.resolve()),
            log_path=str(log_path.resolve()),
            status="failed",
            failure_reason="FORMALIZER_PROMPT",
            rule_ids=[],
        )

    policy_path_str = str(policy_model_path)
    existing = ""
    if policy_model_path.is_file():
        existing = policy_model_path.read_text(encoding="utf-8")

    if formalizer_fn is None:

        def _form_impl(ctx: AspFormalizerContext) -> str:
            from asp_pipeline.llm_steps import formalizer_lp_gemini

            return formalizer_lp_gemini(ctx, cfg=cfg)

        formalizer_fn = _form_impl

    if critic_fn is None:

        def _crit_impl(ctx: AspCriticContext) -> dict[str, Any]:
            from asp_pipeline.llm_steps import critic_json_gemini

            raw_t = critic_json_gemini(ctx, cfg=cfg)
            return extract_first_json_object(raw_t)

        critic_fn = _crit_impl

    def finalize(
        status: str,
        *,
        failure: Optional[dict[str, Any]] = None,
        committed_at: Optional[str] = None,
        rule_ids: Optional[list[str]] = None,
    ) -> AspPipelineRunResult:
        st = "committed" if status == "success" else "failed"
        _write_bundle_json(
            bundle_json_path,
            bundle_id=bundle_id,
            accepted_at=accepted_at,
            committed_at=committed_at,
            pipeline_status=st,
            rule_ids=rule_ids or [],
            out_of_scope_line_indices=out_indices,
            wfm_payload=wfm_payload,
            failure_reason=failure,
            policy_model_path=policy_path_str,
            formalizer_prompt=fp_name,
            formalizer_prompt_sha256=fp_sha,
        )
        return AspPipelineRunResult(
            bundle_id=bundle_id,
            policy_model_path=policy_path_str,
            bundle_record_path=str(bundle_json_path.resolve()),
            log_path=str(log_path.resolve()),
            status="success" if status == "success" else "failed",
            failure_reason=failure["category"] if failure else None,
            rule_ids=rule_ids or [],
        )

    if _context_size_bytes(existing, handoff_dict) > cfg.context_char_limit:
        return finalize(
            "failed",
            failure=_failure_record("CONTEXT_LIMIT_EXCEEDED", "handoff + policy exceeds context limit"),
        )

    if existing.strip():
        ok_e, emsg = _validate_existing_lp(existing, cfg)
        if not ok_e:
            return finalize("failed", failure=_failure_record("POLICY_MODEL_CORRUPT", emsg))

    n_existing = lp_rule_count(existing)
    if n_existing + len(in_scope_sorted) > cfg.rule_cap and in_scope_sorted:
        pre = [new_rule_id() for _ in in_scope_sorted]
        return finalize(
            "failed",
            failure=_failure_record(
                "SIZE_CAP_REACHED",
                f"current_rules={n_existing} in_scope_lines={len(in_scope_sorted)} cap={cfg.rule_cap}",
            ),
            rule_ids=pre,
        )

    if not in_scope_sorted:
        return finalize("success", committed_at=_utc_now_iso(), rule_ids=[])

    rule_ids: list[str] = [new_rule_id() for _ in in_scope_sorted]
    in_scope_text_lines: list[str] = []
    for rid, ln in zip(rule_ids, in_scope_sorted, strict=True):
        in_scope_text_lines.append(
            f"rule_id={rid} line_index={ln.line_index} "
            f"statement_nl={json.dumps(ln.statement_nl, ensure_ascii=False)}"
        )
    wfm_summary = "\n".join(in_scope_text_lines)

    def _check_block(block: str) -> tuple[bool, str, str]:
        b = block.strip()
        if not b:
            return False, "parse", "empty formalizer output"
        return check_parse_and_ground(
            existing,
            b,
            parse_timeout_sec=cfg.clingo_parse_timeout_sec,
            ground_timeout_sec=cfg.clingo_ground_timeout_sec,
        )

    # --- loop 1: parse + ground ---
    block = ""
    loop1_left = cfg.parse_ground_repair_cap
    parse_fb: Optional[str] = None
    prev_b: Optional[str] = None

    while loop1_left > 0:
        att = cfg.parse_ground_repair_cap - loop1_left + 1
        repair_fb: Optional[str] = None
        if parse_fb is not None:
            repair_fb = f"REPAIR (parse/ground check failed):\n{parse_fb}\n"
        ctx = AspFormalizerContext(
            bundle_id=bundle_id,
            policy_path=policy_path_str,
            policy_text=existing,
            existing_rule_count=n_existing,
            in_scope_lines=in_scope_text_lines,
            attempt_index=att,
            feedback=repair_fb,
            previous_lp_block=prev_b,
        )
        try:
            raw_out = formalizer_fn(ctx)
            block = strip_lp_fences(raw_out).strip()
        except Exception as e:
            block = ""
            exc = f"formalizer_exception: {e}"
            _log_line(
                log_path,
                {
                    "bundle_id": bundle_id,
                    "timestamp": _utc_now_iso(),
                    "loop": "parse_ground",
                    "iteration": att,
                    "formalizer_output_lp": "",
                    "check_result": "fail",
                    "check_detail": exc,
                },
            )
            parse_fb = exc
            loop1_left -= 1
            if loop1_left == 0:
                return finalize("failed", failure=_failure_record("PARSE_GROUND_FAIL", exc), rule_ids=rule_ids)
            prev_b = block or prev_b
            continue

        ok_pg, stg, errdet = _check_block(block)
        _log_line(
            log_path,
            {
                "bundle_id": bundle_id,
                "timestamp": _utc_now_iso(),
                "loop": "parse_ground",
                "iteration": att,
                "formalizer_output_lp": block[:12000] + ("..." if len(block) > 12000 else ""),
                "check_result": "pass" if ok_pg else "fail",
                "check_detail": errdet if not ok_pg else "",
            },
        )
        if ok_pg:
            break
        loop1_left -= 1
        prev_b = block
        parse_fb = f"[{stg}] {errdet}"
        if loop1_left == 0:
            return finalize(
                "failed",
                failure=_failure_record("PARSE_GROUND_FAIL", f"{stg}: {errdet}"),
                rule_ids=rule_ids,
            )

    cctx0 = AspCriticContext(
        bundle_id=bundle_id,
        proposed_lp_block=block,
        policy_path=policy_path_str,
        policy_text=existing,
        in_scope_wfm_summary=wfm_summary,
    )
    try:
        cr0 = critic_fn(cctx0)
    except Exception as e:
        return finalize("failed", failure=_failure_record("CRITIC_FAIL", f"critic_exception: {e}"), rule_ids=rule_ids)

    if _critic_approved(cr0):
        com = _commit_asp(policy_model_path, existing, block, bundle_id)
        return finalize("success", committed_at=com, rule_ids=rule_ids)

    objections = _critic_feedback_text(cr0)
    loop2_left = cfg.semantic_repair_cap
    prev_sem = block
    parse_err: Optional[str] = None
    if loop2_left == 0:
        return finalize("failed", failure=_failure_record("CRITIC_FAIL", objections), rule_ids=rule_ids)

    while loop2_left > 0:
        sem = cfg.semantic_repair_cap - loop2_left + 1
        fb = objections if not parse_err else f"{objections}\n\nparse_ground_error:\n{parse_err}"
        ctx2 = AspFormalizerContext(
            bundle_id=bundle_id,
            policy_path=policy_path_str,
            policy_text=existing,
            existing_rule_count=n_existing,
            in_scope_lines=in_scope_text_lines,
            attempt_index=cfg.parse_ground_repair_cap + sem,
            feedback=fb,
            previous_lp_block=prev_sem,
        )
        try:
            raw2 = formalizer_fn(ctx2)
            block = strip_lp_fences(raw2).strip()
        except Exception as e:
            block = ""
            parse_err = f"formalizer_exception: {e}"
            _log_line(
                log_path,
                {
                    "bundle_id": bundle_id,
                    "timestamp": _utc_now_iso(),
                    "loop": "semantic",
                    "iteration": sem,
                    "formalizer_output_lp": "",
                    "check_result": "fail",
                    "check_detail": parse_err,
                },
            )
            loop2_left -= 1
            if loop2_left == 0:
                return finalize("failed", failure=_failure_record("CRITIC_FAIL", parse_err), rule_ids=rule_ids)
            continue

        prev_sem = block
        ok_pg, stg, errdet = _check_block(block)
        _log_line(
            log_path,
            {
                "bundle_id": bundle_id,
                "timestamp": _utc_now_iso(),
                "loop": "semantic",
                "iteration": sem,
                "formalizer_output_lp": block[:12000] + ("..." if len(block) > 12000 else ""),
                "check_result": "pass" if ok_pg else "fail",
                "check_detail": errdet if not ok_pg else "",
            },
        )
        if not ok_pg:
            parse_err = f"{stg}: {errdet}"
            loop2_left -= 1
            if loop2_left == 0:
                return finalize("failed", failure=_failure_record("CRITIC_FAIL", parse_err), rule_ids=rule_ids)
            continue
        parse_err = None

        try:
            crn = critic_fn(
                AspCriticContext(
                    bundle_id=bundle_id,
                    proposed_lp_block=block,
                    policy_path=policy_path_str,
                    policy_text=existing,
                    in_scope_wfm_summary=wfm_summary,
                )
            )
        except Exception as e:
            loop2_left -= 1
            if loop2_left == 0:
                return finalize("failed", failure=_failure_record("CRITIC_FAIL", f"critic_exception: {e}"), rule_ids=rule_ids)
            objections = f"critic_exception: {e}"
            continue

        if _critic_approved(crn):
            com = _commit_asp(policy_model_path, existing, block, bundle_id)
            return finalize("success", committed_at=com, rule_ids=rule_ids)

        objections = _critic_feedback_text(crn)
        loop2_left -= 1
        if loop2_left == 0:
            return finalize("failed", failure=_failure_record("CRITIC_FAIL", objections), rule_ids=rule_ids)

    return finalize("failed", failure=_failure_record("CRITIC_FAIL", "exhausted semantic repair budget"), rule_ids=rule_ids)
