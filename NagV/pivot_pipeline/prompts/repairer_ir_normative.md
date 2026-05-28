# Pivot IR — normative shape (repairer / test-repairer)

Apply **minimal edits** valid for `pivot_pipeline.ir` / `load_rules_and_compile`. Do **not** invent fields or types the schema does not allow.

## Forbidden / ignored fields (denylist)

These keys are **never** valid on **rule** objects (any `template_class`). The loader **drops** unknown keys, but you must **not** rely on that — omit them so the repair is stable:

- `description`, `summary`, `notes`, `comment`, `explanation`, `rationale`, `natural_language`, `nl_text`, `prose`, `name`, `title`
- `metadata`, `extra`, `tags`, `annotations`
- `action`, `target_rule_id` on any rule whose `template_class` is **not** `PREEMPTION`
- Any parallel array of triggers/requireds at the rule top level (use `trigger_condition` / `required_condition` only on `LOGICAL_IMPLICATION`)

**Allowlisted prose:** Only `evaluation_pathways[].description` exists in compiled meta-scheme, and you output **rules only** — pathways are derived. **Do not** stuff NL summaries into rule objects; fix **logic** (`trigger_condition`, `required_condition`, `PREEMPTION`, sorts) instead.

## Allowed keys per `template_class` (core v1)

Each **core** rule object may include **only** `BaseRule` fields plus the template’s fields:

- **Common:** `rule_id`, `applies_to` (default `GLOBAL`), `overrides` (optional), `template_class`
- **CONSTANT_RELATIONAL:** `variable`, `relational_operator`, `constant_value`, `yields` (**required** string: `"SATISFIED"` or `"UNSATISFIED"`)
- **SET_INCLUSION:** `variable`, `inclusion_operator`, `constant_array`, `yields` (same)
- **VARIABLE_RELATIONAL:** `left_variable`, `relational_operator`, `right_variable`, `yields` (same)
- **ARITHMETIC_EVALUATION:** `operand_1`, `math_operator`, `operand_2`, `relational_operator`, `target_limit`, `yields` (same)
- **LOGICAL_IMPLICATION:** `trigger_condition`, `required_condition` (each a single condition tree)
- **PREEMPTION:** `preempting_condition`, `action`, `target_rule_id` (one string or null)
- **EXCLUSIVE_CHOICE:** `mode`, `variables`
- **LOGICAL_IFF:** `left`, `right`

### Minimal shape examples (illustrative)

`LOGICAL_IMPLICATION`:

```json
{
  "rule_id": "R0001",
  "template_class": "LOGICAL_IMPLICATION",
  "applies_to": "GLOBAL",
  "trigger_condition": { "kind": "atom", "variable": "x", "operator": "EQ", "value": true },
  "required_condition": { "kind": "atom", "variable": "y", "operator": "GTE", "value": 3 }
}
```

`PREEMPTION` — single string target:

```json
{
  "rule_id": "R0009",
  "template_class": "PREEMPTION",
  "applies_to": "GLOBAL",
  "preempting_condition": { "kind": "atom", "variable": "vip", "operator": "EQ", "value": true },
  "action": "BYPASS_RULE",
  "target_rule_id": "R0005"
}
```

## v1 IR shape (normative)

- **`PREEMPTION`:** `target_rule_id` is **exactly one string**. To bypass **several** earlier rules with the **same** `preempting_condition`, output **several `PREEMPTION` rules**—one per target id. There is no multi-target field.
- **`PREEMPTION` target:** Must name an **earlier** rule whose `template_class` is **not** `PREEMPTION`.
- **One `rule_id` per rule**; no duplicate ids.
- **`LOGICAL_IMPLICATION`:** Exactly one `trigger_condition` and one `required_condition`. Each condition tree uses **only** `ConditionExpr` nodes: `atom`, `varcmp`, `varprod_cmp`, `and`, `or`, `not`. **Never** embed `k_of_n`, `SUM_THRESHOLD`, or any other **rule-level** vNext template inside `trigger_condition` / `required_condition` — `K_OF_N` etc. are separate rules with their own `template_class`.
- **`SET_INCLUSION`:** Only `constant_array` holds a list of allowed/forbidden **values**—not rule ids, not condition trees.
- **Scalars:** Keep scalar fields scalar per the closed IR model.

## vNext templates (assessment / lowering)

- **`K_OF_N`:** `k`, `clauses`, optional **`result_variable`** (aggregate boolean set true when ≥k clauses hold). **Not** `variable`, **not** `yields` at rule top level.
- Wiring gatekeepers: set `result_variable` on the `K_OF_N` rule **or** add **`LOGICAL_IMPLICATION`** / **`CONSTANT_RELATIONAL`** companion rules. Invalid keys are **dropped on sanitize**; repairs that only add dropped keys fail validation.
- Linearized assessment view shows `assigns result → <name>` or `no result_variable` for each `K_OF_N` — match that contract after repair.
