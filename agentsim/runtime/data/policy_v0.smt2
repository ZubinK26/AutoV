; AutoV agentsim - policy artifact v0 (hand-authored for Slice C; NL pipeline may replace later).
; Policy-Version: policy-v0
; Rule-ID: R-VULN-GOODWILL-CAP
; Covers-Tool: apply_goodwill_credit
; Rule-Note: Reachability uses RULE_TRIGGER_BUILDERS in policy_consistency.py (guard: vulnerable AND amount>50000).
; NL: Vulnerable customers may not receive goodwill credits above GBP 500 (50000 pence) in one action.

(set-logic ALL)

(declare-const sim-vulnerable Bool)
(declare-const sim-proposed-goodwill-pence Int)
(declare-const sim-legal-goodwill Bool)

(assert (= sim-legal-goodwill (not (and sim-vulnerable (> sim-proposed-goodwill-pence 50000)))))
