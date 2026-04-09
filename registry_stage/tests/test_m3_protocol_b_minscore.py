"""Protocol B helper (pure helpers only; no live API)."""

from __future__ import annotations

from registry_stage.m3_protocol_b_minscore import score_tag_for_filename


def test_score_tag_for_filename() -> None:
    assert score_tag_for_filename(0.28) == "0p280"
    assert score_tag_for_filename(0.22) == "0p220"
    assert score_tag_for_filename(1.0) == "1p000"
