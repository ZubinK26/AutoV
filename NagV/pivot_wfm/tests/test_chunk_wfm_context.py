from __future__ import annotations

from pathlib import Path

from pivot_wfm.chunk_wfm_context import PivotChunkWfmContext


def test_drop_local_1based(tmp_path: Path) -> None:
    rules = ["r0", "r1", "r2", "r3", "r4"]
    ctx = PivotChunkWfmContext(
        all_rules=rules,
        work_dir=tmp_path,
        chunk_start=1,
        rules_per_chunk=3,
    )
    ctx.begin_chunk(1, 4)
    dropped = ctx.drop_local_1based([2], reason="test", bundle_id="x")
    assert dropped == [2]
    assert rules == ["r0", "r1", "r3", "r4"]
    assert ctx.active_chunk_end_exclusive == 3
    assert rules[1:3] == ["r1", "r3"]


def test_omit_three_of_five_chunk_keeps_first_two_only(tmp_path: Path) -> None:
    rules = [f"line{i}" for i in range(1, 11)]
    ctx = PivotChunkWfmContext(
        all_rules=rules,
        work_dir=tmp_path,
        chunk_start=5,
        rules_per_chunk=5,
    )
    ctx.begin_chunk(5, 10)
    ctx.drop_local_1based([3, 4, 5], reason="test", bundle_id="x")
    assert len(rules) == 7
    assert ctx.active_chunk_end_exclusive == 7
    assert rules[5:7] == ["line6", "line7"]
    assert rules[5:10] != ["line6", "line7", "line8", "line9", "line10"]
