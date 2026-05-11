"""State mutations for tests and mutation-style verification (slice 5)."""

from __future__ import annotations

from typing import Any


def mutate_field(state: dict[str, Any], field: str, value: Any) -> dict[str, Any]:
    """Copy-on-write: replace a scalar *field* (or any top-level key)."""
    out = dict(state)
    out[field] = value
    return out


def mutate_vector_element(
    state: dict[str, Any],
    *,
    field: str,
    index: int,
    value: Any,
) -> dict[str, Any]:
    """Mutate ``field[index]`` using flat key ``field[index]`` if present; else list copy."""
    flat_key = f"{field}[{index}]"
    out = dict(state)
    if flat_key in state:
        out[flat_key] = value
        return out
    seq = state.get(field)
    if isinstance(seq, list):
        copy = list(seq)
        copy[index] = value
        out[field] = copy
        return out
    raise KeyError(f"no flat key {flat_key!r} or list {field!r} in state")
