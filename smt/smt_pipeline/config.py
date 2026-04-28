"""Configuration for NL→SMT-LIB pipeline (`control_flow_v3.md`)."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class SmtPipelineConfig:
    syntax_repair_cap: int = 3
    semantic_repair_cap: int = 3
    rule_cap: int = 50
    parse_timeout_sec: float = 30.0
    # If total chars (policy + formalizer payload) exceed, fail CONTEXT_LIMIT_EXCEEDED
    context_char_limit: int = 900_000
    formalizer_max_output_tokens: int = 16_384
    critic_max_output_tokens: int = 8_192


def smt_config_from_env() -> SmtPipelineConfig:
    def _i(name: str, default: int) -> int:
        raw = os.environ.get(name, "").strip()
        return int(raw) if raw else default

    def _f(name: str, default: float) -> float:
        raw = os.environ.get(name, "").strip()
        return float(raw) if raw else default

    return SmtPipelineConfig(
        syntax_repair_cap=_i("SMT_PIPELINE_SYNTAX_REPAIR_CAP", 3),
        semantic_repair_cap=_i("SMT_PIPELINE_SEMANTIC_REPAIR_CAP", 3),
        rule_cap=_i("SMT_PIPELINE_RULE_CAP", 50),
        parse_timeout_sec=_f("SMT_PIPELINE_PARSE_TIMEOUT_SEC", 30.0),
        context_char_limit=_i("SMT_PIPELINE_CONTEXT_CHAR_LIMIT", 900_000),
        formalizer_max_output_tokens=_i("SMT_PIPELINE_FORMALIZER_MAX_OUTPUT_TOKENS", 16384),
        critic_max_output_tokens=_i("SMT_PIPELINE_CRITIC_MAX_OUTPUT_TOKENS", 8192),
    )
