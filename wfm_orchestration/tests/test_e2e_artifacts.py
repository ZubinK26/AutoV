"""Auto e2e artifacts (exports/e2e_demo_runs) + dotenv for API key."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import patch

from registry_stage.models import DevSessionSnapshot

from wfm_orchestration.orchestrator import _write_e2e_auto_artifacts


def _minimal_dev_session() -> DevSessionSnapshot:
    return DevSessionSnapshot(
        registry=None,
        bundle=None,
        line_traces=[],
        notes="test",
    )


def test_write_e2e_auto_artifacts_creates_json_and_viewer(tmp_path: Path) -> None:
    dev = _minimal_dev_session()
    out = io.StringIO()

    def print_fn(*args, **kwargs):
        print(*args, **kwargs, file=out)

    err = io.StringIO()
    _write_e2e_auto_artifacts(dev, repo_root=tmp_path, print_fn=print_fn, stderr=err)

    runs = tmp_path / "exports" / "e2e_demo_runs"
    assert runs.is_dir()
    subdirs = list(runs.iterdir())
    assert len(subdirs) == 1
    run_dir = subdirs[0]
    assert (run_dir / "dev_session.json").is_file()
    assert (run_dir / "viewer" / "index.md").is_file()
    assert "Run folder:" in out.getvalue()


def test_load_dotenv_for_e2e_calls_load_repo_dotenv():
    with patch("registry_stage.llm.gemini_call.load_repo_dotenv") as m:
        from wfm_orchestration.e2e_context import load_dotenv_for_e2e

        load_dotenv_for_e2e()
        assert m.call_count == 1
