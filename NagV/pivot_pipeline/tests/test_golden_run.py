from __future__ import annotations

import json
from pathlib import Path

from pivot_pipeline.golden_run import save_golden_snapshot


def test_save_golden_snapshot_copies_work_and_input(tmp_path: Path) -> None:
    work = tmp_path / "run"
    work.mkdir()
    (work / "run_summary.json").write_text('{"outcome":"ok"}\n', encoding="utf-8")
    (work / "nested").mkdir()
    (work / "nested" / "x.txt").write_text("wfm", encoding="utf-8")

    src = tmp_path / "in.md"
    src.write_text("# policy\n", encoding="utf-8")

    golden = tmp_path / "golden"
    root = save_golden_snapshot(work_dir=work, nl_source=src, golden_root=golden, summary={"outcome": "ok"})

    assert root == golden.resolve()
    assert (golden / "input" / "in.md").read_text(encoding="utf-8") == "# policy\n"
    assert (golden / "work" / "run_summary.json").read_text(encoding="utf-8").strip() == '{"outcome":"ok"}'
    assert (golden / "work" / "nested" / "x.txt").read_text(encoding="utf-8") == "wfm"
    meta = json.loads((golden / "snapshot_meta.json").read_text(encoding="utf-8"))
    assert meta["outcome"] == "ok"
