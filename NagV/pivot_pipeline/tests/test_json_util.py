from __future__ import annotations

import pytest

from pivot_pipeline.json_util import extract_first_json_value, parse_json_object


def test_parse_fenced_json() -> None:
    text = 'Here:\n```json\n{"a": 1}\n```\n'
    assert parse_json_object(text) == {"a": 1}


def test_parse_raw_object() -> None:
    assert parse_json_object('prefix {"x": true} suffix') == {"x": True}


def test_parse_array() -> None:
    assert extract_first_json_value("[1,2]") == [1, 2]
