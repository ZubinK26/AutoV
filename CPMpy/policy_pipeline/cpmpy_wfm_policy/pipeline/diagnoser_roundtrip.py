"""Round-trip failure diagnosis (Project_Spec_Agents `diagnoser.md`)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from cpmpy_wfm_policy.json_utils import extract_first_json_object
from cpmpy_wfm_policy.llm import FormalizerLLM


class RoundtripDiagnosisModel(BaseModel):
    category: Literal[
        "ORIGINAL_FORMALIZATION_DRIFT",
        "BACK_TRANSLATION_DRIFT",
        "REFORMALIZATION_DRIFT",
        "AMBIGUOUS_NL",
        "CONFLATED_FAILURE",
    ]
    repair_strategy: Literal[
        "REGENERATE_ORIGINAL",
        "REGENERATE_BACK_TRANSLATION",
        "ACCEPT_ORIGINAL",
        "ESCALATE_TO_HUMAN",
    ]
    confidence: Literal["high", "medium", "low"] = "medium"
    reasoning: str = ""
    specific_divergence: str = ""
    human_review_notes: str = Field(default="")


@dataclass(frozen=True)
class RoundtripDiagnosis:
    category: str
    repair_strategy: str
    confidence: str
    reasoning: str
    specific_divergence: str
    human_review_notes: str
    raw_response: str


def _prompts_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "llm" / "prompts"


def load_roundtrip_diagnoser_system_prompt(name: str = "diagnoser_roundtrip_system.md") -> str:
    p = _prompts_dir() / name
    if not p.is_file():
        raise FileNotFoundError(f"missing roundtrip diagnoser prompt: {p}")
    return p.read_text(encoding="utf-8")


def build_roundtrip_diagnoser_user_message(
    *,
    signature_py_text: str,
    glossary_md_text: str,
    original_nl_text: str,
    rule_variable_name: str,
    original_expression_string: str,
    back_translation_nl: str,
    back_translation_confidence: str,
    back_translation_ambiguity_notes: str,
    reformalized_expression_string: str,
) -> str:
    return "\n".join(
        [
            "SIGNATURE",
            "=========",
            signature_py_text,
            "",
            "GLOSSARY",
            "========",
            glossary_md_text,
            "",
            "ORIGINAL NL RULE",
            "================",
            original_nl_text.strip(),
            "",
            "ORIGINAL FORMAL EXPRESSION",
            "==========================",
            f"Variable name: {rule_variable_name}",
            f"Expression: {original_expression_string}",
            "",
            "BACK-TRANSLATION",
            "================",
            f"NL: {back_translation_nl}",
            f"Confidence: {back_translation_confidence}",
            f"Ambiguity notes: {back_translation_ambiguity_notes}",
            "",
            "RE-FORMALIZED EXPRESSION",
            "========================",
            f"Expression: {reformalized_expression_string}",
            "",
            "EQUIVALENCE CHECK RESULT",
            "========================",
            "Status: NOT_EQUIVALENT (this has been verified by SAT)",
            "",
            "Produce the JSON output described in your instructions.",
        ]
    )


def diagnose_roundtrip_failure_llm(
    *,
    llm: FormalizerLLM,
    signature_py_text: str,
    glossary_md_text: str,
    original_nl_text: str,
    rule_variable_name: str,
    original_expression_string: str,
    back_translation_nl: str,
    back_translation_confidence: str,
    back_translation_ambiguity_notes: str,
    reformalized_expression_string: str,
    system_prompt: str | None = None,
) -> RoundtripDiagnosis:
    sys = system_prompt or load_roundtrip_diagnoser_system_prompt()
    user = build_roundtrip_diagnoser_user_message(
        signature_py_text=signature_py_text,
        glossary_md_text=glossary_md_text,
        original_nl_text=original_nl_text,
        rule_variable_name=rule_variable_name,
        original_expression_string=original_expression_string,
        back_translation_nl=back_translation_nl,
        back_translation_confidence=back_translation_confidence,
        back_translation_ambiguity_notes=back_translation_ambiguity_notes,
        reformalized_expression_string=reformalized_expression_string,
    )
    raw = llm(system_instruction=sys, user_text=user)
    data = extract_first_json_object(raw)
    m = RoundtripDiagnosisModel.model_validate(data)
    return RoundtripDiagnosis(
        category=m.category,
        repair_strategy=m.repair_strategy,
        confidence=m.confidence,
        reasoning=m.reasoning,
        specific_divergence=m.specific_divergence,
        human_review_notes=m.human_review_notes,
        raw_response=raw,
    )
