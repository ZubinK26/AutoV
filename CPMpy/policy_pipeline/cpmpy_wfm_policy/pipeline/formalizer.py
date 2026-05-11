"""
Formalizer: one NL line → validated rule module (Project_Spec_Agents + slice 2 legacy).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from cpmpy_wfm_policy.json_utils import extract_first_json_object
from cpmpy_wfm_policy.llm import FormalizerLLM
from cpmpy_wfm_policy.llm.formalizer_response import normalize_formalizer_llm_dict
from cpmpy_wfm_policy.pipeline.ast_validator import (
    ASTValidationError,
    RuleMetadata,
    load_signature_namespace,
    validate_rule_ast,
)
from cpmpy_wfm_policy.pipeline.few_shot import compose_few_shot_block


class FormalizerError(RuntimeError):
    """Malformed LLM output or validation failure."""


@dataclass(frozen=True)
class FormalizerOutput:
    rule_index: int
    rule_name: str
    rule_module: str
    used_symbols: frozenset[str]
    uses_global_constraints: bool
    uses_vector_variables: bool
    raw_response: str
    claimed_dependencies: frozenset[str] = field(default_factory=frozenset)


def _prompts_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "llm" / "prompts"


def load_formalizer_system_prompt(name: str = "formalizer_system.md") -> str:
    """Prefer Project_Spec_Agents-style prompt; fall back to legacy slice-2 file."""
    p = _prompts_dir() / name
    if not p.is_file():
        legacy = _prompts_dir() / "formalizer_slice2.md"
        if legacy.is_file():
            return legacy.read_text(encoding="utf-8")
        raise FileNotFoundError(f"missing formalizer prompt: {p}")
    return p.read_text(encoding="utf-8")


def build_formalizer_user_message(
    *,
    nl_rule: str,
    rule_index: int,
    tool_name: str,
    signature_py_text: str,
    glossary_md_text: str,
    few_shot_examples_block: str,
    repair_hint: str | None = None,
) -> str:
    rule_variable_name = f"rule_{rule_index}"
    parts: list[str] = [
        "SIGNATURE",
        "=========",
        signature_py_text,
        "",
        "GLOSSARY",
        "========",
        glossary_md_text,
        "",
        "FEW-SHOT EXAMPLES",
        "=================",
        few_shot_examples_block.rstrip(),
        "",
        "CURRENT RULE",
        "============",
        f"Tool scope: {tool_name}",
        f"Variable name to assign to: {rule_variable_name}",
        f"NL rule: {nl_rule.strip()}",
        "",
        "Produce the JSON output described in your instructions.",
    ]
    if repair_hint:
        parts.extend(["", "REPAIR HINT", "===========", repair_hint.strip(), ""])
    return "\n".join(parts)


def parse_formalizer_json(raw: str) -> dict[str, Any]:
    try:
        return extract_first_json_object(raw)
    except ValueError as e:
        raise FormalizerError(f"invalid_json: {e}") from e


def formalize_one_rule(
    *,
    nl_rule: str,
    rule_index: int,
    signature_path: str,
    glossary_path: str,
    llm: FormalizerLLM,
    tool_name: str = "apply_refund",
    system_prompt: str | None = None,
    repair_hint: str | None = None,
    few_shot_examples_block: str | None = None,
    max_llm_json_retries: int = 3,
    log_event: Any | None = None,
) -> FormalizerOutput:
    sig_text = Path(signature_path).read_text(encoding="utf-8")
    gloss_text = Path(glossary_path).read_text(encoding="utf-8")
    system = system_prompt or load_formalizer_system_prompt()
    if few_shot_examples_block is None:
        few_shot_examples_block = compose_few_shot_block(
            rule_index=rule_index, prior_outputs=[], prior_nl_lines=[]
        )
    user = build_formalizer_user_message(
        nl_rule=nl_rule,
        rule_index=rule_index,
        tool_name=tool_name,
        signature_py_text=sig_text,
        glossary_md_text=gloss_text,
        few_shot_examples_block=few_shot_examples_block,
        repair_hint=repair_hint,
    )

    last_err: Exception | None = None
    raw = ""
    for j_attempt in range(max(1, max_llm_json_retries)):
        t0 = time.perf_counter()
        raw = llm(system_instruction=system, user_text=user)
        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        if log_event is not None:
            log_event(
                "llm_call",
                role="formalizer",
                rule_index=rule_index,
                attempt=j_attempt,
                latency_ms=latency_ms,
            )
        try:
            data = parse_formalizer_json(raw)
            norm = normalize_formalizer_llm_dict(data)
            break
        except FormalizerError as fe:
            if str(fe).startswith("out_of_scope:"):
                raise
            last_err = fe
            if j_attempt >= max_llm_json_retries - 1:
                raise FormalizerError(
                    f"formalizer_json_retries_exhausted ({max_llm_json_retries}): {fe}"
                ) from fe
        except ValueError as ve:
            if str(ve).startswith("out_of_scope:"):
                raise FormalizerError(str(ve)) from ve
            last_err = ve
            if j_attempt >= max_llm_json_retries - 1:
                raise FormalizerError(
                    f"formalizer_json_retries_exhausted ({max_llm_json_retries}): {ve}"
                ) from ve
        except ValidationError as ve:
            last_err = ve
            if j_attempt >= max_llm_json_retries - 1:
                raise FormalizerError(
                    f"formalizer_json_retries_exhausted ({max_llm_json_retries}): {ve}"
                ) from ve

    try:
        rule_module = norm["rule_module"]
        used = norm["used_symbols"]
        ug = norm["uses_global_constraints"]
        uv = norm["uses_vector_variables"]
        claimed = norm.get("claimed_dependencies", frozenset())
    except (KeyError, TypeError) as e:
        raise FormalizerError(f"missing_json_fields: {e}") from e

    meta = RuleMetadata(
        used_symbols=used,
        uses_global_constraints=ug,
        uses_vector_variables=uv,
    )
    sig_ns = load_signature_namespace(signature_path)
    try:
        rule_name, _ = validate_rule_ast(rule_module, signature_namespace=sig_ns, metadata=meta)
    except ASTValidationError as e:
        raise FormalizerError(f"ast_validation: {e}") from e
    idx_from_name = int(rule_name.split("_", 1)[1])
    if idx_from_name != rule_index:
        raise FormalizerError(f"rule name {rule_name!r} must match rule_index {rule_index}")

    return FormalizerOutput(
        rule_index=rule_index,
        rule_name=rule_name,
        rule_module=rule_module,
        used_symbols=used,
        uses_global_constraints=ug,
        uses_vector_variables=uv,
        raw_response=raw,
        claimed_dependencies=claimed if isinstance(claimed, frozenset) else frozenset(claimed),
    )


def formalize_rules_file(
    *,
    rules_txt_path: str,
    signature_path: str,
    glossary_path: str,
    llm: FormalizerLLM,
    tool_name: str = "apply_refund",
    system_prompt: str | None = None,
    repair_hints_by_index: dict[int, str] | None = None,
) -> list[FormalizerOutput]:
    """Formalize each non-empty, non-# line in ``rules.txt`` as ``rule_1`` … ``rule_n``."""
    raw_lines = Path(rules_txt_path).read_text(encoding="utf-8").splitlines()
    lines = [ln.strip() for ln in raw_lines if ln.strip() and not ln.strip().startswith("#")]
    out: list[FormalizerOutput] = []
    hints = repair_hints_by_index or {}
    prior_nl: list[str] = []
    for i, nl in enumerate(lines, start=1):
        fs = compose_few_shot_block(rule_index=i, prior_outputs=out, prior_nl_lines=prior_nl)
        out.append(
            formalize_one_rule(
                nl_rule=nl,
                rule_index=i,
                signature_path=signature_path,
                glossary_path=glossary_path,
                llm=llm,
                tool_name=tool_name,
                system_prompt=system_prompt,
                repair_hint=hints.get(i),
                max_llm_json_retries=3,
                few_shot_examples_block=fs,
            )
        )
        prior_nl.append(nl)
    return out


def materialize_rule_expression(
    formalizer_output: FormalizerOutput,
    signature_path: str,
) -> Any:
    """Exec validated module in a copy of the signature namespace; return CPMpy expr."""
    sig_ns = load_signature_namespace(signature_path)
    ns = dict(sig_ns)
    try:
        exec(compile(formalizer_output.rule_module, "<rule_module>", "exec"), ns, ns)
    except Exception as e:
        raise FormalizerError(f"exec_failed: {e}") from e
    if formalizer_output.rule_name not in ns:
        raise FormalizerError(f"missing {formalizer_output.rule_name!r} after exec")
    return ns[formalizer_output.rule_name]
