"""Read variable values from a Z3 model (shared by world_builder and policy_query)."""

from __future__ import annotations

from typing import Any

from z3 import is_false, is_true

from pivot_pipeline.template_suite.execute_z3 import _fresh_bool, _int_var


def model_value(model: Any, sym: dict, sorts: dict[str, str], name: str) -> int | bool:
    st = sorts[name]
    if st == "bool":
        v = model.eval(_fresh_bool(sym, sorts, name), model_completion=True)
        if is_true(v):
            return True
        if is_false(v):
            return False
        raise ValueError(f"non-boolean model value for {name!r}")
    v = model.eval(_int_var(sym, sorts, name), model_completion=True)
    return int(v.as_long())


__all__ = ["model_value"]
