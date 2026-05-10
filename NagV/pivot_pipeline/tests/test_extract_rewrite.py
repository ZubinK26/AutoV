from __future__ import annotations

import json
from pathlib import Path

import pytest

from pivot_pipeline.exceptions import PivotPipelineUserAbort
from pivot_pipeline.extract import ExtractAbort
from pivot_pipeline.extract_scope_rewrite import (
    normalize_operator_hint_input,
    run_scope_rewrite,
    scope_rewrite_hint_max_chars,
)


def test_run_scope_rewrite_parses() -> None:
    def fake_llm(_p: str) -> str:
        return json.dumps(
            {
                "rewritten_line": "Total estimated cost must be at most 1000 dollars.",
                "semantic_deltas": ["Replaced product with scalar total_estimated_cost."],
                "fidelity_notes": "Requires upstream field.",
            }
        )

    out = run_scope_rewrite("a times b <= 1000", extractor_abort_text="ABORT:", llm=fake_llm)
    assert "1000" in out["rewritten_line"]
    assert len(out["semantic_deltas"]) >= 1


def test_run_scope_rewrite_includes_operator_hint_in_prompt() -> None:
    captured: dict[str, str] = {}

    def fake_llm(p: str) -> str:
        captured["prompt"] = p
        return json.dumps(
            {
                "rewritten_line": "x",
                "semantic_deltas": [],
                "fidelity_notes": "",
            }
        )

    run_scope_rewrite(
        "line a",
        extractor_abort_text="ABORT",
        operator_hint="Rule references mean R0004 not literal text",
        llm=fake_llm,
    )
    assert "R0004" in captured["prompt"]
    assert "Rule references mean R0004" in captured["prompt"]


def test_normalize_operator_hint_truncates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PIVOT_SCOPE_REWRITE_HINT_MAX_CHARS", "5")
    assert scope_rewrite_hint_max_chars() == 5
    assert normalize_operator_hint_input("hello world") == "hello"


