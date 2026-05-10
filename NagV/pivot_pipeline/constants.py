"""Pivot policy pipeline — versioned limits (see ``NagV/Extract-Pivot.md`` §7)."""

from __future__ import annotations

POLICY_SEMANTICS_VERSION_DEFAULT = "1.0"
PATHWAY_CAP = 256
CONDITION_EXPR_MAX_DEPTH = 8

# Variable×variable product conditions (`varprod_cmp`): 0 ≤ v ≤ G per factor / rhs variable (Z3).
DEFAULT_PIVOT_PRODUCT_INT_CAP = 1_000_000
