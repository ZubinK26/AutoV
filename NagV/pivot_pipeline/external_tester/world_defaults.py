"""Closed-world defaults for external tester scenario lowering."""

from __future__ import annotations

import os
from typing import Literal

from pivot_pipeline.external_tester.schemas import VariableAssignment
from pivot_pipeline.external_tester.variable_tiers import Tier

WORLD_SEMANTICS = "closed_world_defaults_v1"
WORLD_SEMANTICS_GROUNDED_ONLY = "closed_world_grounded_only_v1"

TestMode = Literal["scenario", "decision_query"]
DerivedPolicy = Literal["block", "default"]


def _parse_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name, str(default).lower()).strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    return default


def _parse_int_env(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        return int(raw)
    except ValueError:
        return default


def not_found_defaults() -> dict[str, int | bool]:
    """Env: PIVOT_EXTERNAL_NOT_FOUND_BOOL_DEFAULT, PIVOT_EXTERNAL_NOT_FOUND_INT_DEFAULT."""
    return {
        "bool": _parse_bool_env("PIVOT_EXTERNAL_NOT_FOUND_BOOL_DEFAULT", False),
        "int": _parse_int_env("PIVOT_EXTERNAL_NOT_FOUND_INT_DEFAULT", 0),
    }


def derived_not_found_policy() -> DerivedPolicy:
    raw = os.getenv("PIVOT_EXTERNAL_DERIVED_NOT_FOUND_POLICY", "block").strip().lower()
    if raw == "default":
        return "default"
    return "block"


def default_for_sort(sort: str, *, defaults: dict[str, int | bool] | None = None) -> int | bool:
    d = defaults or not_found_defaults()
    if sort == "bool":
        return bool(d["bool"])
    if sort == "int":
        return int(d["int"])
    raise ValueError(f"unsupported sort for not_found default: {sort!r}")


def apply_not_found_defaults(
    assignments: list[VariableAssignment],
    sorts: dict[str, str],
    *,
    tiers: dict[str, Tier] | None = None,
) -> dict[str, int | bool]:
    """Build a complete Z3 world with tier-aware not_found handling."""
    tiers = tiers or {n: "grounded" for n in sorts}
    policy = derived_not_found_policy()
    by_var = {a.variable: a for a in assignments}
    defaults = not_found_defaults()
    world: dict[str, int | bool] = {}
    derived_incomplete: list[str] = []

    for var in sorted(sorts.keys()):
        a = by_var.get(var)
        if a is None:
            raise KeyError(f"missing assignment for {var!r}")
        if a.status in ("present", "inferred"):
            if a.value is None:
                raise ValueError(f"{var}: {a.status} requires value")
            world[var] = a.value
        elif a.status == "not_found":
            tier = tiers.get(var, "grounded")
            if tier == "derived":
                if policy == "block":
                    derived_incomplete.append(var)
                    continue
                world[var] = default_for_sort(a.sort, defaults=defaults)
            else:
                world[var] = default_for_sort(a.sort, defaults=defaults)
        else:
            raise ValueError(f"{var}: unknown status {a.status!r}")

    if derived_incomplete:
        raise DerivedIncompleteError(derived_incomplete)
    return world


class DerivedIncompleteError(Exception):
    def __init__(self, variables: list[str]) -> None:
        self.variables = variables
        super().__init__(f"derived tier not_found: {', '.join(variables)}")


def resolve_test_mode(explicit: str | None = None) -> TestMode:
    """CLI/param wins; else env PIVOT_EXTERNAL_TEST_MODE; default scenario."""
    if explicit is not None:
        mode = explicit.strip().lower()
    else:
        mode = os.getenv("PIVOT_EXTERNAL_TEST_MODE", "scenario").strip().lower()
    if mode not in ("scenario", "decision_query"):
        raise ValueError(f"external test mode must be scenario|decision_query, got {mode!r}")
    return mode  # type: ignore[return-value]


def resolve_fill_orchestration(explicit: str | None = None) -> str:
    """v3 default; v2 monolithic fallback."""
    if explicit is not None:
        return explicit.strip().lower()
    return os.getenv("PIVOT_EXTERNAL_FILL_ORCHESTRATION", "v3").strip().lower()


__all__ = [
    "DerivedIncompleteError",
    "DerivedPolicy",
    "WORLD_SEMANTICS",
    "WORLD_SEMANTICS_GROUNDED_ONLY",
    "TestMode",
    "apply_not_found_defaults",
    "default_for_sort",
    "derived_not_found_policy",
    "not_found_defaults",
    "resolve_fill_orchestration",
    "resolve_test_mode",
]
