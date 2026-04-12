"""Warm registry file for interactive demo (exports/wfm_demo_warm_registry.json)."""

from __future__ import annotations

import json

from registry_stage.models import SCHEMA_VERSION

from wfm_orchestration.demo_launcher import _build_warm_session, _default_warm_registry_path


def test_default_warm_path_under_exports():
    p = _default_warm_registry_path()
    assert p.name == "wfm_demo_warm_registry.json"
    assert "exports" in p.parts


def test_build_warm_session_clear_removes_file(tmp_path):
    path = tmp_path / "w.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "entries": [],
                "entry_edges": [],
            }
        ),
        encoding="utf-8",
    )
    s = _build_warm_session(path, persist_load=True, clear_existing=True)
    assert not path.is_file()
    assert not list(s.entries.values())


def test_build_warm_session_loads_entries(tmp_path):
    path = tmp_path / "w.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "entries": [
                    {
                        "id": "sort_test_alpha",
                        "kind": "sort",
                        "name": "Alpha",
                        "source_rule": [],
                        "nl_description": "d",
                        "status": "active",
                    }
                ],
                "entry_edges": [],
            }
        ),
        encoding="utf-8",
    )
    s = _build_warm_session(path, persist_load=True, clear_existing=False)
    assert s.get("sort_test_alpha") is not None
    assert s.get("sort_test_alpha").name == "Alpha"
