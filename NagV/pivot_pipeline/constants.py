"""Pivot policy pipeline — versioned limits (see ``NagV/Extract-Pivot.md`` §7)."""

from __future__ import annotations

POLICY_SEMANTICS_VERSION_DEFAULT = "1.0"
POLICY_SEMANTICS_VERSION_VNEXT = "1.1"
POLICY_SEMANTICS_VERSIONS_SUPPORTED = frozenset(
    {POLICY_SEMANTICS_VERSION_DEFAULT, POLICY_SEMANTICS_VERSION_VNEXT}
)
PATHWAY_CAP = 256
CONDITION_EXPR_MAX_DEPTH = 8

# Variable×variable product conditions (`varprod_cmp`): 0 ≤ v ≤ G per factor / rhs variable (Z3).
DEFAULT_PIVOT_PRODUCT_INT_CAP = 1_000_000

# --- IR vNext expansion templates (lower to core v1 before compile) ---
PIVOT_IR_EXTENSIONS_MANIFEST = "vnext_8"
INT_RANGE_MAX_SPAN = 2_147_483_647
TABLE_BLOCK_MAX_ROWS = 32
BOUNDED_FORALL_MAX_DOMAIN = 32
K_OF_N_MAX_CLAUSES = 10
K_OF_N_MIN_CLAUSES = 1
EXHAUSTIVE_SWITCH_MAX_CASES = 32
# SUM_THRESHOLD: single cap for schema, lowering, extract, and prompts (never 5+ terms).
SUM_THRESHOLD_MAX_TERMS = 4
SUM_THRESHOLD_MAX_COEFF = 10_000
