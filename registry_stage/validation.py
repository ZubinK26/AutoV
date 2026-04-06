"""Alignment checks for registry vs committed rules (Phase 2)."""

from __future__ import annotations

from typing import Any

from registry_stage.models import RegistryFile


def validate_alignment(
    registry: RegistryFile,
    *,
    rule_rows: list[dict[str, Any]] | None = None,
) -> list[str]:
    """
    Verify `committed_edges` and `entries[].source_rule` per `registry_persistence_v1.md` §7.

    Phase 1: stub — returns no issues. Full enforcement belongs with production rule commit
    (formalizer / Z3 path); see `development_plan_registry_stage_v1.md` Phase 2 outline.
    """
    _ = registry
    _ = rule_rows
    return []
