from smt_pipeline.unsat_core import analyze_policy_sat_and_core


def test_simple_unsat_core():
    smt = """(set-logic ALL)
(declare-const p Bool)

; Rule: r_a  |  Line: 0
; NL: "p"
(assert p)

; Rule: r_b  |  Line: 1
; NL: "not p"
(assert (not p))
"""
    r = analyze_policy_sat_and_core(smt)
    assert r.sat_result == "unsat"
    assert r.unsat_core is not None
    assert set(r.unsat_core) == {"r_a#0", "r_b#0"}


def test_sat():
    smt = """(set-logic ALL)
; Rule: r_x  |  Line: 0
(assert true)
"""
    r = analyze_policy_sat_and_core(smt)
    assert r.sat_result == "sat"
