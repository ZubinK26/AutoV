"""Diagnoser LLM: map formalizer/verify failures to repair hints (slice 3)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from cpmpy_wfm_policy.json_utils import extract_first_json_object

DiagnoserLLM = Callable[..., str]


@dataclass(frozen=True)
class Diagnosis:
    failure_class: str
    formalizer_hint: str


DEFAULT_DIAGNOSE_SYSTEM = """You classify failures in a CPMpy policy formalization pipeline.
Return exactly one JSON object with keys:
  "failure_class": one of formalizer_json, ast, cheap_check, unknown
  "formalizer_hint": short imperative English for the formalizer model to fix the rule module

No markdown fences."""


def load_diagnoser_repair_system_prompt(name: str = "diagnoser_repair_system.md") -> str:
    from pathlib import Path

    p = Path(__file__).resolve().parents[1] / "llm" / "prompts" / name
    if p.is_file():
        return p.read_text(encoding="utf-8")
    return DEFAULT_DIAGNOSE_SYSTEM


def diagnose_failure(
    *,
    raw_error: str,
    rule_nl: str,
    rule_index: int,
    llm: DiagnoserLLM,
    system_prompt: str | None = None,
) -> Diagnosis:
    system = system_prompt or load_diagnoser_repair_system_prompt()
    user = "\n".join(
        [
            f"rule_index: {rule_index}",
            f"nl_rule: {rule_nl}",
            f"error: {raw_error}",
        ]
    )
    raw = llm(system_instruction=system, user_text=user)
    try:
        data = extract_first_json_object(raw)
    except ValueError:
        return Diagnosis("unknown", f"Fix the rule. Previous error: {raw_error}")
    fc = str(data.get("failure_class") or "unknown")
    hint = str(data.get("formalizer_hint") or raw_error)
    return Diagnosis(fc, hint)
