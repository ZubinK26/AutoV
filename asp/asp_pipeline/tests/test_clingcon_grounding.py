"""Grounding with Potassco clingcon for ``&sum{{...}}`` (ClinCon fragment)."""

from __future__ import annotations

import pytest

from asp_pipeline.clingo_check import check_parse_and_ground
from asp_pipeline.clingcon_api import clingcon_import_error_message


pytestmark = pytest.mark.skipif(
    clingcon_import_error_message() is not None,
    reason="clingcon not installed (pip install clingcon)",
)


def test_clincon_sum_grounding_from_spec() -> None:
    """§2.1 style: ``&sum{{...}}`` linear constraint (grounding must succeed)."""
    proposed = "#const rate=50.\n:- &sum{ rate } > 100.\n"
    ok, stage, err = check_parse_and_ground(
        "",
        proposed,
        parse_timeout_sec=15.0,
        ground_timeout_sec=30.0,
    )
    assert ok, f"expected parse+ground ok, got stage={stage!r} err={err!r}"


def test_clincon_sum_unchanged_with_empty_existing() -> None:
    proposed = "#const a=1.\n#const b=2.\n:- &sum{ a; b } > 5.\n"
    ok, stage, err = check_parse_and_ground(
        "",
        proposed,
        parse_timeout_sec=15.0,
        ground_timeout_sec=30.0,
    )
    assert ok, (stage, err)


def test_core_asp_still_parses_and_grounds() -> None:
    proposed = "p(a). q(b). r(X) :- p(X), not q(X).\n"
    ok, stage, err = check_parse_and_ground(
        "",
        proposed,
        parse_timeout_sec=15.0,
        ground_timeout_sec=30.0,
    )
    assert ok, (stage, err)
