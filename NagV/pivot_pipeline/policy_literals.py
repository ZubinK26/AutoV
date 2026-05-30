"""Policy string literals for Z3: enum-like values in atom EQ (domain-agnostic)."""

from __future__ import annotations

from typing import Any

from z3 import IntVal

# Set during build_solver / load path; read by encode_condition.
_ACTIVE_LITERAL_MAP: dict[str, int] | None = None


def harvest_policy_literals(rules: list[dict[str, Any]]) -> dict[str, int]:
    """Map atom / constant string values to stable positive integers (1-based)."""
    found: set[str] = set()

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            if obj.get("kind") == "atom":
                v = obj.get("value")
                if isinstance(v, str):
                    found.add(v)
            elif obj.get("kind") in ("and", "or"):
                for c in obj.get("children") or []:
                    walk(c)
            elif obj.get("kind") == "not":
                walk(obj.get("child"))
            else:
                for key, val in obj.items():
                    if key in (
                        "trigger_condition",
                        "required_condition",
                        "preempting_condition",
                        "left",
                        "right",
                    ):
                        walk(val)
                    elif key == "constant_value" and isinstance(val, str):
                        found.add(val)
                    else:
                        walk(val)
        elif isinstance(obj, list):
            for it in obj:
                walk(it)

    for rule in rules:
        if isinstance(rule, dict):
            walk(rule)

    return {lit: idx + 1 for idx, lit in enumerate(sorted(found))}


def set_active_policy_literals(literal_map: dict[str, int] | None) -> None:
    global _ACTIVE_LITERAL_MAP
    _ACTIVE_LITERAL_MAP = dict(literal_map) if literal_map else None


def get_active_policy_literals() -> dict[str, int]:
    return dict(_ACTIVE_LITERAL_MAP or {})


def literal_int_value(literal: str) -> int | None:
    if _ACTIVE_LITERAL_MAP is None:
        return None
    return _ACTIVE_LITERAL_MAP.get(literal)


def atom_rhs_to_z3(
    sym: dict[str, Any],
    sorts: dict[str, str],
    rhs: Any,
    *,
    int_var_fn: Any,
    scalar_fn: Any,
) -> Any:
    """RHS for condition atom: string policy literals → IntVal, not a free variable."""
    if isinstance(rhs, str):
        lit = literal_int_value(rhs)
        if lit is not None:
            return IntVal(lit)
        return int_var_fn(sym, sorts, rhs)
    return scalar_fn(sym, sorts, rhs)


__all__ = [
    "atom_rhs_to_z3",
    "get_active_policy_literals",
    "harvest_policy_literals",
    "literal_int_value",
    "set_active_policy_literals",
]
