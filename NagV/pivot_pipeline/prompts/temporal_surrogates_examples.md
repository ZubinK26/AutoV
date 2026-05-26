# Temporal surrogates — NL examples (T1–T8)

One encodable line per rule unless noted. Variable names are illustrative.

## T1 — Scalar ordering

`start_x must be strictly before start_y.` → `VARIABLE_RELATIONAL`: `start_x` LT `start_y`.

## T2 — Prerequisite gating

`Refund may be issued only if identity_verified equals 1.` → `LOGICAL_IMPLICATION`: trigger `identity_verified` EQ 1 → required `refund_may_be_issued` EQ 1.

## T3 — Implication chain (two lines)

1. `If step_b_complete equals 1 then step_a_complete must equal 1.`
2. `If step_c_complete equals 1 then step_b_complete must equal 1.`

Each → one `LOGICAL_IMPLICATION` rule.

## T4 — Phase enum + switch

1. `phase must be one of 1, 2, or 3.` → `SET_INCLUSION` or `INT_RANGE`.
2. `When phase equals 2, review_required must equal 1.` → `LOGICAL_IMPLICATION` or `EXHAUSTIVE_SWITCH` case.

## T5 — Exclusive modes

`Exactly one of draft_mode, review_mode, published_mode must be true.` → `EXCLUSIVE_CHOICE` exactly_one.

## T6 — K-of-n

`At least 2 of the following must hold: income_verified, identity_verified, address_verified, employment_verified.` → `K_OF_N` with k=2, four clauses.

## T7 — Phase table

`When workflow_state equals PENDING, approver_assigned must equal 1.` (one line per state, or one `TABLE_BLOCK`.)

## T8 — Int range on counter

`retry_count must be between 0 and 5 inclusive.` → `INT_RANGE` lo=0 hi=5.
