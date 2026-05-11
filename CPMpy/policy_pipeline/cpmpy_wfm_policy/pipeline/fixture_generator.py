"""Optional LLM draft fixture generation (Project_Spec_Agents test_case_generator)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from cpmpy_wfm_policy.json_utils import extract_first_json_object
from cpmpy_wfm_policy.llm import FormalizerLLM


class _FixtureItem(BaseModel):
    label: str = ""
    state: dict[str, Any]
    expected: bool


class FixtureGeneratorOutput(BaseModel):
    fixtures: list[_FixtureItem] = Field(default_factory=list)
    coverage_notes: str = ""
    skipped_aspects: str = ""


def load_test_case_generator_system_prompt(
    name: str = "test_case_generator_system.md",
) -> str:
    p = Path(__file__).resolve().parents[1] / "llm" / "prompts" / name
    if not p.is_file():
        raise FileNotFoundError(f"missing test-case generator prompt: {p}")
    return p.read_text(encoding="utf-8")


def build_fixture_generator_user_message(
    *,
    signature_py_text: str,
    glossary_md_text: str,
    original_nl_text: str,
    rule_variable_name: str,
    expression_string: str,
    used_symbols_list: list[str],
    target_fixture_count: int,
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
            "RULE",
            "====",
            f"NL: {original_nl_text}",
            f"Variable name: {rule_variable_name}",
            f"Expression: {expression_string}",
            f"Symbols used: {used_symbols_list}",
            "",
            "TARGET",
            "======",
            f"Produce {target_fixture_count} fixtures.",
            "",
            "Produce the JSON output described in your instructions.",
        ]
    )


def generate_fixtures_via_llm(
    *,
    llm: FormalizerLLM,
    signature_path: str,
    glossary_path: str,
    original_nl_text: str,
    rule_variable_name: str,
    expression_string: str,
    used_symbols: list[str],
    target_fixture_count: int = 6,
    system_prompt: str | None = None,
) -> FixtureGeneratorOutput:
    sig = Path(signature_path).read_text(encoding="utf-8")
    gloss = Path(glossary_path).read_text(encoding="utf-8")
    sys = system_prompt or load_test_case_generator_system_prompt()
    user = build_fixture_generator_user_message(
        signature_py_text=sig,
        glossary_md_text=gloss,
        original_nl_text=original_nl_text,
        rule_variable_name=rule_variable_name,
        expression_string=expression_string,
        used_symbols_list=sorted(used_symbols),
        target_fixture_count=target_fixture_count,
    )
    raw = llm(system_instruction=sys, user_text=user)
    data = extract_first_json_object(raw)
    return FixtureGeneratorOutput.model_validate(data)


def write_per_rule_py_draft(
    *,
    rule_name: str,
    output: FixtureGeneratorOutput,
    dest: Path,
) -> None:
    """Write a human-reviewable draft (not executed by the orchestrator)."""
    tuples: list[tuple[dict[str, Any], bool]] = [
        (f.state, f.expected) for f in output.fixtures
    ]
    body = (
        "# draft fixtures — human review required before promoting to per_rule.py\n"
        f"DRAFT_METADATA = {json.dumps(output.model_dump(), indent=2, ensure_ascii=False)}\n\n"
        "PER_RULE_FIXTURES_DRAFT = {\n"
        f"    {rule_name!r}: [\n"
    )
    for state, exp in tuples:
        body += f"        ({state!r}, {exp!r}),\n"
    body += "    ],\n}\n"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(body, encoding="utf-8")
