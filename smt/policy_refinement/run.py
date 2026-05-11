"""Orchestrate assessor → implementer → repair (policy refinement v1)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal, Optional

from smt_pipeline.json_utils import extract_first_json_object

from .config import RefinementConfig, refinement_config_from_env
from .llm_steps import (
    assessor_gemini,
    build_assessor_user_message,
    build_implementer_user_message,
    implementer_gemini,
    maybe_truncate_for_assessor,
)
from .nl_digest import build_numbered_digest
from .refinement_repair import run_repair_loop
from .validate import (
    validate_assessment,
    validate_assessor_policy_refs,
    validate_implementation,
)


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


@dataclass
class RefinementRunResult:
    status: Literal["success", "failed"]
    failure_reason: Optional[str] = None
    out_dir: Path = field(default_factory=Path)
    artifact_paths: dict[str, str] = field(default_factory=dict)


def run_assess_and_refine(
    *,
    policy_path: Path,
    nl_path: Path,
    out_dir: Path,
    run_id: Optional[str] = None,
    skip_assessor: bool = False,
    assessment_path: Optional[Path] = None,
    cfg: Optional[RefinementConfig] = None,
    assessor_fn: Optional[Callable[[str], str]] = None,
    implementer_fn: Optional[Callable[[str], str]] = None,
    repair_fn: Optional[Callable[..., str]] = None,
    critic_fn: Optional[Callable[..., Any]] = None,
    critic_raw_fn: Optional[Callable[..., str]] = None,
) -> RefinementRunResult:
    """
    End-to-end refinement run. Writes artifacts under ``out_dir``.
    Injected ``*_fn`` callables accept user_message str (assessor/implementer) or repair kwargs.
    """
    cfg = cfg or refinement_config_from_env()
    policy_path = policy_path.resolve()
    nl_path = nl_path.resolve()
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    rid = run_id or f"refine_{_utc_stamp()}"

    policy_text = policy_path.read_text(encoding="utf-8")
    nl_source = nl_path.read_text(encoding="utf-8")
    nl_digest = build_numbered_digest(nl_source)
    policy_sha = _sha256_text(policy_text)
    nl_sha = _sha256_text(nl_source)

    manifest = {
        "schema_version": "policy_refinement_run_manifest_v1",
        "run_id": rid,
        "policy_path": str(policy_path),
        "nl_path": str(nl_path),
        "policy_sha256_before": policy_sha,
        "nl_sha256": nl_sha,
        "started_at_utc": datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (out_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    def fail(reason: str) -> RefinementRunResult:
        report = {
            "run_id": rid,
            "status": "failed",
            "failure_reason": reason,
            "policy_model_sha256_before": policy_sha,
        }
        (out_dir / "final_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return RefinementRunResult(
            status="failed",
            failure_reason=reason,
            out_dir=out_dir,
            artifact_paths={"final_report": str(out_dir / "final_report.json")},
        )

    # --- Assessor ---
    if skip_assessor:
        ap = assessment_path or (out_dir / "assessment.json")
        if not ap.is_file():
            return fail("skip_assessor_but_no_assessment_file")
        assessment = json.loads(ap.read_text(encoding="utf-8"))
    else:
        if assessor_fn is None:
            assessor_fn = lambda ut: assessor_gemini(ut, cfg=cfg)  # type: ignore[assignment]
        pol_for_assessor = maybe_truncate_for_assessor(
            nl_source=nl_source,
            nl_digest=nl_digest,
            policy_text=policy_text,
            limit=cfg.assessor_context_char_limit,
        )
        user_a = build_assessor_user_message(
            nl_source=nl_source,
            nl_digest=nl_digest,
            policy_text=pol_for_assessor,
            run_id=rid,
        )
        raw_a = assessor_fn(user_a)
        try:
            assessment = extract_first_json_object(raw_a)
        except Exception:
            nudge = user_a + "\n\nYour previous reply was not valid JSON. Output exactly one JSON object. No markdown."
            raw_a2 = assessor_fn(nudge)
            try:
                assessment = extract_first_json_object(raw_a2)
            except Exception as e:
                return fail(f"ASSESSOR_MALFORMED:{e}")

        assessment.setdefault("nl_source_sha256", nl_sha)
        assessment.setdefault("policy_model_sha256_before", policy_sha)
        assessment.setdefault("run_id", rid)
        (out_dir / "assessment.json").write_text(
            json.dumps(assessment, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    errs = validate_assessment(assessment, max_recommendations=cfg.max_recommendations)
    if errs:
        return fail("ASSESSOR_SCHEMA:" + "; ".join(errs))

    warn_refs = validate_assessor_policy_refs(assessment, policy_text)
    if warn_refs:
        assessment["_validation_warnings"] = warn_refs
        (out_dir / "assessment.json").write_text(
            json.dumps(assessment, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    if assessment.get("no_changes_needed"):
        (out_dir / "policy_refined.smt2").write_text(policy_text, encoding="utf-8")
        report = {
            "run_id": rid,
            "status": "success",
            "no_changes_needed": True,
            "critic_final_approved": True,
            "sat_result": "skipped",
            "paths": {"policy_refined": str(out_dir / "policy_refined.smt2")},
        }
        (out_dir / "final_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return RefinementRunResult(
            status="success",
            out_dir=out_dir,
            artifact_paths={k: str(v) for k, v in report["paths"].items()},
        )

    recs = assessment.get("recommendations") or []
    if not recs:
        (out_dir / "policy_refined.smt2").write_text(policy_text, encoding="utf-8")
        report = {
            "run_id": rid,
            "status": "success",
            "empty_recommendations": True,
            "critic_final_approved": True,
            "paths": {"policy_refined": str(out_dir / "policy_refined.smt2")},
        }
        (out_dir / "final_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return RefinementRunResult(status="success", out_dir=out_dir, artifact_paths={})

    allowed = {str(r["rec_id"]) for r in recs if isinstance(r, dict) and r.get("rec_id")}
    impl_request = {
        "recommendations": recs,
        "summary": assessment.get("summary"),
        "assessor_run_id": assessment.get("run_id"),
    }
    (out_dir / "implementation_request.json").write_text(
        json.dumps(impl_request, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    if implementer_fn is None:
        implementer_fn = lambda ut: implementer_gemini(ut, cfg=cfg)  # type: ignore[assignment]

    nl_excerpt = nl_source if len(nl_source) <= 14_000 else nl_source[:14_000] + "\n# [truncated]\n"
    user_i = build_implementer_user_message(
        recommendations_json=json.dumps(recs, ensure_ascii=False),
        policy_text=policy_text,
        nl_excerpt=nl_excerpt,
    )
    raw_i = implementer_fn(user_i)
    try:
        impl = extract_first_json_object(raw_i)
    except Exception:
        raw_i2 = implementer_fn(user_i + "\n\nOutput must be one JSON object with policy_smt2_full_text. No markdown.")
        try:
            impl = extract_first_json_object(raw_i2)
        except Exception as e:
            return fail(f"IMPLEMENTER_MALFORMED:{e}")

    cand = impl.get("policy_smt2_full_text") or ""
    i_errs = validate_implementation(
        impl,
        allowed_rec_ids=allowed,
        policy_text=cand,
    )
    if i_errs:
        return fail("IMPLEMENTER_SCHEMA:" + "; ".join(i_errs))

    addr = impl.get("rec_ids_addressed") or []
    if not addr:
        (out_dir / "policy_before.smt2").write_text(policy_text, encoding="utf-8")
        (out_dir / "implementation_response.json").write_text(
            json.dumps(impl, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (out_dir / "policy_refined.smt2").write_text(policy_text, encoding="utf-8")
        report = {
            "run_id": rid,
            "status": "success",
            "note": "implementer addressed no rec_ids; policy unchanged",
            "paths": {"policy_refined": str(out_dir / "policy_refined.smt2")},
        }
        (out_dir / "final_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return RefinementRunResult(status="success", out_dir=out_dir, artifact_paths={})

    (out_dir / "policy_before.smt2").write_text(policy_text, encoding="utf-8")
    (out_dir / "implementation_response.json").write_text(
        json.dumps(impl, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (out_dir / "policy_implementer_raw.smt2").write_text(cand, encoding="utf-8")

    repair_log = out_dir / "repair_log.jsonl"
    if repair_log.is_file():
        repair_log.unlink()

    final, status, meta = run_repair_loop(
        policy_before=policy_text,
        candidate=cand,
        out_repair_log=repair_log,
        cfg=cfg,
        repair_fn=repair_fn,
        critic_fn=critic_fn,
        critic_raw_fn=critic_raw_fn,
    )

    if status != "success":
        (out_dir / "policy_refined_failed.smt2").write_text(final, encoding="utf-8")
        report = {
            "run_id": rid,
            "status": "failed",
            "failure_reason": status,
            "repair_meta": meta,
            "paths": {
                "policy_refined_failed": str(out_dir / "policy_refined_failed.smt2"),
                "repair_log": str(repair_log),
            },
        }
        (out_dir / "final_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return RefinementRunResult(
            status="failed",
            failure_reason=status,
            out_dir=out_dir,
            artifact_paths={k: str(v) for k, v in report["paths"].items()},
        )

    (out_dir / "policy_refined.smt2").write_text(final, encoding="utf-8")
    sat_report = None
    try:
        from smt_pipeline.unsat_core import analyze_policy_sat_and_core, report_to_jsonable

        sat_report = report_to_jsonable(analyze_policy_sat_and_core(final))
    except Exception:
        pass

    report = {
        "run_id": rid,
        "status": "success",
        "failure_reason": None,
        "critic_final_approved": True,
        "sat_result": (sat_report or {}).get("sat_result"),
        "repair_meta": meta,
        "paths": {
            "policy_refined": str(out_dir / "policy_refined.smt2"),
            "repair_log": str(repair_log),
            "policy_before": str(out_dir / "policy_before.smt2"),
        },
    }
    (out_dir / "final_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return RefinementRunResult(
        status="success",
        out_dir=out_dir,
        artifact_paths={k: str(v) for k, v in report["paths"].items()},
    )
