"""Batch planning for chunked phase-1 grounded fill."""

from __future__ import annotations

import os
from typing import Literal

from pivot_pipeline.external_tester.variable_tiers import Tier

SortKind = Literal["int", "bool"]


def fill_batch_size() -> int:
    raw = os.getenv("PIVOT_EXTERNAL_FILL_BATCH_SIZE", "12").strip()
    try:
        return max(4, min(int(raw), 30))
    except ValueError:
        return 12


def plan_grounded_batches(
    *,
    tiers: dict[str, Tier],
    sorts: dict[str, SortKind],
) -> list[list[str]]:
    """Order: int grounded, bool grounded, stable name sort within each."""
    ints = sorted(n for n, t in tiers.items() if t == "grounded" and sorts.get(n) == "int")
    bools = sorted(n for n, t in tiers.items() if t == "grounded" and sorts.get(n) == "bool")
    ordered = ints + bools
    size = fill_batch_size()
    return [ordered[i : i + size] for i in range(0, len(ordered), size)] or [[]]


def catalog_excerpt_for_names(
    names: list[str],
    sorts: dict[str, SortKind],
    *,
    tiers: dict[str, Tier] | None = None,
) -> str:
    lines = ["### Variables for this batch only", ""]
    for name in names:
        sort = sorts.get(name, "?")
        tier = f", tier={tiers[name]}" if tiers else ""
        lines.append(f"- `{name}` ({sort}{tier})")
    return "\n".join(lines)


__all__ = [
    "catalog_excerpt_for_names",
    "fill_batch_size",
    "plan_grounded_batches",
]
