import pytest

from smt_pipeline.json_utils import extract_first_json_object


def test_fenced_json():
    text = 'Here:\n```json\n{"approved": true, "objections": []}\n```'
    assert extract_first_json_object(text) == {"approved": True, "objections": []}


def test_raw_braces():
    assert extract_first_json_object('prefix {"approved": false, "objections": [{}]}')["approved"] is False
