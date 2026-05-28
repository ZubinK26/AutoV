"""Registry pass helpers for semantic Repairer_Piv loop."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

from pivot_pipeline.registry_pass import registry_pass_from_nl_and_rules_with_repairs
from pivot_pipeline.test_repair_registry import (
    apply_cached_registry,
    can_reuse_cached_registry,
)


def semantic_repair_registry_attempts_max() -> int:
    raw = os.getenv("PIVOT_CRITIC_SEMANTIC_REPAIR_REGISTRY_ATTEMPTS", "3").strip()
    try:
        return max(1, min(int(raw), 10))
    except ValueError:
        return 3


def run_semantic_repair_registry(
    *,
    work_dir: Path,
    nl_lines_reg: list[str],
    rules_before: list[dict[str, Any]],
    merged_rules: list[dict[str, Any]],
    cli_skip_registry: bool,
    llm: Callable[..., str],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], bool]:
    """Apply registry to merged rules. Returns ``(registry_obj_or_none, updated_rules, reused_cache)``."""
    if can_reuse_cached_registry(
        rules_before=rules_before,
        rules_after=merged_rules,
        work_dir=work_dir,
        cli_skip_registry=cli_skip_registry,
    ):
        if (work_dir / "identifier_registry.json").is_file():
            reg, updated = apply_cached_registry(work_dir, merged_rules)
            return reg, updated, True
        if cli_skip_registry:
            return None, merged_rules, True

    reg, updated, _rounds = registry_pass_from_nl_and_rules_with_repairs(
        nl_lines_reg,
        merged_rules,
        llm=llm,
        work_dir=work_dir,
    )
    if reg is not None:
        (work_dir / "identifier_registry.json").write_text(
            json.dumps(reg, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return reg, updated, False


__all__ = [
    "run_semantic_repair_registry",
    "semantic_repair_registry_attempts_max",
]
