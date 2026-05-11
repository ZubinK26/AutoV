"""Slice 5: vector AST, helper DAG, Hypothesis, mutation, state extractor."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from cpmpy_wfm_policy.pipeline.ast_validator import (
    RuleMetadata,
    load_signature_namespace,
    validate_rule_ast,
)
from cpmpy_wfm_policy.pipeline.signature_analysis import (
    build_helper_dependency_graph,
    validate_signature_helper_dag,
)
from cpmpy_wfm_policy.runtime.pattern_b import gate_pattern_b_rules
from cpmpy_wfm_policy.runtime.state_extractor import extract_tool_state
from cpmpy_wfm_policy.verification.hypothesis_generators import flat_state_strategy
from cpmpy_wfm_policy.verification.mutation import mutate_field, mutate_vector_element


def _root() -> Path:
    r = Path(__file__).resolve().parents[1]
    if str(r) not in sys.path:
        sys.path.insert(0, str(r))
    return r


def _vector_sig() -> Path:
    return _root() / "domains" / "vector_line" / "signature.py"


def test_vector_line_rule_ast():
    ns = load_signature_namespace(str(_vector_sig()))
    src = """
import cpmpy as cp
rule_1 = cp.all(line_flags[i] for i in range(LINE_LEN))
"""
    meta = RuleMetadata(
        used_symbols=frozenset({"line_flags", "LINE_LEN"}),
        uses_global_constraints=False,
        uses_vector_variables=True,
    )
    name, _ = validate_rule_ast(src, signature_namespace=ns, metadata=meta)
    assert name == "rule_1"


def test_helper_dag_no_cycle_vector_line():
    validate_signature_helper_dag(_vector_sig())


def test_helper_dag_detects_cycle(tmp_path):
    p = tmp_path / "sig.py"
    p.write_text(
        "a = 1\n"
        "b = a + 1\n"
        "c = b + 1\n"
        "a = c + 1\n",
        encoding="utf-8",
    )
    from cpmpy_wfm_policy.pipeline.ast_validator import ASTValidationError

    with pytest.raises(ASTValidationError, match="cycle"):
        validate_signature_helper_dag(p)


def test_build_helper_graph_ignores_var_ctors():
    g = build_helper_dependency_graph(
        _vector_sig().read_text(encoding="utf-8"),
    )
    assert "line_flags" not in g


def test_pattern_b_vector_rule_all_true():
    _root()
    from domains.vector_line import handwritten_rules as hr

    st = {f"line_flags[{i}]": True for i in range(4)}
    ok, viol, _ = gate_pattern_b_rules(hr.all_rules(), st, [], solver="z3")
    assert ok and viol == []


@pytest.mark.filterwarnings("ignore::hypothesis.errors.NonInteractiveExampleWarning")
def test_hypothesis_flat_strategy_smoke():
    ns = load_signature_namespace(str(_vector_sig()))
    strat = flat_state_strategy(ns)
    d = strat.example()
    assert any(k.startswith("line_flags[") for k in d)
    assert len([k for k in d if k.startswith("line_flags[")]) == 4


def test_mutation_vector_flat():
    st = {"line_flags[0]": True, "line_flags[1]": False}
    st2 = mutate_vector_element(st, field="line_flags", index=1, value=True)
    assert st2["line_flags[1]"] is True


def test_mutation_nested_list():
    st = {"line_flags": [True, False, True, False]}
    st2 = mutate_vector_element(st, field="line_flags", index=2, value=False)
    assert st2["line_flags"][2] is False


def test_state_extractor_full_and_index_flat():
    full = {f"line_flags[{i}]": i % 2 == 0 for i in range(4)}
    deps = [
        {"name": "line_flags", "slice": "full"},
        {"name": "line_flags", "slice": "by_index", "index_param": "k"},
    ]
    sub = extract_tool_state(full, tool_dependencies=deps, call_params={"k": 2})
    assert sub["line_flags[2]"] is full["line_flags[2]"]
    assert len(sub) == 4


def test_state_extractor_full_list_form():
    full = {"line_flags": [True, True, False, True]}
    sub = extract_tool_state(
        full,
        tool_dependencies=[{"name": "line_flags", "slice": "full"}],
        call_params={},
    )
    assert sub["line_flags[2]"] is False


def test_state_extractor_by_range():
    full = {f"v[{i}]": i for i in range(5)}
    sub = extract_tool_state(
        full,
        tool_dependencies=[
            {"name": "v", "slice": "by_range", "lower_param": "a", "upper_param": "b"}
        ],
        call_params={"a": 1, "b": 3},
    )
    assert sub == {"v[1]": 1, "v[2]": 2, "v[3]": 3}


def test_mutate_scalar_field():
    s = mutate_field({"x": 1}, "x", 2)
    assert s["x"] == 2
