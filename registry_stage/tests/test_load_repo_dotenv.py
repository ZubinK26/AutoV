"""``load_repo_dotenv``: shell empty GEMINI_API_KEY must not block repo .env."""

from __future__ import annotations

import os

import pytest


def test_load_repo_dotenv_fills_when_shell_has_empty_key(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    (tmp_path / ".env").write_text("GEMINI_API_KEY=from_dotenv_file\n", encoding="utf-8")
    monkeypatch.setenv("GEMINI_API_KEY", "")

    import registry_stage.llm.gemini_call as gc

    monkeypatch.setattr(gc, "repo_root_containing_registry_stage", lambda: tmp_path)
    gc.load_repo_dotenv()
    assert os.environ.get("GEMINI_API_KEY", "").strip() == "from_dotenv_file"


def test_load_repo_dotenv_respects_nonempty_env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    (tmp_path / ".env").write_text("GEMINI_API_KEY=from_file\n", encoding="utf-8")
    monkeypatch.setenv("GEMINI_API_KEY", "already_set")

    import registry_stage.llm.gemini_call as gc

    monkeypatch.setattr(gc, "repo_root_containing_registry_stage", lambda: tmp_path)
    gc.load_repo_dotenv()
    assert os.environ.get("GEMINI_API_KEY") == "already_set"
