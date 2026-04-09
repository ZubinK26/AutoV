"""Labeled JSONL scoring (no API)."""

from __future__ import annotations

import json
from pathlib import Path

from registry_stage.m3_eval_score import (
    LineLabel,
    check_row,
    parse_jsonl_results,
    score_jsonl,
)


def test_parse_jsonl_header_and_results(tmp_path: Path) -> None:
    p = tmp_path / "t.jsonl"
    p.write_text(
        '{"row_kind":"header","x":1}\n'
        '{"row_kind":"result","example_id":"a","query_mode":"multi_query_fuse","masking_preset":"standard",'
        '"authoritative_hits":[{"entry_id":"ent_1","score":0.9}],'
        '"gap_spans":["AlphaCorp"],"structured_gaps":[]}\n',
        encoding="utf-8",
    )
    header, rows = parse_jsonl_results(p)
    assert header.get("x") == 1
    assert len(rows) == 1
    assert rows[0]["example_id"] == "a"


def test_check_row_retrieval_and_gaps() -> None:
    row = {
        "authoritative_hits": [{"entry_id": "ent_acme_ltd", "score": 0.9}],
        "gap_spans": ["PO-999"],
        "structured_gaps": [],
    }
    lb = LineLabel(
        example_id="x",
        required_authoritative_entry_ids=("ent_acme_ltd", "sort_order"),
        expected_gap_substrings=("PO-999",),
    )
    r = check_row(row, lb, check_authoritative=True, check_gaps=True)
    assert not r.retrieval_ok
    assert "sort_order" in r.retrieval_missing
    assert r.gaps_ok


def test_score_jsonl_against_fixture_labels(tmp_path: Path) -> None:
    labels = Path(__file__).resolve().parent.parent / "eval_fixtures" / "m3_eval_labels.json"
    jsonl = tmp_path / "mini.jsonl"
    # One group / one line: passes retrieval for biz_betacorp (ent_betacorp) and gap NetLedger
    row = {
        "row_kind": "result",
        "example_id": "biz_betacorp_confirm",
        "query_mode": "multi_query_fuse",
        "masking_preset": "standard",
        "authoritative_min_score": 0.28,
        "semantic_backend_label": "stub",
        "authoritative_hits": [{"entry_id": "ent_betacorp", "score": 0.9}],
        "gap_spans": ["NetLedger", "fiscal"],
        "structured_gaps": [],
    }
    jsonl.write_text(
        json.dumps({"row_kind": "header"}) + "\n" + json.dumps(row) + "\n",
        encoding="utf-8",
    )
    _, groups = score_jsonl(jsonl, labels)
    key = ("multi_query_fuse", "standard", 0.28)
    assert key in groups
    assert groups[key].all_ok


def test_labels_file_loads() -> None:
    from registry_stage.m3_eval_score import load_labels

    labels = Path(__file__).resolve().parent.parent / "eval_fixtures" / "m3_eval_labels.json"
    assert labels.is_file()
    a, b, lbs = load_labels(labels)
    assert a and b
    assert len(lbs) == 5


def test_retrieval_eval_labels_load() -> None:
    from registry_stage.m3_eval_score import load_labels

    labels = Path(__file__).resolve().parent.parent / "eval_fixtures" / "m3_retrieval_eval_labels.json"
    assert labels.is_file()
    check_auth, check_gaps, lbs = load_labels(labels)
    assert check_auth
    assert not check_gaps
    assert len(lbs) == 12


def test_score_jsonl_splits_groups_by_min_score(tmp_path: Path) -> None:
    labels = tmp_path / "labels.json"
    labels.write_text(
        json.dumps(
            {
                "check_authoritative": True,
                "check_gaps": False,
                "lines": [
                    {
                        "id": "only",
                        "required_authoritative_entry_ids": ["ent_x"],
                        "expected_gap_substrings": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    row_lo = {
        "row_kind": "result",
        "example_id": "only",
        "query_mode": "multi_query_fuse",
        "masking_preset": "conservative",
        "authoritative_min_score": 0.1,
        "semantic_backend_label": "stub",
        "authoritative_hits": [{"entry_id": "ent_x", "score": 0.9}],
        "gap_spans": [],
        "structured_gaps": [],
    }
    row_hi = {**row_lo, "authoritative_min_score": 0.9}
    jsonl = tmp_path / "t.jsonl"
    jsonl.write_text(
        json.dumps({"row_kind": "header"}) + "\n" + json.dumps(row_lo) + "\n" + json.dumps(row_hi) + "\n",
        encoding="utf-8",
    )
    _, groups = score_jsonl(jsonl, labels)
    assert len(groups) == 2
    assert ("multi_query_fuse", "conservative", 0.1) in groups
    assert ("multi_query_fuse", "conservative", 0.9) in groups
