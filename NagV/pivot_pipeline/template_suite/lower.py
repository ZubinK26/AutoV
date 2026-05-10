"""Pure lowering helpers (debug / future caching)."""

from __future__ import annotations

from typing import Any

from pivot_pipeline.template_suite.schemas import BoundaryInstance, TemplateInstance


def lowered_view(inst: TemplateInstance) -> dict[str, Any]:
    """Serializable snapshot of instance (for lowered/ debug dumps)."""
    return inst.model_dump(mode="json")


def boundary_worlds(inst: BoundaryInstance) -> list[dict[str, int | bool]]:
    out: list[dict[str, int | bool]] = []
    for val in inst.values:
        w = dict(inst.world_base)
        w[inst.axis_variable] = val
        out.append(w)
    return out
