# Test-Repairer — ConditionExpr and template encoding

## `atom` in `LOGICAL_IMPLICATION` (and other condition trees)

- `operator` must be **`EQ`**, **`NEQ`**, **`GT`**, **`LT`**, **`GTE`**, or **`LTE`** only.
- **Never** use `IN` or `NOT_IN` on an `atom` — list membership belongs on a **`SET_INCLUSION`** rule (`inclusion_operator` + `constant_array`).
- Boolean requirement flags in `trigger_condition` / `required_condition` use **`value: true`** or **`value: false`** — **not** `"SATISFIED"` / `"UNSATISFIED"` (those strings are rule-level **`yields`** on relational templates only).

## SET_INCLUSION vs LOGICAL_IMPLICATION (tester pattern)

When a finding asks to align NL “if any of these platforms / categories, set flag X” with the linearized model:

- Prefer **`LOGICAL_IMPLICATION`** with:
  - `trigger_condition`: `or` of `atom` nodes (one per boolean surrogate variable, each `EQ true`), **or** a single triggering atom as NL requires.
  - `required_condition`: `atom` on the flag variable with `operator: "EQ"`, `value: true`.
- You may **keep** an existing **`SET_INCLUSION`** row **and** add a separate **`LOGICAL_IMPLICATION`** that sets the flag when the SET_INCLUSION condition holds — if the finding says the flag is missing downstream.
- Do **not** encode platform/category lists inside an `atom` `value` array.

## Focused payload (`focus_rule_ids`)

- The payload lists **full** rule bodies only for ids in `focus_rule_ids`.
- Other rules appear as **stubs** (`_payload_stub: true`) with only `rule_id`, `template_class`, `applies_to`.
- Your output **`rules`** array must include **every existing** `rule_id` from the input (stubs for non-focus).
- **Default (Way B):** do **not** append new `rule_id`s. When `allow_append_rules` is true, you may append using `suggested_next_rule_ids` (full bodies, not stubs).
- **Only edit** rules in `focus_rule_ids`; return stubs **unchanged** for all other **existing** ids.

## `K_OF_N` (when in focus — critical)

The assessment linearized view shows `no result_variable` or `assigns result → <name>` under each `K_OF_N` block. When a finding cites **missing outcome / yields / enforcement** on `K_OF_N`:

- **`K_OF_N` allowed top-level fields:** `rule_id`, `template_class`, `applies_to`, `overrides`, `k`, `clauses`, optional **`result_variable`** (string).
- **Forbidden on `K_OF_N`:** top-level `variable`, `yields`, `trigger_condition`, `required_condition` — the loader **silently drops** these; the repair round **fails validation** if you only add them.
- **Correct fix (GLOBAL “every applicant” obligations — Way B):**
  1. Set `"result_variable": "<aggregate_boolean>"` on the cited `K_OF_N` rule (same name gatekeepers already reference when present).
  2. Fix `k` and `clauses` to match NL; use snake_case clause variables consistent with the policy.
  3. **Do not** put `yields` or `variable` on `K_OF_N`; compile lowering enforces `result_variable`. **Do not** append a separate `CONSTANT_RELATIONAL` rule for the same NL line unless `allow_append_rules` is true.
  4. Replace `K_OF_N` with `LOGICAL_IMPLICATION` + `or` on the **same `rule_id`** only when NL is **conditional**, not for bare “every applicant has…”.
- **Never** claim in `change_summary` that you “added yields/variable to K_OF_N” unless `result_variable` or companion rules are **actually present** in the emitted JSON.
- Read `repairer_ir_normative.md` vNext section for the same contract CrossRepairer uses.
