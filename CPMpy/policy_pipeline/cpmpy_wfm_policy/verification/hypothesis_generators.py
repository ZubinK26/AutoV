"""Hypothesis strategies from ``signature.py`` + ``TEST_SHAPE_BOUNDS`` (slice 5)."""

from __future__ import annotations

from typing import Any

from cpmpy_wfm_policy.pipeline.ast_validator import dimension_constant_names


def _merge_test_bounds(namespace: dict[str, Any]) -> dict[str, int]:
    dd = namespace.get("DOMAIN_DIMENSIONS")
    tb = namespace.get("TEST_SHAPE_BOUNDS")
    out: dict[str, int] = {}
    if isinstance(dd, dict):
        for k, v in dd.items():
            out[str(k)] = int(v)
    if isinstance(tb, dict):
        for k, v in tb.items():
            out[str(k)] = int(v)
    return out


def _resolve_shape_elts(shape: Any, merged: dict[str, int], namespace: dict[str, Any]) -> tuple[int, ...]:
    if shape is None:
        return ()
    if isinstance(shape, int):
        return (shape,)
    if not isinstance(shape, tuple):
        shape = (shape,)
    out: list[int] = []
    for dim in shape:
        if isinstance(dim, int):
            out.append(dim)
        elif isinstance(dim, str):
            out.append(int(merged[dim]))
        else:
            key = str(dim)
            if key in merged:
                out.append(int(merged[key]))
            elif hasattr(dim, "__int__"):
                out.append(int(dim))
            elif key in namespace and isinstance(namespace[key], int):
                out.append(int(namespace[key]))
            else:
                raise ValueError(f"cannot resolve shape dimension {dim!r}")
    return tuple(out)


def _is_bool_var(v: Any) -> bool:
    try:
        return int(v.lb) == 0 and int(v.ub) == 1
    except Exception:
        return "bool" in type(v).__name__.lower()


def flat_state_strategy(namespace: dict[str, Any]) -> Any:
    """
    Hypothesis composite producing flat dicts: scalar ``name -> value`` and vector
    ``name[i] -> value`` suitable for :func:`cpmpy_wfm_policy.runtime.pattern_b.gate_pattern_b_rules`.
    """
    from hypothesis import strategies as st

    _ = dimension_constant_names(namespace)
    merged = _merge_test_bounds(namespace)
    skip = frozenset(
        {
            "cp",
            "cpmpy",
            "TOOL_DEPENDENCIES",
            "DOMAIN_DIMENSIONS",
            "TEST_SHAPE_BOUNDS",
            "GLOBAL_CONSTRAINTS",
        }
    )
    scalar: dict[str, Any] = {}
    vec_parts: list[Any] = []

    for k, v in namespace.items():
        if k.startswith("_") or k in skip:
            continue
        shape = getattr(v, "shape", None)
        if shape is None:
            if not hasattr(v, "lb"):
                continue
            lo, hi = int(v.lb), int(v.ub)
            scalar[k] = st.booleans() if _is_bool_var(v) else st.integers(lo, hi)
            continue
        shp = _resolve_shape_elts(shape, merged, namespace)
        if len(shp) != 1:
            raise NotImplementedError("slice 5 supports only 1D vector Hypothesis")
        n = shp[0]
        probe = v[0]
        if hasattr(probe, "lb") and probe.lb is not None:
            lo, hi = int(probe.lb), int(probe.ub)
            elem = st.booleans() if _is_bool_var(probe) else st.integers(lo, hi)
        else:
            elem = st.booleans()

        def _flat_map(vals: list, name: str = k) -> dict[str, Any]:
            return {f"{name}[{i}]": vals[i] for i in range(len(vals))}

        vec_parts.append(st.lists(elem, min_size=n, max_size=n).map(_flat_map))

    if not scalar and not vec_parts:
        return st.just({})

    scal_st = st.fixed_dictionaries(scalar) if scalar else st.just({})
    if not vec_parts:
        return scal_st

    def _merge_maps(parts: tuple) -> dict[str, Any]:
        out = dict(parts[0])
        for p in parts[1:]:
            out.update(p)
        return out

    return st.tuples(scal_st, *vec_parts).map(_merge_maps)
