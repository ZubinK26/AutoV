"""Phase 0a + 0b orchestrator (04_signature_glossary_workflow)."""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cpmpy_wfm_policy.llm import FormalizerLLM
from cpmpy_wfm_policy.pipeline.drafting.critic_motivation import validate_critique_motivations
from cpmpy_wfm_policy.pipeline.drafting.glossary_drafter import (
    build_glossary_drafter_user_message,
    run_glossary_drafter_llm,
)
from cpmpy_wfm_policy.pipeline.drafting.human_review_gate import (
    load_workflow_state,
    save_workflow_state,
)
from cpmpy_wfm_policy.pipeline.drafting.phase0_models import critique_finding_count
from cpmpy_wfm_policy.pipeline.drafting.phase0_seed_bank import (
    load_seed_reference_glossary_text,
    load_seed_reference_signature_text,
)
from cpmpy_wfm_policy.pipeline.drafting.signature_critic import (
    build_signature_critic_user_message,
    critique_to_json,
    run_signature_critic_llm,
)
from cpmpy_wfm_policy.pipeline.drafting.signature_drafter import (
    build_signature_drafter_user_message,
    run_signature_drafter_llm,
)
from cpmpy_wfm_policy.pipeline.drafting.signature_refiner import (
    build_signature_refiner_user_message,
    run_signature_refiner_llm,
)
from cpmpy_wfm_policy.pipeline.drafting.structural_check_glossary import (
    check_glossary_structure,
    required_glossary_symbols_from_signature,
)
from cpmpy_wfm_policy.pipeline.drafting.structural_check_signature import (
    check_signature_structure,
)


@dataclass
class Phase0Config:
    max_structural_retries: int = 3
    max_llm_json_retries: int = 3
    skip_human: bool = False
    model_tag: str | None = None
    rerun_phase_0a: bool = False
    max_critic_motivation_retries: int = 2


@dataclass
class Phase0Result:
    success: bool
    error: str | None = None
    domain_dir: Path | None = None
    phase_0a_complete: bool = False
    phase_0b_complete: bool = False


def _log_phase(domain_dir: Path, event: str, payload: dict[str, Any]) -> None:
    append_jsonl(
        domain_dir / "signature_draft_log.jsonl",
        {"event": event, **payload},
    )


def _check_sig_with_tools(
    signature_py: str,
    *,
    tools_provided: bool,
    tools_object: dict[str, Any] | None,
    domain_dir: Path,
) -> tuple[Any, Path | None]:
    """Return (report, temp_tools_path or None). Caller unlinks temp if set."""
    tmp: Path | None = None
    tpath: Path | None = None
    if tools_provided:
        tpath = domain_dir / "tools.json"
    elif tools_object is not None:
        tf = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
            encoding="utf-8",
        )
        json.dump(tools_object, tf)
        tf.flush()
        tf.close()
        tmp = Path(tf.name)
        tpath = tmp
    require_align = tools_provided or tools_object is not None
    rep = check_signature_structure(
        signature_py,
        tools_json_path=tpath,
        require_tools_json_alignment=require_align,
    )
    return rep, tmp


