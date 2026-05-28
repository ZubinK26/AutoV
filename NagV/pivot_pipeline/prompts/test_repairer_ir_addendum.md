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
- Your output **`rules`** array must include **every** `rule_id` from the input (same count and order).
- **Only edit** rules in `focus_rule_ids`; return stubs **unchanged** for all other ids.
