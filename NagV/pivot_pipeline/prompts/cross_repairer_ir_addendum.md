# CrossRepairer — cross-rule coherence encoding

## Scope

- Repair **only** findings in `handoff.findings` / `approved_finding_ids`.
- **Never** implement items in `ignored_finding_ids` or findings omitted from the handoff.
- Do **not** broaden into per-rule NL↔linearized content fixes (Test-Repairer) or semantic critic synthetic drift (Repairer_Piv semantic).

## Rule ids and policy size

- **Do not invent new `rule_id` values** (no suffix ids like `R0029_a`). Edit existing rules only unless compile absolutely requires a new id (rare; prefer wiring existing variables).
- Your output **`rules`** array must include **every** `rule_id` from the input payload (same count; one id each).
- **Only edit** rules listed in `focus_rule_ids`; return **stubs unchanged** for all other ids.

## Cross-family edits (outcome_split / escalation / rejection)

- When a finding names `rule_ids` in one **semantic family** (escalation, rejection/veto, minimum-criteria aggregate), align variables **within that family only** — e.g. use the same consequent variable R0030–R0033 and R0037 already agree on.
- **Do not** rewrite unrelated numeric limits, `K_OF_N` blocks, or entity-scoped work-sample rules unless those `rule_ids` are **explicitly** in the finding.
- Prefer **renaming / aligning a variable in listed rules** over adding a new aggregate definition rule unless the finding and NL clearly require aggregation.

## `LOGICAL_IMPLICATION` triggers — **never nest vNext inside `ConditionExpr`**

**Compile will reject** any `trigger_condition` or `required_condition` node with `"kind": "k_of_n"` (or any other vNext / rule-level template). Condition trees allow **only**:

`atom`, `varcmp`, `varprod_cmp`, `and`, `or`, `not`

### Forbidden (common CrossRepairer mistake)

```json
"trigger_condition": {
  "kind": "or",
  "children": [
    { "kind": "atom", "variable": "resume_count", "operator": "GTE", "value": 1 },
    { "kind": "k_of_n", "k": 3, "clauses": [ ... ] }
  ]
}
```

`K_OF_N`, `SUM_THRESHOLD`, `TABLE_BLOCK`, etc. are **separate rules** with `"template_class": "K_OF_N"` at the **rule** level — never pasted into an `and` / `or` under `LOGICAL_IMPLICATION`.

### Correct pattern for aggregate / gatekeeper rules (e.g. `advance_to_recruiter_review`)

When a finding says wire minimum criteria, escalation, or missing-info into **R0036 / R0037** (or similar aggregates):

1. **Add conjuncts** to the existing `trigger_condition` `and` / `or` using **`atom` only** — e.g. `meets_two_year_customer_operations_experience_requirement` **EQ** `true`, `missing_information_count` **EQ** `0`, `answer_submitted` **EQ** `true`, `escalation_condition_applies` **EQ** `false` (or as NL requires).
2. Use **variable names already present** in the payload / linearized excerpt / cited rules. **Do not invent** new `rule_id` values to host a `K_OF_N` block inside a gatekeeper.
3. **`K_OF_N` → aggregate boolean wiring (critical):** `K_OF_N` rules support **`result_variable`** only (optional string). They **cannot** use top-level `variable`, `yields`, or prose fields — the loader **silently drops** those keys and the repair round will **fail validation**.
   - To connect a `K_OF_N` block to booleans used in gatekeeper triggers: set `"result_variable": "<boolean_name>"` on that `K_OF_N` rule (same name R0036/R0037 already reference).
   - For **`yields SATISFIED`** enforcement like experience rules: add a separate **`CONSTANT_RELATIONAL`** rule (new `rule_id` only if unavoidable) on that boolean, or a **`LOGICAL_IMPLICATION`** companion — **not** `yields` on `K_OF_N`.
   - **Never** claim in `change_summary` that you “added variable/yields to K_OF_N” unless `result_variable` or companion rules are actually present.
4. If gatekeepers already reference a boolean but the linearized line says **`no result_variable`**, edit the cited **`K_OF_N` `rule_id`** (set `result_variable`) — do **not** only add `atom` conjuncts on gatekeepers without defining the boolean.
5. For **`outcome_split` / `yields SATISFIED`** findings on competency: add **`CONSTANT_RELATIONAL`** companion rule(s) on the wired boolean; do not paste `yields` onto `K_OF_N`.

### After a compile error mentioning `k_of_n` in `trigger_condition`

Strip every nested `k_of_n` (and any non–ConditionExpr `kind`) from the failing rule’s trees; replace with **`atom`** conjuncts on the **same boolean variables** the policy already uses elsewhere.

## Focused payload (`focus_rule_ids`)

- Full rule bodies appear only for `focus_rule_ids`; other rules are **stubs** (`_payload_stub: true`).
- Echo stubs **verbatim** (same fields); do not expand stubs into full rules in the output unless that id is in `focus_rule_ids`.

## change_summary

- Each entry: `{ "finding_id": "X001", "rule_id": "R0037", "change": "..." }`.
- Every `finding_id` must be in `approved_finding_ids`.
- One finding → minimal edits; do not merge unrelated findings into one rewrite.
- Describe **concrete IR fields** changed (`result_variable`, `trigger_condition` conjuncts, new `CONSTANT_RELATIONAL` rule). Narrative-only summaries that do not change focus rules are rejected.

## `K_OF_N` allowed fields (vNext)

- **Allowed:** `rule_id`, `template_class`, `applies_to`, `overrides`, `k`, `clauses`, `result_variable` (optional).
- **Forbidden on `K_OF_N`:** `variable`, `yields`, `trigger_condition`, `required_condition`, and any denylist prose keys from `repairer_ir_normative.md`.
