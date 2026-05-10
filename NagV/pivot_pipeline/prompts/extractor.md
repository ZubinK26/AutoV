# Pivot NL → one rule JSON object (v1 IR)

The pipeline appends a **Normative v1 encodability** block (from `v1_policy_encodability_contract.md`, same text as pivot Phase 0 WFM Agents 2–3) after this file so extract and WFM stay aligned.

You convert **one** English policy line into **one** JSON object for the Pivot IR (see `pivot_pipeline.ir`).

## Output contract

Return **only** JSON: one object. No markdown fences, no commentary.

Required on **every** rule:

- `template_class`: **exactly one** of the strings below — **no other value is valid**. The pipeline rejects invented labels.
  
  **Closed set (copy spelling exactly):**  
  `CONSTANT_RELATIONAL`, `SET_INCLUSION`, `VARIABLE_RELATIONAL`, `ARITHMETIC_EVALUATION`,  
  `LOGICAL_IMPLICATION`, `PREEMPTION`, `EXCLUSIVE_CHOICE`, `LOGICAL_IFF`.

  **Do not** output domain-specific or narrative names (e.g. types of rule *described* in English such as “decision”, “access control”, “constraint template”, “policy fragment”). Those descriptions must be encoded with this **same** closed list — typically **`LOGICAL_IMPLICATION`** (with `ConditionExpr`) for if/then obligations, or **`CONSTANT_RELATIONAL`** / **`VARIABLE_RELATIONAL`** / **`SET_INCLUSION`** / **`ARITHMETIC_EVALUATION`** / **`PREEMPTION`** / **`EXCLUSIVE_CHOICE`** / **`LOGICAL_IFF`** as appropriate. If you cannot encode without inventing a new `template_class`, reply with **`ABORT: Ruleset exceeds decidable scope.`** instead of fabricating a type name.
- `rule_id`: string — a placeholder is fine; the pipeline may overwrite with a fixed id.
- `applies_to`: `"GLOBAL"` or another rule id string this rule is scoped under.
- `overrides`: `null` or a rule id this rule supersedes (optional routing).

Templates (use **exact** key names and enum spellings):

### CONSTANT_RELATIONAL

`variable` (string), `relational_operator` (`EQ`|`NEQ`|`GT`|`LT`|`GTE`|`LTE`), `constant_value` (number|string|boolean), `yields` (`SATISFIED`|`UNSATISFIED`).

### SET_INCLUSION

`variable`, `inclusion_operator` (`IN`|`NOT_IN`), `constant_array` (non-empty array of literals), `yields`.

### VARIABLE_RELATIONAL

`left_variable`, `relational_operator`, `right_variable`, `yields`.

### ARITHMETIC_EVALUATION

`operand_1` (variable name string), `math_operator` (`ADD`|`SUBTRACT`|`MULTIPLY`|`DIVIDE`), `operand_2` (number **or** variable name string), `relational_operator`, `target_limit` (number **or** variable name string), `yields`.  
Use only linear forms allowed by v1 (e.g. no variable×variable for `MULTIPLY`).

### LOGICAL_IMPLICATION

`trigger_condition`, `required_condition` — each a **ConditionExpr** (below).

### PREEMPTION

`preempting_condition` (ConditionExpr), `action` (`FORCE_SATISFIED`|`FORCE_UNSATISFIED`|`BYPASS_RULE`), `target_rule_id`:

- For **`BYPASS_RULE`**, **`FORCE_SATISFIED`**, and **`FORCE_UNSATISFIED`**: **`target_rule_id` is required** — a string equal to the **`rule_id` of an earlier rule** in this same policy (e.g. `R0003`). It **must not** name another **`PREEMPTION`** rule. Do not invent symbolic ids (e.g. `storage_limit_500gb`) unless that literal is the sibling rule's actual `rule_id`.
- Use **`null`** for `target_rule_id` only when no concrete rule is being targeted in a way that matches the extractor examples for your policy (most FORCE/BYPASS lines need a real earlier id).

### EXCLUSIVE_CHOICE

`mode` (`exactly_one`|`at_most_one`), `variables` (array of **at least two** variable name strings).

### LOGICAL_IFF

`left`, `right` — each a ConditionExpr.

## ConditionExpr (nested; max depth per `CONDITION_EXPR_MAX_DEPTH` in code — **8** in v1)

Every node is an object with a **`kind`** field:

- Atom: `{"kind":"atom","variable":"snake_case_name","operator":"EQ"|...,"value": <literal>}`  
  `operator` uses the same relational enum as templates (e.g. `GTE`, not `>=`).
- Compare two variables: `{"kind":"varcmp","left_variable":"...","operator":"EQ"|...,"right_variable":"..."}`.
- **Variable × variable product** (when encodable per contract): `{"kind":"varprod_cmp","left_variable":"...","right_variable":"...","operator":"EQ"|...,"rhs":<object>}` with `rhs` either `{"kind":"const","value":<int>}` or `{"kind":"var","variable":"..."}` — see appended encodability contract; **at most one** `varprod_cmp` in this rule's conditions.
- AND / OR: `{"kind":"and","children":[<ConditionExpr>,...]}` or `{"kind":"or","children":[...]}` — **at least two** children each.
- NOT: `{"kind":"not","child":<ConditionExpr>}`.

Use `snake_case` variable names (e.g. `days_since_purchase`, `refund_amount`).

## Common mistakes (check before you answer)

- **Output shape:** one JSON object only — no markdown fences, no trailing comma, no comments.
- **template_class:** only the **closed list** in **`extractor.md`** / encodability contract — never invent a new class name; map NL to `LOGICAL_IMPLICATION`, `CONSTANT_RELATIONAL`, etc. If impossible without a new type, the correct response is **`ABORT: Ruleset exceeds decidable scope.`** (not a made-up `template_class`).
- **Enums:** uppercase tokens only (`SATISFIED`, `BYPASS_RULE`, `EQ`, …).
- **PREEMPTION:** for `BYPASS_RULE` / `FORCE_*`, always set `target_rule_id` to a **prior** line's `rule_id` (`R0001`…), never to another `PREEMPTION`.
- **ConditionExpr:** every node has `kind`; `and` / `or` need **at least two** children.
- **Number vs string:** use JSON numbers for numeric constants unless the schema expects a variable name string.
- **Quotes in NL:** do not paste raw double quotes inside strings in a way that breaks JSON; escape `\"` inside JSON string values.

## Scope and abstain

If the line is **not** an encodable policy rule, or is out of schema, reply with **exactly**:

`ABORT: Ruleset exceeds decidable scope.`

---

## Input line (verbatim)

<<<LINE>>>
