"""Glossary Drafter — Phase 0b (Sig_Agents glossary_drafter.md)."""

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
from cpmpy_wfm_policy.pipeline.drafting.phase0_models import GlossaryDrafterOutput


def build_glossary_drafter_user_message(
    *,
    signature_py: str,
    rules_text: str,
    domain_notes: str | None = None,
    rationale_json: str | None = None,
    reference_glossary: str | None = None,
    structural_feedback: str | None = None,
) -> str:
    dn = domain_notes.strip() if domain_notes else ""
    parts = [
        "FINALIZED SIGNATURE",
        "===================",
        signature_py.strip(),
        "",
        "RULES",
        "=====",
        rules_text.strip(),
        "",
        "DOMAIN NOTES",
        "============",
        dn if dn else "(none provided)",
        "",
        "SIGNATURE RATIONALE (FROM PHASE 0A)",
        "===================================",
        (rationale_json.strip() if rationale_json else "{}"),
    ]
    if reference_glossary:
        parts.extend(
            [
                "",
                "REFERENCE GLOSSARY (PRIOR VALIDATED DOMAIN — STYLE ONLY)",
                "=========================================================",
                reference_glossary.strip(),
            ]
        )
    if structural_feedback:
        parts.extend(
            [
                "",
                "GLOSSARY STRUCTURAL / GROUNDING FAILURES",
                "=======================================",
                structural_feedback.strip(),
            ]
        )
    parts.extend(
        [
            "",
            "INSTRUCTIONS",
            "============",
            "Produce the JSON output described in your system instructions. "
            "Populate entries_with_inferred_phrases for any symbol where rules+notes lack "
            "two verbatim phrases — only those entries are exempt from phrase substring checks.",
        ]
    )
    return "\n".join(parts)


def parse_glossary_drafter_response(raw: str) -> GlossaryDrafterOutput:
    data = extract_first_json_object(raw)
    return GlossaryDrafterOutput.model_validate(data)


def run_glossary_drafter_llm(
    llm: FormalizerLLM,
    *,
    log_path: Path,
    user_text: str,
    model_tag: str | None,
    max_json_retries: int,
) -> GlossaryDrafterOutput:
    system = load_phase0_system_prompt("glossary_drafter.md")

    def _once() -> GlossaryDrafterOutput:
        raw = call_llm_logged(
            llm,
            log_path=log_path,
            role="glossary_drafter",
            system_instruction=system,
            user_text=user_text,
            model_tag=model_tag,
        )
        return parse_glossary_drafter_response(raw)

    try:
        return retry_json_parse(
            _once,
            max_attempts=max_json_retries,
            log_path=log_path,
            role="glossary_drafter",
            on_fail_message="invalid Glossary Drafter JSON",
        )
    except (ValidationError, ValueError) as e:
        raise ValueError(f"glossary_drafter_validation: {e}") from e
