"""CPMpy NL → policy pipeline package."""

__version__ = "0.1.0"

from cpmpy_wfm_policy.pipeline.ast_validator import (
    ASTValidationError,
    RuleMetadata,
    global_constraints_from_namespace,
    load_signature_namespace,
    validate_rule_ast,
)
from cpmpy_wfm_policy.pipeline.cheap_checks import (
    CheapCheckError,
    run_global_cheap_checks,
    run_routed_cheap_checks,
    run_scalar_cheap_checks,
)
from cpmpy_wfm_policy.pipeline.diagnoser import DEFAULT_DIAGNOSE_SYSTEM, Diagnosis, diagnose_failure
from cpmpy_wfm_policy.pipeline.formalizer import (
    FormalizerError,
    FormalizerOutput,
    formalize_one_rule,
    formalize_rules_file,
    load_formalizer_system_prompt,
    materialize_rule_expression,
)
from cpmpy_wfm_policy.pipeline.orchestrator import (
    OrchestratorConfig,
    OrchestratorResult,
    OrchestratorState,
    emit_manifest,
    emit_policy_py,
    run_orchestrator,
)
from cpmpy_wfm_policy.pipeline.repair import fallback_repair_hint
from cpmpy_wfm_policy.runtime.decision import Decision
from cpmpy_wfm_policy.runtime.pattern_a import (
    PatternAEvaluationError,
    evaluate_boolean_expr,
    gate_scalar_rules,
)
from cpmpy_wfm_policy.runtime.pattern_b import PatternBError, gate_pattern_b_rules
from cpmpy_wfm_policy.runtime.router import (
    RouterError,
    assert_manifest_routing_consistent,
    gate_tool,
    partition_rules_by_manifest,
)

__all__ = [
    "ASTValidationError",
    "DEFAULT_DIAGNOSE_SYSTEM",
    "Decision",
    "Diagnosis",
    "PatternAEvaluationError",
    "PatternBError",
    "RouterError",
    "assert_manifest_routing_consistent",
    "CheapCheckError",
    "FormalizerError",
    "FormalizerOutput",
    "OrchestratorConfig",
    "OrchestratorResult",
    "OrchestratorState",
    "partition_rules_by_manifest",
    "RuleMetadata",
    "diagnose_failure",
    "evaluate_boolean_expr",
    "emit_manifest",
    "emit_policy_py",
    "fallback_repair_hint",
    "formalize_one_rule",
    "formalize_rules_file",
    "gate_pattern_b_rules",
    "gate_scalar_rules",
    "gate_tool",
    "global_constraints_from_namespace",
    "load_formalizer_system_prompt",
    "load_signature_namespace",
    "materialize_rule_expression",
    "run_global_cheap_checks",
    "run_orchestrator",
    "run_routed_cheap_checks",
    "run_scalar_cheap_checks",
    "validate_rule_ast",
]
