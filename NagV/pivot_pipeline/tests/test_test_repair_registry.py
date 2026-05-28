from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pivot_pipeline.test_repair_registry import can_reuse_cached_registry, run_test_repair_registry


def test_can_reuse_cached_registry_when_slugs_unchanged(tmp_path: Path) -> None:
    rules = [
        {
            "template_class": "CONSTANT_RELATIONAL",
            "rule_id": "R0001",
            "variable": "foo",
            "relational_operator": "EQ",
            "constant_value": 1,
            "yields": "SATISFIED",
        }
    ]
    (tmp_path / "identifier_registry.json").write_text(
        json.dumps({"canonical_variables": [{"id": "foo", "aliases": []}]}),
        encoding="utf-8",
    )
    assert can_reuse_cached_registry(
        rules_before=rules,
        rules_after=rules,
        work_dir=tmp_path,
        cli_skip_registry=False,
    )


def test_run_test_repair_registry_reuses_cache_without_llm(tmp_path: Path) -> None:
    rules = [
        {
            "template_class": "CONSTANT_RELATIONAL",
            "rule_id": "R0001",
            "variable": "foo_var",
            "relational_operator": "EQ",
            "constant_value": 1,
            "yields": "SATISFIED",
        }
    ]
    (tmp_path / "identifier_registry.json").write_text(
        json.dumps({"canonical_variables": [{"id": "foo", "aliases": ["foo_var"]}]}),
        encoding="utf-8",
    )
    llm = MagicMock(side_effect=AssertionError("LLM should not run"))

    _reg, updated, reused = run_test_repair_registry(
        work_dir=tmp_path,
        nl_lines_reg=["line"],
        rules_before=rules,
        merged_rules=rules,
        cli_skip_registry=False,
        llm=llm,
    )
    assert reused is True
    assert updated[0]["variable"] == "foo"
