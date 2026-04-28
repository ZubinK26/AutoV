from smt_pipeline.rule_count import distinct_rule_ids_in_policy, rule_count


def test_empty_policy_zero_rules():
    assert rule_count("") == 0
    assert rule_count("   \n") == 0


def test_counts_distinct_rule_ids():
    s = """
; Rule: r_aaa  |  Line: 0
; Rule: r_bbb  |  Line: 1
; Rule: r_aaa  |  Line: 2
"""
    assert rule_count(s) == 2
    assert distinct_rule_ids_in_policy(s) == {"r_aaa", "r_bbb"}
