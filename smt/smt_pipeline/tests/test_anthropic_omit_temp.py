import pytest

from smt_pipeline.anthropic_call import _omit_temperature_for_model


def test_omit_temp_opus4_family(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_OMIT_TEMPERATURE", raising=False)
    assert _omit_temperature_for_model("claude-opus-4-7") is True
    assert _omit_temperature_for_model("claude-opus-4-6") is True
    assert _omit_temperature_for_model("claude-sonnet-4-6") is False


def test_omit_temp_env_overrides_all(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_OMIT_TEMPERATURE", "1")
    assert _omit_temperature_for_model("claude-sonnet-4-6") is True
