"""ThinkingConfig is omitted for models that reject it (e.g. gemini-2.5-pro)."""

from __future__ import annotations

from wfm_orchestration.gemini_client import model_supports_thinking_config


def test_model_supports_thinking_config_skips_2_5_pro() -> None:
    assert not model_supports_thinking_config("gemini-2.5-pro")
    assert not model_supports_thinking_config("gemini-2.5-pro-preview-05-06")
    assert model_supports_thinking_config("gemini-3.1-pro-preview")
    assert model_supports_thinking_config("gemini-3-flash-preview")
