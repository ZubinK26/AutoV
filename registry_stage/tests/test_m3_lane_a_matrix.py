"""Lane A matrix axis resolution (no API)."""

from __future__ import annotations

import pytest

from registry_stage.m3_lane_a import resolve_lane_a_matrix_axes


def test_defaults_full_matrix() -> None:
    q, m = resolve_lane_a_matrix_axes(None, None)
    assert q == ["multi_query_fuse", "single_concat"]
    assert m == ["standard", "aggressive", "conservative"]


def test_conservative_only_preserves_query_modes() -> None:
    q, m = resolve_lane_a_matrix_axes(None, ["conservative"])
    assert q == ["multi_query_fuse", "single_concat"]
    assert m == ["conservative"]


def test_single_query_mode() -> None:
    q, m = resolve_lane_a_matrix_axes(["multi_query_fuse"], None)
    assert q == ["multi_query_fuse"]
    assert m == ["standard", "aggressive", "conservative"]


def test_empty_raises() -> None:
    with pytest.raises(ValueError, match="query_modes"):
        resolve_lane_a_matrix_axes([], ["conservative"])
    with pytest.raises(ValueError, match="masking_presets"):
        resolve_lane_a_matrix_axes(["single_concat"], [])
