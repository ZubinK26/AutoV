"""Configuration for NL→SMT-LIB pipeline (`control_flow_v3.md`)."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class SmtPipelineConfig:
    syntax_repair_cap: int = 3
    semantic_repair_cap: int = 3
    rule_cap: int = 2000
    parse_timeout_sec: float = 30.0
    # If total chars (policy + formalizer payload) exceed, fail CONTEXT_LIMIT_EXCEEDED
    context_char_limit: int = 900_000
    formalizer_max_output_tokens: int = 16_384
    critic_max_output_tokens: int = 8_192
    # When False (default): after critic approval, Z3 check-sat on full merged policy; commit only if sat.
    skip_global_sat_check: bool = False


def smt_config_from_env() -> SmtPipelineConfig:
    def _i(name: str, default: int) -> int:
        raw = os.environ.get(name, "").strip()
        return int(raw) if raw else default

    def _f(name: str, default: float) -> float:
        raw = os.environ.get(name, "").strip()
        return float(raw) if raw else default

    skip_sat = os.environ.get("SMT_PIPELINE_SKIP_GLOBAL_SAT", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )

    return SmtPipelineConfig(
        syntax_repair_cap=_i("SMT_PIPELINE_SYNTAX_REPAIR_CAP", 3),
        semantic_repair_cap=_i("SMT_PIPELINE_SEMANTIC_REPAIR_CAP", 3),
        rule_cap=_i("SMT_PIPELINE_RULE_CAP", 2000),
        parse_timeout_sec=_f("SMT_PIPELINE_PARSE_TIMEOUT_SEC", 30.0),
        context_char_limit=_i("SMT_PIPELINE_CONTEXT_CHAR_LIMIT", 900_000),
        formalizer_max_output_tokens=_i("SMT_PIPELINE_FORMALIZER_MAX_OUTPUT_TOKENS", 16384),
        critic_max_output_tokens=_i("SMT_PIPELINE_CRITIC_MAX_OUTPUT_TOKENS", 8192),
        skip_global_sat_check=skip_sat,
    )
