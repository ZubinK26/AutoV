# Example Domain: Refund Policy

A worked example demonstrating the full set of inputs the pipeline expects per domain. Used as the reference instantiation for v1 testing and as a template for new domains.

This domain is **deliberately minimal**: scalar fields only, no vector fields, no global constraints, no nested helpers. It exercises the simplest path through the pipeline. A second example domain exercising the full scope (vectors, globals, nested helpers) should be authored as part of the v1 success criteria — see the project specification's success criterion #9.

This document is not executed; it shows what each input file looks like. Cursor produces these as actual files in `domains/refund_example/` when implementing.

---

## File 1: `signature.py`

```python
import cpmpy as cp

# Section 2 — Enumerations
KYC_STATUS = {"VERIFIED": 0, "FAILED": 1}
REFUND_TYPE = {"MERCHANT_REFUND": 0, "GOODWILL_CREDIT": 1}
TRANSACTION_STATUS = {"POSTED": 0, "PENDING": 1}

# Section 3 — Entity field declarations (scalar)
customer_kyc_status = cp.intvar(0, 1, name="customer_kyc_status")
customer_vulnerable_flag = cp.boolvar(name="customer_vulnerable_flag")
customer_recent_goodwill_total = cp.intvar(0, 1_000_000, name="customer_recent_goodwill_total")
account_has_sanctions_block = cp.boolvar(name="account_has_sanctions_block")
transaction_amount_pence = cp.intvar(0, 10_000_000, name="transaction_amount_pence")
transaction_status = cp.intvar(0, 1, name="transaction_status")

# Section 4 — Entity field declarations (vector)
# (none in this domain)

# Section 5 — Tool-call parameter declarations
refund_call_amount_pence = cp.intvar(0, 10_000_000, name="refund_call_amount_pence")
refund_call_type = cp.intvar(0, 1, name="refund_call_type")

# Section 6 — Derived helpers
customer_kyc_failed = (customer_kyc_status == KYC_STATUS["FAILED"])
transaction_is_posted = (transaction_status == TRANSACTION_STATUS["POSTED"])
refund_is_merchant = (refund_call_type == REFUND_TYPE["MERCHANT_REFUND"])
refund_is_goodwill = (refund_call_type == REFUND_TYPE["GOODWILL_CREDIT"])

# Section 7 — Domain dimensions
# (omitted; no vector fields)

# Section 8 — Tool-to-state-dependency manifest
TOOL_DEPENDENCIES = {
    "apply_refund": [
        "customer_kyc_status",
        "customer_vulnerable_flag",
        "customer_recent_goodwill_total",
        "account_has_sanctions_block",
        "transaction_amount_pence",
        "transaction_status",
        "refund_call_amount_pence",
        "refund_call_type",
    ],
}
```

---

## File 2: `glossary.md`

```
customer_kyc_status: integer encoding of the customer's KYC verification state.
  0 means VERIFIED. 1 means FAILED.

customer_vulnerable_flag: boolean indicating whether the customer is flagged
  as a vulnerable customer under FCA Consumer Duty.

customer_recent_goodwill_total: integer in pence. Cumulative total of goodwill
  credits issued to this customer in the rolling preceding twelve months.
  Maintained by the runtime; the formal model treats it as a ground integer.

account_has_sanctions_block: boolean. True if the account has an active
  sanctions block of any type.

transaction_amount_pence: integer in pence. Amount of the original transaction
  being refunded. Always positive.

transaction_status: integer encoding. 0 means POSTED. 1 means PENDING.

refund_call_amount_pence: integer in pence. Proposed refund amount in the
  current tool call. Always positive.

refund_call_type: integer encoding. 0 means MERCHANT_REFUND. 1 means GOODWILL_CREDIT.

customer_kyc_failed: derived. True iff customer_kyc_status equals FAILED.

transaction_is_posted: derived. True iff transaction_status equals POSTED.

refund_is_merchant: derived. True iff refund_call_type equals MERCHANT_REFUND.

refund_is_goodwill: derived. True iff refund_call_type equals GOODWILL_CREDIT.
```

---

## File 3: `rules.txt`

```
A refund call requires that the referenced transaction has status POSTED.
A refund call is not permitted if the affected customer's KYC status is FAILED.
A refund call is not permitted if the affected account has its sanctions block flag set to true.
A merchant refund call with an amount greater than the referenced transaction's amount is not permitted.
A goodwill credit call with an amount greater than ten thousand pence is not permitted.
A goodwill credit call is not permitted if the sum of the customer's recent goodwill credit total and the proposed amount exceeds fifty thousand pence.
A refund call is not permitted if the affected customer's vulnerable flag is set to true and the proposed amount exceeds twenty thousand pence.
```

Seven rules. All are scalar boolean/arithmetic expressions; none requires global constraints or vector indexing. All seven should be formalized via Pattern A's direct-evaluation cheap check.

