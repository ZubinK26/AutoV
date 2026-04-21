"""Tests for curated pools + manual word cap (**G6 / G7**)."""

from __future__ import annotations

import random

import pytest

from wfm_orchestration.demo_loader import (
    ManualInputRejected,
    compute_manual_word_limit,
    get_curated_example_text,
    load_demo_pool_config,
    text_for_demo_choice,
    validate_manual_text,
    word_count,
)


def test_get_curated_example_text_known_ids():
    cfg = load_demo_pool_config()
    for ex_id in ("F-8", "PF-8", "R-4", "E-5"):
        t = get_curated_example_text(ex_id, cfg=cfg)
        assert len(t.strip()) > 10


def test_load_demo_pool_config_has_expected_keys():
    cfg = load_demo_pool_config()
    assert "folio_example_ids" in cfg
    assert "pfolio_example_ids" in cfg
    assert "stress_example_ids" in cfg
    assert len(cfg["folio_example_ids"]) >= 1
    assert len(cfg["pfolio_example_ids"]) >= 1
    assert len(cfg["stress_example_ids"]) >= 1


def test_compute_manual_word_limit_is_positive():
    lim = compute_manual_word_limit()
    assert lim > 15


def test_text_for_demo_choice_reproducible_with_seed():
    cfg = load_demo_pool_config()
    a = text_for_demo_choice("folio", cfg=cfg, rng=random.Random(42))
    b = text_for_demo_choice("folio", cfg=cfg, rng=random.Random(42))
    assert a == b


def test_text_for_demo_choice_exclude_ids():
    cfg = load_demo_pool_config()
    pool = list(cfg["folio_example_ids"])
    excl = set(pool[:-1])
    ex_id, _body = text_for_demo_choice("folio", cfg=cfg, rng=random.Random(0), exclude_ids=excl)
    assert ex_id == pool[-1]


def test_text_for_demo_choice_exclude_all_raises():
    cfg = load_demo_pool_config()
    pool = frozenset(cfg["folio_example_ids"])
    with pytest.raises(ValueError, match="no curated examples left"):
        text_for_demo_choice("folio", cfg=cfg, exclude_ids=pool)


def test_validate_manual_text_rejects_over_limit():
    cfg = load_demo_pool_config()
    limit = compute_manual_word_limit(cfg)
    too_long = "word " * (limit + 5)
    with pytest.raises(ManualInputRejected):
        validate_manual_text(too_long, limit=limit)


def test_validate_manual_text_accepts_at_limit():
    cfg = load_demo_pool_config()
    limit = compute_manual_word_limit(cfg)
    ok = ("x " * limit).strip()
    assert word_count(ok) == limit
    validate_manual_text(ok, limit=limit)
