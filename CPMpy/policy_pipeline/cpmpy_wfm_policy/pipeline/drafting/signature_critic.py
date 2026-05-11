"""Signature Critic — Phase 0a (Sig_Agents signature_critic.md)."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from cpmpy_wfm_policy.json_utils import extract_first_json_object
from cpmpy_wfm_policy.llm import FormalizerLLM
from cpmpy_wfm_policy.pipeline.drafting.phase0_io import (
    call_llm_logged,
    load_phase0_system_prompt,
    retry_json_parse,
)
from cpmpy_wfm_policy.pipeline.drafting.phase0_models import SignatureCritique


def build_signature_critic_user_message(
    *,
    rules_text: str,
    domain_notes: str | None,
    signature_py: str,
    tools_json_text: str,
    co_drafted_by_drafter: bool,
    rationale: dict,
    bound_confidence: dict,
    enum_completeness: dict,
    drafter_notes: str,
    motivation_rejection_feedback: str | None = None,
) -> str:
    dn = domain_notes.strip() if domain_notes else ""
    parts = [
        "RULES",
        "=====",
        rules_text.strip(),
        "",
        "DOMAIN NOTES",
        "============",
        dn if dn else "(none provided)",
        "",
        "DRAFT SIGNATURE",
        "===============",
        signature_py.strip(),
        "",
        "DRAFT TOOLS.JSON",
        "================",
        tools_json_text.strip(),
        f"co_drafted_by_drafter: {str(co_drafted_by_drafter).lower()}",
        "",
        "DRAFTER RATIONALE",
        "=================",
        json.dumps(rationale, indent=2),
        "",
        "DRAFTER BOUND CONFIDENCE FLAGS",
        "==============================",
        json.dumps(bound_confidence, indent=2),
        "",
        "DRAFTER ENUM COMPLETENESS FLAGS",
        "===============================",
        json.dumps(enum_completeness, indent=2),
        "",
        "DRAFTER NOTES",
        "=============",
        drafter_notes.strip() if drafter_notes else "(none)",
    ]
    if motivation_rejection_feedback:
        parts.extend(
            [
                "",
                "CORRECTION REQUIRED",
                "==================",
                motivation_rejection_feedback.strip(),
            ]
        )
    parts.extend(
        [
            "",
            "INSTRUCTIONS",
            "============",
            "Produce the JSON critique described in your system instructions. "
            "Every motivating_rule_text in missing_fields, suspicious_bounds, and incomplete_enums "
            "must quote or closely paraphrase text that actually appears in RULES or DOMAIN NOTES above.",
        ]
    )
    return "\n".join(parts)


def parse_signature_critic_response(raw: str) -> SignatureCritique:
    data = extract_first_json_object(raw)
    return SignatureCritique.model_validate(data)


def run_signature_critic_llm(
    llm: FormalizerLLM,
    *,
    log_path: Path,
    user_text: str,
    model_tag: str | None,
    max_json_retries: int,
) -> SignatureCritique:
    system = load_phase0_system_prompt("signature_critic.md")

    def _once() -> SignatureCritique:
        raw = call_llm_logged(
            llm,
            log_path=log_path,
            role="signature_critic",
            system_instruction=system,
            user_text=user_text,
            model_tag=model_tag,
        )
        return parse_signature_critic_response(raw)

    try:
        return retry_json_parse(
            _once,
            max_attempts=max_json_retries,
            log_path=log_path,
            role="signature_critic",
            on_fail_message="invalid Signature Critic JSON",
        )
    except (ValidationError, ValueError) as e:
        raise ValueError(f"signature_critic_validation: {e}") from e


def critique_to_json(critique: SignatureCritique) -> str:
    return json.dumps(critique.model_dump(), indent=2)
