"""G3–G5 run metadata helpers."""

from __future__ import annotations

import re

from wfm_orchestration.run_metadata import (
    new_bundle_id,
    orchestration_run_id_accept,
    utc_now_iso_z,
    wfm_pipeline_timestamps_at_accept,
)


def test_utc_now_iso_z_format() -> None:
    s = utc_now_iso_z()
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", s)


def test_new_bundle_id_shape() -> None:
    b = new_bundle_id(prefix="demo")
    assert b.startswith("demo_")
    parts = b.split("_")
    assert len(parts) >= 4
    assert len(parts[-1]) == 8


def test_new_bundle_id_invalid_prefix() -> None:
    try:
        new_bundle_id(prefix="123bad")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_orchestration_run_id_accept() -> None:
    r = orchestration_run_id_accept(bundle_id="demo_x", outer_pass_index=0)
    assert "demo_x" in r
    assert r.endswith("_p0_accept")


def test_wfm_pipeline_timestamps() -> None:
    d = wfm_pipeline_timestamps_at_accept()
    assert "confirmation_accepted_utc" in d
    assert d["confirmation_accepted_utc"].endswith("Z")
