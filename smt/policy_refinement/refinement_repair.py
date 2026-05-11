"""SAT, parse, and critic-driven repair after the implementer (v1)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from smt_pipeline.json_utils import extract_first_json_object
from smt_pipeline.models import CriticContext
from smt_pipeline.smt_parse import parse_smt2_string_check
from smt_pipeline.unsat_core import analyze_policy_sat_and_core, report_to_jsonable

from .config import RefinementConfig
from .llm_steps import build_repair_user_message, repair_formalizer_gemini


_REFINE_START = re.compile(r"^; --- REFINE rec_id=(\S+)", re.MULTILINE)


def extract_refine_regions_concat(policy_text: str) -> str:
    """All text from each REFINE marker through the next REFINE / bundle banner / EOF."""
    matches = list(_REFINE_START.finditer(policy_text))
    if not matches:
        return ""
    chunks: list[str] = []
    bundle_banner = re.compile(r"^; ={10,}\s*$", re.MULTILINE)
    for i, m in enumerate(matches):
        start = m.start()
        end = len(policy_text)
        if i + 1 < len(matches):
            end = min(end, matches[i + 1].start())
        for bm in bundle_banner.finditer(policy_text, pos=m.end()):
            end = min(end, bm.start())
            break
        chunks.append(policy_text[start:end].rstrip())
    return "\n\n".join(chunks)


def _log(path: Path, event: str, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rec = {
        "ts": datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "event": event,
        **data,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def run_repair_loop(
    *,
    policy_before: str,
    candidate: str,
    out_repair_log: Path,
    cfg: RefinementConfig,
    repair_fn: Optional[Callable[..., str]] = None,
    critic_fn: Optional[Callable[[CriticContext], dict[str, Any]]] = None,
    critic_raw_fn: Optional[Callable[[CriticContext], str]] = None,
) -> tuple[str, str, dict[str, Any]]:
    """
    Returns ``(final_policy, status, meta)`` where status is ``success`` or a failure token:
    ``PARSE_FAIL``, ``SAT_UNSAT``, ``SAT_UNKNOWN``, ``CRITIC_REJECTED``.
    """
    if repair_fn is None:

        def default_repair(
            *,
            full_policy: str,
            refine_regions: str = "",
            syntax_error: str | None = None,
            unsat_detail: str | None = None,
            objections_json: str | None = None,
        ) -> str:
            ut = build_repair_user_message(
                full_policy=full_policy,
                refine_regions=refine_regions,
                syntax_error=syntax_error,
                unsat_detail=unsat_detail,
                objections_json=objections_json,
            )
            return repair_formalizer_gemini(ut, cfg=cfg)

        repair_fn = default_repair

    from smt_pipeline.llm_steps import critic_json
    from smt_pipeline.config import SmtPipelineConfig

    smt_cfg = SmtPipelineConfig(
        parse_timeout_sec=cfg.parse_timeout_sec,
        critic_max_output_tokens=cfg.critic_max_output_tokens,
    )

    if critic_raw_fn is None:
        critic_raw_fn = lambda ctx: critic_json(ctx, cfg=smt_cfg)

    if critic_fn is None:

        def _critic(ctx: CriticContext) -> dict[str, Any]:
            raw = critic_raw_fn(ctx)
            return extract_first_json_object(raw)

        critic_fn = _critic

    text = candidate
    syntax_left = cfg.syntax_repair_cap
    semantic_left = cfg.semantic_repair_cap
    meta: dict[str, Any] = {"parse_repairs": 0, "semantic_repairs": 0, "unsat_repairs": 0}

    while True:
        ok, err = parse_smt2_string_check(text, timeout_sec=cfg.parse_timeout_sec)
        if not ok:
            _log(out_repair_log, "parse_fail", {"detail": err})
            if syntax_left <= 0:
                return text, "PARSE_FAIL", meta
            regions = extract_refine_regions_concat(text) or text[-8000:]
            text = repair_fn(
                full_policy=text,
                refine_regions=regions,
                syntax_error=err,
                unsat_detail=None,
                objections_json=None,
            )
            syntax_left -= 1
            meta["parse_repairs"] = meta.get("parse_repairs", 0) + 1
            continue

        sat = analyze_policy_sat_and_core(text)
        sat_j = report_to_jsonable(sat)
        _log(out_repair_log, "sat_check", sat_j)
        if sat.sat_result == "unknown":
            return text, "SAT_UNKNOWN", meta
        if sat.sat_result == "unsat":
            if syntax_left <= 0:
                return text, "SAT_UNSAT", meta
            regions = extract_refine_regions_concat(text) or text[-8000:]
            detail = json.dumps(sat_j, ensure_ascii=False)
            text = repair_fn(
                full_policy=text,
                refine_regions=regions,
                syntax_error=None,
                unsat_detail=detail,
                objections_json=None,
            )
            syntax_left -= 1
            meta["unsat_repairs"] = meta.get("unsat_repairs", 0) + 1
            continue

        regions = extract_refine_regions_concat(text)
        if not regions.strip():
            regions = "; (full proposed policy used for critic — no REFINE markers)\n" + text[-12000:]

        ctx = CriticContext(
            bundle_id="policy_refinement",
            proposed_smt2_block=regions,
            policy_path="policy_refinement.smt2",
            policy_text=policy_before,
            in_scope_wfm_summary="Policy refinement: proposed block(s) are REFINE-tagged edits; preserve NL alignment.",
        )
        try:
            verdict = critic_fn(ctx)
        except Exception as e:
            _log(out_repair_log, "critic_error", {"detail": str(e)})
            return text, "CRITIC_REJECTED", meta

        _log(out_repair_log, "critic_verdict", verdict)
        approved = bool(verdict.get("approved"))
        if approved:
            return text, "success", meta

        if semantic_left <= 0:
            return text, "CRITIC_REJECTED", meta
        objections_json = json.dumps(verdict.get("objections") or verdict, ensure_ascii=False)
        text = repair_fn(
            full_policy=text,
            refine_regions=extract_refine_regions_concat(text) or text[-8000:],
            syntax_error=None,
            unsat_detail=None,
            objections_json=objections_json,
        )
        semantic_left -= 1
        meta["semantic_repairs"] = meta.get("semantic_repairs", 0) + 1
