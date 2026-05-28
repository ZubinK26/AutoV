"""Registry pass helpers for Test-Repairer loop."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

from pivot_pipeline.registry_pass import (
    apply_registry_to_rules,
    build_alias_map,
    collect_used_slugs,
    registry_pass_from_nl_and_rules_with_repairs,
)


def test_repair_skip_registry_env() -> bool:
    raw = os.getenv("PIVOT_TEST_REPAIR_SKIP_REGISTRY", "0").strip().lower()
    return raw in ("1", "true", "yes")


def test_repair_registry_attempts_max() -> int:
    raw = os.getenv("PIVOT_TESTER_REPAIR_REGISTRY_ATTEMPTS", "3").strip()
    try:
        return max(1, min(int(raw), 10))
    except ValueError:
        return 3


def test_repair_count_api_as_attempt() -> bool:
    raw = os.getenv("PIVOT_TEST_REPAIR_COUNT_API_AS_ATTEMPT", "0").strip().lower()
    return raw in ("1", "true", "yes")


def is_repairer_api_error(exc: BaseException) -> bool:
    msg = str(exc).upper()
    return "503" in msg or "UNAVAILABLE" in msg or "RATE" in msg or "QUOTA" in msg


def slug_set(rules: list[dict[str, Any]]) -> set[str]:
    return set(collect_used_slugs(rules))


def can_reuse_cached_registry(
    *,
    rules_before: list[dict[str, Any]],
    rules_after: list[dict[str, Any]],
    work_dir: Path,
    cli_skip_registry: bool,
) -> bool:
    if cli_skip_registry or test_repair_skip_registry_env():
        return True
    if slug_set(rules_before) != slug_set(rules_after):
        return False
    return (work_dir / "identifier_registry.json").is_file()


def apply_cached_registry(
    work_dir: Path,
    rules: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    reg_path = work_dir / "identifier_registry.json"
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    alias_map = build_alias_map(reg)
    updated = apply_registry_to_rules(rules, alias_map)
    return reg, updated


def run_test_repair_registry(
    *,
    work_dir: Path,
    nl_lines_reg: list[str],
    rules_before: list[dict[str, Any]],
    merged_rules: list[dict[str, Any]],
    cli_skip_registry: bool,
    llm: Callable[..., str],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], bool]:
    """
    Apply registry to merged rules.

    Returns ``(registry_obj_or_none, updated_rules, reused_cache)``.
    """
    if can_reuse_cached_registry(
        rules_before=rules_before,
        rules_after=merged_rules,
        work_dir=work_dir,
        cli_skip_registry=cli_skip_registry,
    ):
        if (work_dir / "identifier_registry.json").is_file():
            reg, updated = apply_cached_registry(work_dir, merged_rules)
            return reg, updated, True
        if cli_skip_registry or test_repair_skip_registry_env():
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
    "apply_cached_registry",
    "can_reuse_cached_registry",
    "is_repairer_api_error",
    "run_test_repair_registry",
    "test_repair_count_api_as_attempt",
    "test_repair_registry_attempts_max",
    "test_repair_skip_registry_env",
]
