; Fixture: contradictory policy (for consistency checker tests).
; Policy-Version: policy-contradiction-test

(set-logic ALL)
(declare-const sim-x Bool)
(assert sim-x)
(assert (not sim-x))
