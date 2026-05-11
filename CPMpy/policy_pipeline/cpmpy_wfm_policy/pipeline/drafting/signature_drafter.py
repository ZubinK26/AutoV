"""Signature Drafter — Phase 0a (Sig_Agents signature_drafter.md)."""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from cpmpy_wfm_policy.json_utils import extract_first_json_object
from cpmpy_wfm_policy.llm import FormalizerLLM
from cpmpy_wfm_policy.pipeline.drafting.phase0_io import (
    call_llm_logged,
    load_phase0_system_prompt,
    retry_json_parse,
)
from cpmpy_wfm_policy.pipeline.drafting.phase0_models import SignatureDrafterOutput


def build_signature_drafter_user_message(
    *,
    rules_text: str,
    domain_notes: str | None = None,
    tools_json_fixed: str | None = None,
    reference_signature: str | None = None,
    structural_feedback: str | None = None,
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
        "REFERENCE SIGNATURE (FROM A PRIOR DOMAIN, FOR REFERENCE ONLY)",
        "=============================================================",
        (reference_signature.strip() if reference_signature else "(no seed reference; add files under llm/prompts/seed_signatures/)"),
        "",
        "EXISTING TOOLS.JSON (IF PROVIDED)",
        "=================================",
        (tools_json_fixed.strip() if tools_json_fixed else "(none — co-draft tools.json)"),
    ]
    if structural_feedback:
        parts.extend(
            [
                "",
                "STRUCTURAL SELF-CHECK FAILURES (FIX THESE)",
                "==========================================",
                structural_feedback.strip(),
            ]
        )
    parts.extend(
        [
            "",
            "INSTRUCTIONS",
            "============",
            "Produce the JSON output described in your system instructions. "
            "If tools.json was provided above, set co_drafted_tools to false and leave tools_json_content as an empty string.",
        ]
    )
    return "\n".join(parts)


def parse_signature_drafter_response(raw: str) -> SignatureDrafterOutput:
    data = extract_first_json_object(raw)
    return SignatureDrafterOutput.model_validate(data)


def run_signature_drafter_llm(
    llm: FormalizerLLM,
    *,
    log_path: Path,
    user_text: str,
    model_tag: str | None,
    max_json_retries: int,
) -> tuple[SignatureDrafterOutput, str]:
    system = load_phase0_system_prompt("signature_drafter.md")

    def _once() -> SignatureDrafterOutput:
        raw = call_llm_logged(
            llm,
            log_path=log_path,
            role="signature_drafter",
            system_instruction=system,
            user_text=user_text,
            model_tag=model_tag,
        )
        return parse_signature_drafter_response(raw)

    try:
        out = retry_json_parse(
            _once,
            max_attempts=max_json_retries,
            log_path=log_path,
            role="signature_drafter",
            on_fail_message="invalid Signature Drafter JSON",
        )
    except (ValidationError, ValueError) as e:
        raise ValueError(f"signature_drafter_validation: {e}") from e
    return out, ""
