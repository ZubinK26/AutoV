from __future__ import annotations

import json
from pathlib import Path

from pivot_wfm.policy_drops import drop_rules_at_global_indices, write_effective_source_nl


def test_drop_rules_high_to_low(tmp_path: Path) -> None:
    rules = ["a", "b", "c", "d"]
    dropped = drop_rules_at_global_indices(
        rules,
        [1, 3],
        work_dir=tmp_path,
        reason="test",
        bundle_id="b1",
    )
    assert dropped == [1, 3]
    assert rules == ["a", "c"]
    log = tmp_path / "pivot_wfm_dropped_rules.jsonl"
    lines = [json.loads(ln) for ln in log.read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 2
    eff = tmp_path / "pivot_wfm_effective_source.nl"
    assert eff.is_file()
    assert "a" in eff.read_text(encoding="utf-8")


def test_write_effective_source_trailing_newline(tmp_path: Path) -> None:
    p = write_effective_source_nl(tmp_path, ["one", "two"])
    assert p.read_text(encoding="utf-8").endswith("\n")