---

## File 4: `tools.json`

```json
{
  "tools": [
    {
      "name": "apply_refund",
      "parameters": {
        "transaction_id": "str",
        "amount_pence": "int",
        "refund_type": "enum:MERCHANT_REFUND|GOODWILL_CREDIT",
        "reason": "str"
      },
      "is_gated": true
    },
    {
      "name": "lookup_bundle",
      "parameters": {
        "transaction_id": "str"
      },
      "is_gated": false
    }
  ]
}
```

---

## File 5: `fixtures/per_rule.py`

For each rule, a small set of (state, expected) pairs the per-rule cheap-checks evaluate against.

```python
PER_RULE_FIXTURES = {
    "rule_1": [  # transaction must be POSTED
        ({"transaction_status": 0, "refund_call_amount_pence": 1000, "refund_call_type": 0,
          "customer_kyc_status": 0, "customer_vulnerable_flag": False,
          "customer_recent_goodwill_total": 0, "account_has_sanctions_block": False,
          "transaction_amount_pence": 5000}, True),
        ({"transaction_status": 1, "refund_call_amount_pence": 1000, "refund_call_type": 0,
          "customer_kyc_status": 0, "customer_vulnerable_flag": False,
          "customer_recent_goodwill_total": 0, "account_has_sanctions_block": False,
          "transaction_amount_pence": 5000}, False),
    ],
    "rule_2": [  # KYC must not be FAILED
        ({"customer_kyc_status": 0, "transaction_status": 0, "refund_call_amount_pence": 1000,
          "refund_call_type": 0, "customer_vulnerable_flag": False,
          "customer_recent_goodwill_total": 0, "account_has_sanctions_block": False,
          "transaction_amount_pence": 5000}, True),
        ({"customer_kyc_status": 1, "transaction_status": 0, "refund_call_amount_pence": 1000,
          "refund_call_type": 0, "customer_vulnerable_flag": False,
          "customer_recent_goodwill_total": 0, "account_has_sanctions_block": False,
          "transaction_amount_pence": 5000}, False),
    ],
    # ... one entry per rule, 2-5 fixtures each
}
```

The full fixture file should have 2–5 entries per rule, exercising positive and negative cases at relevant boundaries.

---

## File 6: `fixtures/properties.py`

Hypothesis-style property predicates. Authored by the user; pipeline runs them but does not generate them.

```python
from hypothesis import given, strategies as st

# Property: any state where KYC is FAILED must result in rule_2 being False.
def property_kyc_failed_blocks_refund(rule_2_eval, state_with_kyc_failed):
    assert rule_2_eval(state_with_kyc_failed) is False

# Property: rule_5 (goodwill > 10000) depends only on refund_call_amount_pence
# and refund_call_type, not on any other field.
def property_rule_5_dependencies(rule_5_eval, two_states_differing_only_in_kyc):
    s1, s2 = two_states_differing_only_in_kyc
    assert rule_5_eval(s1) == rule_5_eval(s2)
```

---

## What the pipeline produces from these inputs

After the orchestrator runs successfully:

- `policy.py` containing the seven verified rules as named CPMpy expressions, plus a `legal(state, call)` predicate.
- `manifest.json` mapping each rule ID to its NL source, dependency list, and routing flags (`uses_global_constraints: False`, `uses_vector_variables: False` for all seven rules in this domain).
- `consistency_report.json` confirming the policy is satisfiable, all rules reachable, no pairwise conflicts.
- `verification_log.jsonl` with the audit trail of every check run.

The runtime then loads `policy.py` and gates `apply_refund` calls against it, using Pattern A for all seven rules (since none uses global constraints or vector variables).

---

## A sketch of what a vector/global second domain looks like

For full v1 success criteria, a second example domain must exercise the parts this refund domain doesn't. A minimal candidate: a meeting-room booking agent with rules like "no two bookings on the same day-and-room may overlap." This requires:

- A vector field `bookings_room` (which room is each booking in) and `bookings_start_time` / `bookings_end_time`.
- A global constraint usage — likely `Cumulative` for capacity or `AllDifferent` for unique slot assignment.
- Comprehension-based rules iterating over the bookings collection.

The signature for such a domain populates section 4 (vector fields) and section 7 (`DOMAIN_DIMENSIONS`, `TEST_SHAPE_BOUNDS`); the rules use comprehensions and at least one global constraint; the runtime routes those rules to Pattern B; the formalizer's few-shot examples include vector and global samples.

This second domain is not provided in v1; it is the test for whether the pipeline truly handles the full scope.

---

## Adding a new domain

1. Create `domains/<new_domain>/`.
2. Author the five input files following the templates above and the eight-section signature schema.
3. Run the orchestrator pointed at the new domain directory.
4. Verify all v1 success criteria pass.

If the pipeline can do this on a domain with vector fields and global constraints without code changes, the generalist claim holds.