def run_phase0(
    domain_dir: Path,
    *,
    llm: FormalizerLLM,
    cfg: Phase0Config | None = None,
) -> Phase0Result:
    cfg = cfg or Phase0Config()
    ddir = Path(domain_dir).resolve()
    rules_path = ddir / "rules.txt"
    if not rules_path.is_file():
        return Phase0Result(False, f"missing {rules_path}", ddir)

    rules_text = rules_path.read_text(encoding="utf-8")
    notes_path = ddir / "domain_notes.md"
    domain_notes = notes_path.read_text(encoding="utf-8") if notes_path.is_file() else None
    tools_path = ddir / "tools.json"
    tools_provided = tools_path.is_file()
    tools_fixed_text = tools_path.read_text(encoding="utf-8") if tools_provided else None
    seed_sig = load_seed_reference_signature_text()
    seed_glossary = load_seed_reference_glossary_text()

    st_pre = load_workflow_state(ddir)
    skip_0a_llm = (
        not cfg.rerun_phase_0a
        and st_pre.phase_0a_approved
        and (ddir / "signature.py").is_file()
        and (ddir / "refiner_decisions.json").is_file()
    )

    log_0a = ddir / "signature_draft_log.jsonl"
    if not skip_0a_llm:
        if log_0a.is_file():
            log_0a.unlink()

        drafter_out = None
        feedback: str | None = None
        for attempt in range(max(1, cfg.max_structural_retries)):
            um = build_signature_drafter_user_message(
                rules_text=rules_text,
                domain_notes=domain_notes,
                tools_json_fixed=tools_fixed_text,
                reference_signature=seed_sig or None,
                structural_feedback=feedback,
            )
            try:
                drafter_out, _ = run_signature_drafter_llm(
                    llm,
                    log_path=log_0a,
                    user_text=um,
                    model_tag=cfg.model_tag,
                    max_json_retries=cfg.max_llm_json_retries,
                )
            except ValueError as e:
                _log_phase(ddir, "drafter_failed", {"attempt": attempt, "error": str(e)})
                return Phase0Result(False, str(e), ddir)

            if not tools_provided:
                if drafter_out.tools_json is None:
                    return Phase0Result(
                        False,
                        "co-drafted tools.json missing from drafter output (workflow §4.2)",
                        ddir,
                    )

            rep, tmp = _check_sig_with_tools(
                drafter_out.signature_py,
                tools_provided=tools_provided,
                tools_object=drafter_out.tools_json if not tools_provided else None,
                domain_dir=ddir,
            )
            if tmp and tmp.is_file():
                tmp.unlink(missing_ok=True)

            if rep.pass_:
                break
            feedback = json.dumps(rep.to_jsonable(), indent=2)
            _log_phase(
                ddir, "drafter_structural_fail", {"attempt": attempt, "report": rep.to_jsonable()}
            )
        else:
            return Phase0Result(
                False,
                "Phase 0a: drafter structural retries exhausted",
                ddir,
            )

        assert drafter_out is not None
        draft_sig = drafter_out.signature_py
        draft_tools_obj = drafter_out.tools_json
        co_drafted = not tools_provided

        tools_json_for_critic = (
            tools_fixed_text
            if tools_provided
            else json.dumps(draft_tools_obj or {}, indent=2)
        )

        motivation_feedback: str | None = None
        critique = None
        for cm in range(max(1, cfg.max_critic_motivation_retries)):
            try:
                critique = run_signature_critic_llm(
                    llm,
                    log_path=log_0a,
                    user_text=build_signature_critic_user_message(
                        rules_text=rules_text,
                        domain_notes=domain_notes,
                        signature_py=draft_sig,
                        tools_json_text=tools_json_for_critic,
                        co_drafted_by_drafter=co_drafted,
                        rationale=dict(drafter_out.rationale),
                        bound_confidence=dict(drafter_out.bound_confidence),
                        enum_completeness=dict(drafter_out.enum_completeness),
                        drafter_notes=drafter_out.drafter_notes,
                        motivation_rejection_feedback=motivation_feedback,
                    ),
                    model_tag=cfg.model_tag,
                    max_json_retries=cfg.max_llm_json_retries,
                )
            except ValueError as e:
                return Phase0Result(False, str(e), ddir)

            mot_errs = validate_critique_motivations(
                critique.model_dump(),
                rules_text=rules_text,
                domain_notes=domain_notes,
            )
            if not mot_errs:
                break
            motivation_feedback = "\n".join(mot_errs)
            _log_phase(
                ddir,
                "critic_motivation_rejected",
                {"attempt": cm, "errors": mot_errs},
            )
        else:
            return Phase0Result(
                False,
                f"Phase 0a: critic motivating_rule_text validation failed after "
                f"{cfg.max_critic_motivation_retries} attempt(s): {motivation_feedback}",
                ddir,
            )

        assert critique is not None
        critique_text = critique_to_json(critique)
        n_critique_findings = critique_finding_count(critique)

        refined_sig = draft_sig
        refined_tools: dict[str, Any] | None = draft_tools_obj if not tools_provided else None
        tools_json_for_refiner = tools_json_for_critic
        ref_feedback: str | None = None
        ref_decision_feedback: str | None = None
        ref_out = None
        for attempt in range(max(1, cfg.max_structural_retries)):
            combo_fb = "\n\n".join(x for x in (ref_feedback, ref_decision_feedback) if x) or None
            rum = build_signature_refiner_user_message(
                rules_text=rules_text,
                domain_notes=domain_notes,
                draft_signature_py=refined_sig,
                tools_json_text=tools_json_for_refiner,
                co_drafted_by_drafter=co_drafted,
                rationale=dict(drafter_out.rationale),
                bound_confidence=dict(drafter_out.bound_confidence),
                enum_completeness=dict(drafter_out.enum_completeness),
                critique_json=critique_text,
                structural_feedback=combo_fb,
                tools_json_fixed=tools_provided,
            )
            try:
                ref_out = run_signature_refiner_llm(
                    llm,
                    log_path=log_0a,
                    user_text=rum,
                    model_tag=cfg.model_tag,
                    max_json_retries=cfg.max_llm_json_retries,
                )
            except ValueError as e:
                _log_phase(ddir, "refiner_failed", {"attempt": attempt, "error": str(e)})
                return Phase0Result(False, str(e), ddir)

            if len(ref_out.decisions) != n_critique_findings:
                ref_decision_feedback = (
                    f"Refiner output must include exactly one decisions[] entry per Critic finding. "
                    f"Expected {n_critique_findings} entries (sum across all critique categories), "
                    f"got {len(ref_out.decisions)}. List missing or extra decisions without changing "
                    f"the signature until the count matches."
                )
                _log_phase(
                    ddir,
                    "refiner_decision_count_mismatch",
                    {
                        "attempt": attempt,
                        "expected": n_critique_findings,
                        "got": len(ref_out.decisions),
                    },
                )
                continue

            ref_decision_feedback = None
            refined_sig = ref_out.signature_py
            if not tools_provided and ref_out.tools_json is not None:
                refined_tools = ref_out.tools_json
                tools_json_for_refiner = json.dumps(refined_tools, indent=2)

            rep, tmp2 = _check_sig_with_tools(
                refined_sig,
                tools_provided=tools_provided,
                tools_object=refined_tools if not tools_provided else None,
                domain_dir=ddir,
            )
            if tmp2 and tmp2.is_file():
                tmp2.unlink(missing_ok=True)

            if rep.pass_:
                (ddir / "signature_check_report.json").write_text(
                    json.dumps(rep.to_jsonable(), indent=2),
                    encoding="utf-8",
                )
                break
            ref_feedback = json.dumps(rep.to_jsonable(), indent=2)
            _log_phase(
                ddir,
                "refiner_structural_fail",
                {"attempt": attempt, "report": rep.to_jsonable()},
            )
        else:
            return Phase0Result(
                False,
                "Phase 0a: refiner structural retries exhausted",
                ddir,
            )

        assert ref_out is not None
        rat_bundle = drafter_out.rationale_bundle_for_disk()
        rer_art = ref_out.artifact_for_disk()
        if any(
            [
                ref_out.rationale,
                ref_out.bound_confidence,
                ref_out.enum_completeness,
                ref_out.decisions,
                ref_out.spontaneous_corrections,
            ]
        ):
            rat_bundle["refiner_artifact"] = rer_art
        (ddir / "signature.py").write_text(refined_sig, encoding="utf-8")
        if not tools_provided and refined_tools is not None:
            (ddir / "tools.json").write_text(json.dumps(refined_tools, indent=2), encoding="utf-8")
        (ddir / "signature_rationale.json").write_text(
            json.dumps(rat_bundle, indent=2),
            encoding="utf-8",
        )
        (ddir / "refiner_decisions.json").write_text(
            json.dumps(rer_art, indent=2),
            encoding="utf-8",
        )
    else:
        append_jsonl(
            log_0a,
            {
                "event": "phase0_resume",
                "skipped": "phase0a_llm",
                "reason": "workflow_state phase_0a_approved and artifacts present",
            },
        )

    st = load_workflow_state(ddir)
    if cfg.skip_human:
        st.phase_0a_approved = True
        save_workflow_state(ddir, st)
    elif not st.phase_0a_approved:
        return Phase0Result(
            False,
            "Phase 0a artifacts written; set workflow_state.json phase_0a_approved=true after human review, then re-run.",
            ddir,
            phase_0a_complete=True,
        )

    sig_final = (ddir / "signature.py").read_text(encoding="utf-8")
    rationale_path = ddir / "signature_rationale.json"
    rationale_blob: dict[str, Any] = {}
    if rationale_path.is_file():
        try:
            rationale_blob = json.loads(rationale_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            rationale_blob = {}
    rationale_json_str = json.dumps(rationale_blob, indent=2) if rationale_blob else "{}"

    glog = ddir / "glossary_draft_log.jsonl"
    if glog.is_file():
        glog.unlink()

    g_feedback: str | None = None
    req_syms = required_glossary_symbols_from_signature(sig_final)
    for attempt in range(max(1, cfg.max_structural_retries)):
        gum = build_glossary_drafter_user_message(
            signature_py=sig_final,
            rules_text=rules_text,
            domain_notes=domain_notes,
            rationale_json=rationale_json_str,
            reference_glossary=seed_glossary or None,
            structural_feedback=g_feedback,
        )
        try:
            g_out = run_glossary_drafter_llm(
                llm,
                log_path=glog,
                user_text=gum,
                model_tag=cfg.model_tag,
                max_json_retries=cfg.max_llm_json_retries,
            )
        except ValueError as e:
            return Phase0Result(False, str(e), ddir, phase_0a_complete=True)

        grep = check_glossary_structure(
            g_out.glossary_yaml,
            required_symbols=req_syms,
            rules_text=rules_text,
            domain_notes=domain_notes,
            inferred_phrase_symbols=frozenset(g_out.entries_with_inferred_phrases or ()),
        )
        if grep.pass_:
            (ddir / "glossary.md").write_text(g_out.glossary_yaml.strip() + "\n", encoding="utf-8")
            break
        g_feedback = json.dumps(grep.to_jsonable(), indent=2)
        append_jsonl(
            glog,
            {"event": "glossary_structural_fail", "attempt": attempt, "report": grep.to_jsonable()},
        )
    else:
        return Phase0Result(
            False,
            "Phase 0b: glossary structural retries exhausted",
            ddir,
            phase_0a_complete=True,
        )

    st = load_workflow_state(ddir)
    if cfg.skip_human:
        st.phase_0b_approved = True
        save_workflow_state(ddir, st)
    elif not st.phase_0b_approved:
        return Phase0Result(
            False,
            "Phase 0b glossary written; set phase_0b_approved=true in workflow_state.json after review.",
            ddir,
            phase_0a_complete=True,
            phase_0b_complete=False,
        )

    return Phase0Result(True, None, ddir, phase_0a_complete=True, phase_0b_complete=True)
