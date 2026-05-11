"""Roundtrip: formal → NL (back-translate) → re-formal + equivalence (§5.3.1)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cpmpy as cp

from cpmpy_wfm_policy.json_utils import extract_first_json_object
from cpmpy_wfm_policy.llm import FormalizerLLM
from cpmpy_wfm_policy.pipeline.diagnoser_roundtrip import (
    RoundtripDiagnosis,
    diagnose_roundtrip_failure_llm,
    load_roundtrip_diagnoser_system_prompt,
)
from cpmpy_wfm_policy.pipeline.few_shot import extract_expression_from_rule_module
from cpmpy_wfm_policy.pipeline.formalizer import (
    FormalizerError,
    FormalizerOutput,
    formalize_one_rule,
    load_formalizer_system_prompt,
    materialize_rule_expression,
)


class RoundtripError(RuntimeError):
    """Back-translation or equivalence check failed."""


def _prompts_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "llm" / "prompts"


def load_back_translator_system_prompt(name: str = "back_translator_system.md") -> str:
    p = _prompts_dir() / name
    if not p.is_file():
        raise FileNotFoundError(f"missing back-translator prompt: {p}")
    return p.read_text(encoding="utf-8")


@dataclass(frozen=True)
class BackTranslationResult:
    sentence: str
    confidence: str
    ambiguity_notes: str


def build_back_translator_user_message(
    *,
    signature_py_text: str,
    glossary_md_text: str,
    rule_variable_name: str,
    expression_string: str,
) -> str:
    """Spec-compliant user message (original NL is intentionally omitted)."""
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
            "EXPRESSION TO BACK-TRANSLATE",
            "============================",
            f"Variable name: {rule_variable_name}",
            f"Expression: {expression_string}",
            "",
            "Produce the JSON output described in your instructions.",
        ]
    )


def parse_back_translator_json(raw: str) -> BackTranslationResult:
    data = extract_first_json_object(raw)
    bt = data.get("back_translation")
    if isinstance(bt, str) and bt.strip():
        return BackTranslationResult(
            sentence=bt.strip(),
            confidence=str(data.get("confidence", "medium")),
            ambiguity_notes=str(data.get("ambiguity_notes", "") or ""),
        )
    nl = data.get("nl_rule")
    if isinstance(nl, str) and nl.strip():
        return BackTranslationResult(nl.strip(), "medium", "")
    raise RoundtripError("back_translator must return back_translation or nl_rule string")


def expressions_equivalent(
    orig: Any,
    reform: Any,
    *,
    solver: str | None = None,
) -> bool:
    m = cp.Model([orig != reform])
    sat = m.solve(solver=solver)
    return not sat


@dataclass(frozen=True)
class RoundtripResult:
    equivalent: bool
    nl_roundtrip: str
    reform: FormalizerOutput | None
    detail: str
    back_translation: BackTranslationResult | None = None
    diagnosis: RoundtripDiagnosis | None = None


def run_roundtrip_one_rule(
    *,
    orig_out: FormalizerOutput,
    orig_expr: Any,
    nl_original: str,
    formalizer_llm: FormalizerLLM,
    back_translator_llm: FormalizerLLM,
    signature_path: str,
    glossary_path: str,
    tool_name: str = "apply_refund",
    system_formalizer: str | None = None,
    system_back_translator: str | None = None,
    roundtrip_solver: str | None = None,
    repair_hint: str | None = None,
    diagnoser_llm: FormalizerLLM | None = None,
    system_roundtrip_diagnoser: str | None = None,
    max_diagnose_cycles: int = 2,
    few_shot_examples_block: str | None = None,
) -> RoundtripResult:
    sig_text = Path(signature_path).read_text(encoding="utf-8")
    gloss_text = Path(glossary_path).read_text(encoding="utf-8")
    try:
        _, orig_expr_str = extract_expression_from_rule_module(orig_out.rule_module)
    except (ValueError, SyntaxError) as e:
        return RoundtripResult(False, "", None, f"extract_expression: {e}")

    sys_bt_base = system_back_translator or load_back_translator_system_prompt()
    extra_bt_suffix = ""
    diagnosis: RoundtripDiagnosis | None = None
    bt_res: BackTranslationResult | None = None

    for cycle in range(max(1, max_diagnose_cycles)):
        sys_bt = sys_bt_base + extra_bt_suffix
        bt_user = build_back_translator_user_message(
            signature_py_text=sig_text,
            glossary_md_text=gloss_text,
            rule_variable_name=orig_out.rule_name,
            expression_string=orig_expr_str,
        )
        raw_bt = back_translator_llm(system_instruction=sys_bt, user_text=bt_user)
        try:
            bt_res = parse_back_translator_json(raw_bt)
        except (ValueError, RoundtripError) as e:
            return RoundtripResult(False, "", None, f"back_translate_parse: {e}")

        try:
            reform_out = formalize_one_rule(
                nl_rule=bt_res.sentence,
                rule_index=orig_out.rule_index,
                signature_path=signature_path,
                glossary_path=glossary_path,
                llm=formalizer_llm,
                tool_name=tool_name,
                system_prompt=system_formalizer or load_formalizer_system_prompt(),
                repair_hint=repair_hint,
                few_shot_examples_block=few_shot_examples_block,
            )
        except FormalizerError as e:
            return RoundtripResult(
                False,
                bt_res.sentence,
                None,
                f"reformalize: {e}",
                back_translation=bt_res,
                diagnosis=diagnosis,
            )

        reform_expr = materialize_rule_expression(reform_out, signature_path)
        if expressions_equivalent(orig_expr, reform_expr, solver=roundtrip_solver):
            return RoundtripResult(
                True,
                bt_res.sentence,
                reform_out,
                "ok",
                back_translation=bt_res,
                diagnosis=diagnosis,
            )

        last_detail = "equivalence: SAT on (orig != reform)"
        try:
            _, reform_str = extract_expression_from_rule_module(reform_out.rule_module)
        except (ValueError, SyntaxError):
            reform_str = ""

        if diagnoser_llm is None or cycle >= max_diagnose_cycles - 1:
            return RoundtripResult(
                False,
                bt_res.sentence,
                reform_out,
                last_detail,
                back_translation=bt_res,
                diagnosis=diagnosis,
            )

        try:
            diagnosis = diagnose_roundtrip_failure_llm(
                llm=diagnoser_llm,
                signature_py_text=sig_text,
                glossary_md_text=gloss_text,
                original_nl_text=nl_original,
                rule_variable_name=orig_out.rule_name,
                original_expression_string=orig_expr_str,
                back_translation_nl=bt_res.sentence,
                back_translation_confidence=bt_res.confidence,
                back_translation_ambiguity_notes=bt_res.ambiguity_notes,
                reformalized_expression_string=reform_str,
                system_prompt=system_roundtrip_diagnoser
                or load_roundtrip_diagnoser_system_prompt(),
            )
        except Exception as e:
            return RoundtripResult(
                False,
                bt_res.sentence,
                reform_out,
                f"{last_detail}; diagnoser_error: {e}",
                back_translation=bt_res,
                diagnosis=None,
            )

        if diagnosis.repair_strategy == "REGENERATE_BACK_TRANSLATION":
            extra_bt_suffix = (
                "\nPrior attempt was imprecise. Preserve strict > vs >=, "
                "exact numeric thresholds, and logical structure verbatim.\n"
            )
            continue
        if diagnosis.repair_strategy == "ACCEPT_ORIGINAL":
            return RoundtripResult(
                True,
                bt_res.sentence,
                reform_out,
                "advisory_accept_original",
                back_translation=bt_res,
                diagnosis=diagnosis,
            )
        return RoundtripResult(
            False,
            bt_res.sentence,
            reform_out,
            f"{last_detail}; diagnosis={diagnosis.category}",
            back_translation=bt_res,
            diagnosis=diagnosis,
        )

    return RoundtripResult(
        False,
        bt_res.sentence if bt_res else "",
        None,
        "roundtrip_exhausted",
        back_translation=bt_res,
        diagnosis=diagnosis,
    )


def diagnose_roundtrip_failure(
    *,
    detail: str,
    nl_original: str,
    nl_roundtrip: str,
    llm: FormalizerLLM | None,
    system_prompt: str | None = None,
) -> str:
    if llm is None:
        return detail
    sys = system_prompt or (
        "Classify roundtrip failure. Return JSON "
        '{"failure_kind":"ambiguity|drift|unknown","hint":"<short explanation>"}'
    )
    user = "\n".join(
        [
            f"detail: {detail}",
            f"original_nl: {nl_original}",
            f"roundtrip_nl: {nl_roundtrip}",
        ]
    )
    raw = llm(system_instruction=sys, user_text=user)
    try:
        data = extract_first_json_object(raw)
        kind = data.get("failure_kind", "unknown")
        hint = data.get("hint", "")
        return f"{detail}; diagnosed={kind}: {hint}"
    except ValueError:
        return detail
