from __future__ import annotations

from pathlib import Path

import pytest

from pivot_pipeline.paths import resolve_existing_user_file


def test_resolve_existing_strips_mistaken_nagv_prefix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Same spelling as the ``nagv`` package dir must not steal the first path segment (Windows)."""
    root = tmp_path
    (root / "nagv").mkdir()
    dest = root / "pivot_pipeline" / "inputs" / "f.md"
    dest.parent.mkdir(parents=True)
    dest.write_text("rule\n", encoding="utf-8")

    monkeypatch.chdir(root)
    resolved = resolve_existing_user_file(Path("NagV/pivot_pipeline/inputs/f.md"), nagv_project_root=root)
    assert resolved == dest.resolve()
