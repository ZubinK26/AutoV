from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pivot_pipeline.semantic_repair_registry import run_semantic_repair_registry


def test_reuse_cached_registry_when_slugs_unchanged(tmp_path: Path) -> None:
    rules = [
        {
            "rule_id": "R0001",
            "template_class": "CONSTANT_RELATIONAL",
            "variable": "x",
            "relational_operator": "EQ",
            "constant_value": 1,
            "yields": "SATISFIED",
            "applies_to": "GLOBAL",
        }
    ]
    (tmp_path / "identifier_registry.json").write_text(
        '{"variables": [{"slug": "x", "display_name": "x"}]}',
        encoding="utf-8",
    )
    reg, updated, reused = run_semantic_repair_registry(
        work_dir=tmp_path,
        nl_lines_reg=[],
        rules_before=rules,
        merged_rules=rules,
        cli_skip_registry=False,
        llm=MagicMock(),
    )
    assert reused
    assert reg is not None
    assert updated == rules
