"""ASP / ClinCon pipeline config (`docs/pipeline_wfm_to_asp.md` §9)."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AspPipelineConfig:
    parse_ground_repair_cap: int = 5
    semantic_repair_cap: int = 3
    rule_cap: int = 50
    clingo_parse_timeout_sec: float = 10.0
    clingo_ground_timeout_sec: float = 30.0
    context_char_limit: int = 900_000
    formalizer_max_output_tokens: int = 16_384
    critic_max_output_tokens: int = 8_192
    #: Basename only; file must live in ``asp_pipeline/prompts/``. Default is the ClinCon prompt validated on
    #: SymTex (parse/ground + critic) with ``policy_check``-style review; override with
    #: ``ASP_PIPELINE_FORMALIZER_PROMPT=formalizer.md`` for the previous template.
    formalizer_prompt: str = "formalizer_new.md"


def asp_config_from_env() -> AspPipelineConfig:
    def _i(name: str, default: int) -> int:
        raw = os.environ.get(name, "").strip()
        return int(raw) if raw else default

    def _f(name: str, default: float) -> float:
        raw = os.environ.get(name, "").strip()
        return float(raw) if raw else default

    _fp = os.environ.get("ASP_PIPELINE_FORMALIZER_PROMPT", "").strip()
    formalizer_prompt = _fp or "formalizer_new.md"
    return AspPipelineConfig(
        parse_ground_repair_cap=_i("ASP_PIPELINE_PARSE_GROUND_REPAIR_CAP", 5),
        semantic_repair_cap=_i("ASP_PIPELINE_SEMANTIC_REPAIR_CAP", 3),
        rule_cap=_i("ASP_PIPELINE_RULE_CAP", 50),
        clingo_parse_timeout_sec=_f("ASP_PIPELINE_CLINGO_PARSE_TIMEOUT", 10.0),
        clingo_ground_timeout_sec=_f("ASP_PIPELINE_CLINGO_GROUND_TIMEOUT", 30.0),
        context_char_limit=_i("ASP_PIPELINE_CONTEXT_CHAR_LIMIT", 900_000),
        formalizer_max_output_tokens=_i("ASP_PIPELINE_FORMALIZER_MAX_OUTPUT_TOKENS", 16384),
        critic_max_output_tokens=_i("ASP_PIPELINE_CRITIC_MAX_OUTPUT_TOKENS", 8192),
        formalizer_prompt=formalizer_prompt,
    )
