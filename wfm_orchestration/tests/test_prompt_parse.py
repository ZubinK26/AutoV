from __future__ import annotations

import io

import pytest

from wfm_orchestration.prompt_parse import parse_int_list, prompt_int_list


def test_parse_int_list() -> None:
    assert parse_int_list("2, 4") == [2, 4]
    assert parse_int_list("") == []


def test_prompt_int_list_reprompts_on_text() -> None:
    stderr = io.StringIO()
    prompts = iter(["Every candidate meets …", "3"])

    def fake_input(_: str) -> str:
        return next(prompts)

    out = prompt_int_list(
        input_fn=fake_input,
        stderr=stderr,
        prompt="indices: ",
        allow_empty=False,
        initial="Every candidate meets …",
    )
    assert out == [3]
    assert "line numbers" in stderr.getvalue().lower()
