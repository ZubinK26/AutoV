from __future__ import annotations

import json
from pathlib import Path

import pytest

from pivot_wfm.handoff_coverage import (
    analyze_chunk_handoff_coverage,
    patch_handoff_inject_missing_rules,
)


def _write_handoff(path: Path, lines: list[dict]) -> None:
    path.write_text(
        json.dumps({"bundle_id": "t1", "lines": lines}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def test_coverage_ok_full_chunk(tmp_path: Path) -> None:
    hp = tmp_path / "h.json"
    _write_handoff(
        hp,
        [
            {"line_index": 0, "statement_nl": "A.", "agent3_verdict": "PASS"},
            {"line_index": 1, "statement_nl": "B.", "agent3_verdict": "REWRITE"},
        ],
    )
    r = analyze_chunk_handoff_coverage(hp, 0, 2)
    assert r.ok and r.missing_indices == ()


def test_coverage_missing_index(tmp_path: Path) -> None:
    hp = tmp_path / "h.json"
    _write_handoff(
        hp,
        [{"line_index": 0, "statement_nl": "A.", "agent3_verdict": "PASS"}],
    )
    r = analyze_chunk_handoff_coverage(hp, 0, 2)
    assert not r.ok
    assert r.missing_indices == (1,)


def test_coverage_duplicate_line_index(tmp_path: Path) -> None:
    hp = tmp_path / "h.json"
    _write_handoff(
        hp,
        [
            {"line_index": 0, "statement_nl": "A.", "agent3_verdict": "PASS"},
            {"line_index": 0, "statement_nl": "A2.", "agent3_verdict": "PASS"},
        ],
    )
    r = analyze_chunk_handoff_coverage(hp, 0, 1)
    assert not r.ok
    assert r.duplicate_indices == (0,)


def test_patch_inject_missing(tmp_path: Path) -> None:
    hp = tmp_path / "h.json"
    _write_handoff(
        hp,
        [{"line_index": 0, "statement_nl": "A.", "agent3_verdict": "PASS"}],
    )
    rules = ["A line", "B line"]
    r = patch_handoff_inject_missing_rules(hp, rule_index_start=0, rule_index_end_exclusive=2, all_rules=rules)
    assert r.ok
    data = json.loads(hp.read_text(encoding="utf-8"))
    idxs = {int(x["line_index"]) for x in data["lines"]}
    assert idxs == {0, 1}
    li1 = next(x for x in data["lines"] if int(x["line_index"]) == 1)
    assert li1["statement_nl"] == "B line"
    assert "coverage_injection" in str(li1.get("scope_report") or "").lower()


def test_patch_inject_rejects_duplicates(tmp_path: Path) -> None:
    hp = tmp_path / "h.json"
    _write_handoff(
        hp,
        [
            {"line_index": 0, "statement_nl": "A.", "agent3_verdict": "PASS"},
            {"line_index": 0, "statement_nl": "A.", "agent3_verdict": "PASS"},
        ],
    )
    with pytest.raises(ValueError, match="duplicate"):
        patch_handoff_inject_missing_rules(hp, rule_index_start=0, rule_index_end_exclusive=1, all_rules=["x"])
