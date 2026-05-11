"""Offline verification utilities (Hypothesis, mutation, … slice 5+)."""

from cpmpy_wfm_policy.verification.hypothesis_generators import flat_state_strategy
from cpmpy_wfm_policy.verification.medium_checks import (
    MediumCheckError,
    run_cumulative_model_sat,
    run_hypothesis_smoke_pattern_a,
    run_mutation_flip_dependency_smoke,
)
from cpmpy_wfm_policy.verification.mutation import mutate_field, mutate_vector_element
from cpmpy_wfm_policy.verification.roundtrip import (
    BackTranslationResult,
    RoundtripError,
    RoundtripResult,
    build_back_translator_user_message,
    diagnose_roundtrip_failure,
    expressions_equivalent,
    load_back_translator_system_prompt,
    run_roundtrip_one_rule,
)

__all__ = [
    "BackTranslationResult",
    "MediumCheckError",
    "RoundtripError",
    "RoundtripResult",
    "build_back_translator_user_message",
    "diagnose_roundtrip_failure",
    "expressions_equivalent",
    "flat_state_strategy",
    "load_back_translator_system_prompt",
    "mutate_field",
    "mutate_vector_element",
    "run_cumulative_model_sat",
    "run_hypothesis_smoke_pattern_a",
    "run_mutation_flip_dependency_smoke",
    "run_roundtrip_one_rule",
]
