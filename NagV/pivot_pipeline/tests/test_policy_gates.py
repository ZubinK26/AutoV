from __future__ import annotations

from pathlib import Path

import pytest

from pivot_pipeline.exceptions import PivotPipelineUserAbort
from pivot_pipeline.policy_gates import enforce_wfm_rule_coverage, wfm_output_matches_source_rule_count


def test_wfm_count_match(tmp_path: Path) -> None:
    src = tmp_path / "a.md"
    src.write_text("one\n\ntwo\n", encoding="utf-8")
    assert wfm_output_matches_source_rule_count(nl_source=src, wfm_nl_text="one\n\ntwo\n")
    assert not wfm_output_matches_source_rule_count(nl_source=src, wfm_nl_text="one\n")


def test_enforce_wfm_blocks_without_interactive(tmp_path: Path) -> None:
    src = tmp_path / "a.md"
    src.write_text("a\n\nb\n", encoding="utf-8")
    ok, inc = enforce_wfm_rule_coverage(
        nl_source=src,
        wfm_nl_text="only one",
        interactive_policy=False,
        print_fn=lambda *a, **k: None,
        input_fn=lambda _s: "",
    )
    assert ok is False and inc is False


def test_enforce_wfm_interactive_proceed(tmp_path: Path) -> None:
    from pivot_pipeline.policy_gates import PROCEED_INCOMPLETE_TOKEN

    src = tmp_path / "a.md"
    src.write_text("a\n\nb\n", encoding="utf-8")
    ok, inc = enforce_wfm_rule_coverage(
        nl_source=src,
        wfm_nl_text="one",
        interactive_policy=True,
        print_fn=lambda *a, **k: None,
        input_fn=lambda _s: PROCEED_INCOMPLETE_TOKEN,
    )
    assert ok is True and inc is True


def test_enforce_wfm_interactive_abort(tmp_path: Path) -> None:
    src = tmp_path / "a.md"
    src.write_text("a\n\nb\n", encoding="utf-8")
    with pytest.raises(PivotPipelineUserAbort):
        enforce_wfm_rule_coverage(
            nl_source=src,
            wfm_nl_text="one",
            interactive_policy=True,
            print_fn=lambda *a, **k: None,
            input_fn=lambda _s: "no",
        )
