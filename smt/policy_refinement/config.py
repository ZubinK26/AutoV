"""Env-driven settings for post-formalization policy refinement (`dev_plan_policy_nl_refinement_agents_v1.md`)."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class RefinementConfig:
    syntax_repair_cap: int = 3
    semantic_repair_cap: int = 3
    max_recommendations: int = 50
    assessor_context_char_limit: int = 900_000
    parse_timeout_sec: float = 30.0
    assessor_max_output_tokens: int = 32_768
    implementer_max_output_tokens: int = 65_536
    repair_max_output_tokens: int = 65_536
    critic_max_output_tokens: int = 8_192


def refinement_config_from_env() -> RefinementConfig:
    def _i(name: str, default: int) -> int:
        raw = os.environ.get(name, "").strip()
        return int(raw) if raw else default

    def _f(name: str, default: float) -> float:
        raw = os.environ.get(name, "").strip()
        return float(raw) if raw else default

    smt_parse = _f("SMT_PIPELINE_PARSE_TIMEOUT_SEC", 30.0)

    return RefinementConfig(
        syntax_repair_cap=_i("REFINEMENT_SYNTAX_REPAIR_CAP", 3),
        semantic_repair_cap=_i("REFINEMENT_SEMANTIC_REPAIR_CAP", 3),
        max_recommendations=_i("REFINEMENT_MAX_RECOMMENDATIONS", 50),
        assessor_context_char_limit=_i("REFINEMENT_ASSESSOR_CONTEXT_CHAR_LIMIT", 900_000),
        parse_timeout_sec=_f("REFINEMENT_PARSE_TIMEOUT_SEC", smt_parse),
        assessor_max_output_tokens=_i("REFINEMENT_ASSESSOR_MAX_OUTPUT_TOKENS", 32768),
        implementer_max_output_tokens=_i("REFINEMENT_IMPLEMENTER_MAX_OUTPUT_TOKENS", 65536),
        repair_max_output_tokens=_i("REFINEMENT_REPAIR_MAX_OUTPUT_TOKENS", 65536),
        critic_max_output_tokens=_i("REFINEMENT_CRITIC_MAX_OUTPUT_TOKENS", 8192),
    )