def test_extract_rewrite_accepts_and_retries(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from pivot_pipeline import extract_rewrite_loop as m

    calls = {"n": 0}

    def fake_one(line_no: int, line: str, **kwargs: object):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ExtractAbort(line_no, line, "ABORT: out of scope")
        return {
            "template_class": "CONSTANT_RELATIONAL",
            "rule_id": f"R{line_no:04d}",
            "applies_to": "GLOBAL",
            "overrides": None,
            "variable": "x",
            "relational_operator": "EQ",
            "constant_value": 1,
            "yields": "SATISFIED",
        }

    def fake_rewrite(orig: str, **kwargs: object):
        return {
            "rewritten_line": "x must be documented",
            "semantic_deltas": ["test"],
            "fidelity_notes": "",
        }

    def fake_wfm(line: str, **kwargs: object):
        return "wfm normalized line"

    monkeypatch.setattr(m, "extract_one_line_with_repairs", fake_one)
    monkeypatch.setattr(m, "run_scope_rewrite", fake_rewrite)
    monkeypatch.setattr(m, "run_pivot_wfm_one_line", fake_wfm)
    monkeypatch.setattr(m, "_max_scope_proposals_per_abort", lambda: 2)

    lines = ["hard line"]
    rules = m.extract_rules_with_abort_rewrite(
        lines,
        work_dir=tmp_path,
        repo_root=tmp_path,
        print_fn=lambda *a, **k: None,
        input_fn=lambda _p: "y",
    )
    assert len(rules) == 1
    assert lines[0] == "wfm normalized line"


def test_extract_rewrite_refused_proposals_then_user_aborts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from pivot_pipeline import extract_rewrite_loop as m

    def fake_one(line_no: int, line: str, **kwargs: object):
        raise ExtractAbort(line_no, line, "ABORT")

    monkeypatch.setattr(m, "extract_one_line_with_repairs", fake_one)
    monkeypatch.setattr(
        m,
        "run_scope_rewrite",
        lambda *a, **k: {"rewritten_line": "r", "semantic_deltas": [], "fidelity_notes": ""},
    )
    monkeypatch.setattr(m, "_max_scope_proposals_per_abort", lambda: 1)
    seq = iter(["n", "", "a"])

    def fake_input(_p: str) -> str:
        return next(seq)

    with pytest.raises(PivotPipelineUserAbort):
        m.extract_rules_with_abort_rewrite(
            ["x"],
            work_dir=tmp_path,
            repo_root=tmp_path,
            print_fn=lambda *a, **k: None,
            input_fn=fake_input,
        )


def test_extract_rewrite_drop_line_restarts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from pivot_pipeline import extract_rewrite_loop as m

    def fake_one(line_no: int, line: str, **kwargs: object):
        if line == "bad":
            raise ExtractAbort(line_no, line, "ABORT")
        return {
            "template_class": "CONSTANT_RELATIONAL",
            "rule_id": f"R{line_no:04d}",
            "applies_to": "GLOBAL",
            "overrides": None,
            "variable": "z",
            "relational_operator": "EQ",
            "constant_value": 1,
            "yields": "SATISFIED",
        }

    monkeypatch.setattr(m, "extract_one_line_with_repairs", fake_one)
    monkeypatch.setattr(
        m,
        "run_scope_rewrite",
        lambda *a, **k: {"rewritten_line": "r", "semantic_deltas": [], "fidelity_notes": ""},
    )
    monkeypatch.setattr(m, "_max_scope_proposals_per_abort", lambda: 1)
    seq = iter(["n", "", "d"])

    def fake_input(_p: str) -> str:
        return next(seq)

    lines = ["bad", "good"]
    rules = m.extract_rules_with_abort_rewrite(
        lines,
        work_dir=tmp_path,
        repo_root=tmp_path,
        print_fn=lambda *a, **k: None,
        input_fn=fake_input,
    )
    assert len(rules) == 1
    assert lines == ["good"]


def test_extract_rewrite_reject_passes_hint_to_next_proposal(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from pivot_pipeline import extract_rewrite_loop as m

    calls = {"n": 0}

    def fake_one(line_no: int, line: str, **kwargs: object):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ExtractAbort(line_no, line, "ABORT")
        return {
            "template_class": "CONSTANT_RELATIONAL",
            "rule_id": f"R{line_no:04d}",
            "applies_to": "GLOBAL",
            "overrides": None,
            "variable": "x",
            "relational_operator": "EQ",
            "constant_value": 1,
            "yields": "SATISFIED",
        }

    rewrite_kw: list[dict[str, object]] = []

    def fake_rewrite(_orig: str, **kwargs: object):
        rewrite_kw.append(dict(kwargs))
        return {"rewritten_line": "ok", "semantic_deltas": [], "fidelity_notes": ""}

    def fake_wfm(line: str, **kwargs: object):
        return line

    monkeypatch.setattr(m, "extract_one_line_with_repairs", fake_one)
    monkeypatch.setattr(m, "run_scope_rewrite", fake_rewrite)
    monkeypatch.setattr(m, "run_pivot_wfm_one_line", fake_wfm)
    monkeypatch.setattr(m, "_max_scope_proposals_per_abort", lambda: 2)
    seq = iter(["n", "disambiguate R0004", "y"])

    def fake_input(_p: str) -> str:
        return next(seq)

    lines = ["hard line"]
    m.extract_rules_with_abort_rewrite(
        lines,
        work_dir=tmp_path,
        repo_root=tmp_path,
        print_fn=lambda *a, **k: None,
        input_fn=fake_input,
    )
    assert len(rewrite_kw) == 2
    assert rewrite_kw[0].get("operator_hint") is None
    assert rewrite_kw[1].get("operator_hint") == "disambiguate R0004"

    log_lines = (tmp_path / "extract_rewrite_log.jsonl").read_text(encoding="utf-8").strip().splitlines()
    reject_rec = json.loads(log_lines[0])
    assert reject_rec["accepted"] is False
    assert reject_rec["operator_hint_submitted"] == "disambiguate R0004"
