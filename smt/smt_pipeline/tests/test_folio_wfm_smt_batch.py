"""Unit tests for FOLIO→SMT batch helpers (no live Gemini)."""

from __future__ import annotations

import json
from pathlib import Path

from smt_pipeline.run_folio_wfm_smt_batch import (
    _is_smt_committed,
    folio_example_key,
    folio_row_to_nl,
    load_folio_rows,
    load_wfm_done,
)


def test_folio_example_key_stable() -> None:
    assert folio_example_key(split="validation", line_index=3) == "folio_validation_00003"


def test_folio_row_to_nl() -> None:
    row = {
        "premises": ["If A then B.", "A."],
        "conclusion": "B.",
    }
    s = folio_row_to_nl(row)
    assert "Premise 1:" in s and "Premise 2:" in s and "Conclusion: B." in s


def test_load_folio_rows_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "t.jsonl"
    p.write_text(
        json.dumps({"premises": ["p"], "conclusion": "c"}) + "\n\n"
        + json.dumps({"premises": ["p2"], "conclusion": "c2"}) + "\n",
        encoding="utf-8",
    )
    rows = load_folio_rows(p)
    assert len(rows) == 2
    assert rows[0]["conclusion"] == "c"


def test_load_wfm_done_latest_wins(tmp_path: Path) -> None:
    log = tmp_path / "wfm_completed.jsonl"
    log.write_text(
        json.dumps({"success": True, "example_key": "k1", "bundle_id": "a"}) + "\n"
        + json.dumps({"success": True, "example_key": "k1", "bundle_id": "b"}) + "\n",
        encoding="utf-8",
    )
    d = load_wfm_done(log)
    assert d["k1"]["bundle_id"] == "b"


def test_is_smt_committed(tmp_path: Path) -> None:
    bid = "folio_smt_test_1"
    rec_path = tmp_path / f"{bid}.json"
    assert not _is_smt_committed(tmp_path, bid)
    rec_path.write_text(
        json.dumps({"bundle_id": bid, "pipeline_status": "failed"}), encoding="utf-8"
    )
    assert not _is_smt_committed(tmp_path, bid)
    rec_path.write_text(
        json.dumps({"bundle_id": bid, "pipeline_status": "committed"}), encoding="utf-8"
    )
    assert _is_smt_committed(tmp_path, bid)
