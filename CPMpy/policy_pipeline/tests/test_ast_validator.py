"""Adversarial and acceptance tests for slice-1 AST validator."""

from __future__ import annotations

from pathlib import Path

import pytest

from cpmpy_wfm_policy.pipeline.ast_validator import (
    ASTValidationError,
    RuleMetadata,
    load_signature_namespace,
    validate_rule_ast,
)


def _sig_path() -> str:
    return str(Path(__file__).resolve().parents[1] / "domains" / "refund_example" / "signature.py")


@pytest.fixture
def sig_ns() -> dict:
    return load_signature_namespace(_sig_path())


def test_accepts_simple_rule(sig_ns):
    src = """
import cpmpy as cp
rule_1 = (customer_kyc_status == 0) & (transaction_status == 0)
"""
    name, _ = validate_rule_ast(src, signature_namespace=sig_ns)
    assert name == "rule_1"


def test_rejects_lambda(sig_ns):
    src = """
import cpmpy as cp
rule_1 = (lambda x: x)(customer_kyc_status == 0)
"""
    with pytest.raises(ASTValidationError, match="Lambda"):
        validate_rule_ast(src, signature_namespace=sig_ns)


def test_rejects_ifexp(sig_ns):
    src = """
import cpmpy as cp
rule_1 = customer_kyc_status if True else transaction_status
"""
    with pytest.raises(ASTValidationError, match="IfExp"):
        validate_rule_ast(src, signature_namespace=sig_ns)


def test_rejects_bad_comprehension_iterable(sig_ns):
    src = """
import cpmpy as cp
rule_1 = cp.all(customer_kyc_status == 0 for _ in enumerate(range(1)))
"""
    with pytest.raises(ASTValidationError, match="comprehension iterable"):
        validate_rule_ast(src, signature_namespace=sig_ns)


def test_accepts_generator_all_over_range(sig_ns):
    src = """
import cpmpy as cp
rule_1 = cp.all(customer_kyc_status == 0 for _ in range(1))
"""
    validate_rule_ast(src, signature_namespace=sig_ns)


def test_rejects_unknown_name(sig_ns):
    src = """
import cpmpy as cp
rule_1 = mystery_var == 0
"""
    with pytest.raises(ASTValidationError, match="undefined"):
        validate_rule_ast(src, signature_namespace=sig_ns)


def test_rejects_bad_import_alias(sig_ns):
    src = """
import cpmpy as zippy
rule_1 = customer_kyc_status == 0
"""
    with pytest.raises(ASTValidationError, match="import"):
        validate_rule_ast(src, signature_namespace=sig_ns)


def test_rejects_raw_string_literal_compare(sig_ns):
    src = """
import cpmpy as cp
rule_1 = customer_kyc_status == "FAILED"
"""
    with pytest.raises(ASTValidationError, match="string literals"):
        validate_rule_ast(src, signature_namespace=sig_ns)


def test_accepts_enum_dict_string_subscript(sig_ns):
    src = """
import cpmpy as cp
rule_1 = (customer_kyc_status == KYC_STATUS["FAILED"]) & (transaction_status == TRANSACTION_STATUS["POSTED"])
"""
    validate_rule_ast(src, signature_namespace=sig_ns)


def test_rejects_string_subscript_on_non_enum(sig_ns):
    src = """
import cpmpy as cp
rule_1 = customer_kyc_status["x"] == 0
"""
    with pytest.raises(ASTValidationError, match="string subscripts are only allowed"):
        validate_rule_ast(src, signature_namespace=sig_ns)
