"""Signature Refiner — Phase 0a (Sig_Agents signature_refiner.md)."""

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
from cpmpy_wfm_policy.pipeline.drafting.phase0_models import SignatureRefinerLLMOutput


def build_signature_refiner_user_message(
    *,
    rules_text: str,
    domain_notes: str | None,
    draft_signature_py: str,
    tools_json_text: str,
    co_drafted_by_drafter: bool,
    rationale: dict,
    bound_confidence: dict,
    enum_completeness: dict,
    critique_json: str,
    structural_feedback: str | None = None,
    tools_json_fixed: bool,
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
        draft_signature_py.strip(),
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
        "CRITIC'S STRUCTURED CRITIQUE",
        "============================",
        critique_json.strip(),
    ]
    if tools_json_fixed:
        parts.append(
            "\nIMPORTANT: tools.json was user-provided and FIXED. Do not change tool names/parameters; "
            "only fix the signature (and tools content only if co_drafted_by_drafter is true)."
        )
    if structural_feedback:
        parts.extend(
            [
                "",
                "STRUCTURAL SELF-CHECK FAILURES (MUST PASS AFTER YOUR EDIT)",
                "==========================================================",
                structural_feedback.strip(),
            ]
        )
    parts.extend(
        [
            "",
            "INSTRUCTIONS",
            "============",
            "Produce the JSON output described in your system instructions. "
            "Include one decisions[] entry per Critic finding across all categories, in section order.",
        ]
    )
    return "\n".join(parts)


def parse_signature_refiner_response(raw: str) -> SignatureRefinerLLMOutput:
    data = extract_first_json_object(raw)
    return SignatureRefinerLLMOutput.model_validate(data)


def run_signature_refiner_llm(
    llm: FormalizerLLM,
    *,
    log_path: Path,
    user_text: str,
    model_tag: str | None,
    max_json_retries: int,
) -> SignatureRefinerLLMOutput:
    system = load_phase0_system_prompt("signature_refiner.md")

    def _once() -> SignatureRefinerLLMOutput:
        raw = call_llm_logged(
            llm,
            log_path=log_path,
            role="signature_refiner",
            system_instruction=system,
            user_text=user_text,
            model_tag=model_tag,
        )
        return parse_signature_refiner_response(raw)

    try:
        return retry_json_parse(
            _once,
            max_attempts=max_json_retries,
            log_path=log_path,
            role="signature_refiner",
            on_fail_message="invalid Signature Refiner JSON",
        )
    except (ValidationError, ValueError) as e:
        raise ValueError(f"signature_refiner_validation: {e}") from e
