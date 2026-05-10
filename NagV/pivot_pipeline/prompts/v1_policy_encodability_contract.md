# Normative v1 policy encodability (Pivot pipeline)

**Single contract** for **Phase 0 WFM (pivot profile)**, **extract**, **chunk scope rewrite**, and **extract ABORT scope rewrite**. Wording may differ; **semantic limits** must match.

## IR templates (pivot v1)

### `template_class` is a closed vocabulary

Only these **eight** values are valid — spell them **exactly** (uppercase, underscores as shown):

`CONSTANT_RELATIONAL`, `SET_INCLUSION`, `VARIABLE_RELATIONAL`, `ARITHMETIC_EVALUATION`, `LOGICAL_IMPLICATION`, `PREEMPTION`, `EXCLUSIVE_CHOICE`, `LOGICAL_IFF`.

**There are no other** `template_class` values in v1. Natural-language phrases that *sound* like templates (“decision rule”, “access rule”, “constraint type”, “policy block”, etc.) **must not** appear as `template_class`. Encode meaning with the list above — most conditional obligations use **`LOGICAL_IMPLICATION`** and nested **`ConditionExpr`**. If a line cannot be encoded without inventing a new class name, extract must respond **`ABORT: Ruleset exceeds decidable scope.`** (not a fabricated type).

Nested conditions use **`ConditionExpr`** with `kind`: `atom`, `varcmp`, `varprod_cmp`, `and`, `or`, `not` — **max depth** equals `CONDITION_EXPR_MAX_DEPTH` in code (currently **8**).

## Arithmetic (strict)

- **`ARITHMETIC_EVALUATION`** is **linear for multiply**: **`MULTIPLY`** cannot have `operand_2` as another variable name string (operand_2 must be numeric or use non-`MULTIPLY` ops with variables as today).
- **Variable × variable** (single product per rule): use **`ConditionExpr`** with **`kind`: `varprod_cmp`**: `left_variable`, `right_variable`, `operator` (`EQ`, `NEQ`, `LT`, `LTE`, `GT`, `GTE`), **`rhs`** either `{ "kind": "const", "value": <int> }` or `{ "kind": "var", "variable": "<slug>" }`. **At most one** `varprod_cmp` node in **each** rule’s condition trees (trigger + required + … combined). Factors/rhs variable must **not** be variables listed in **`EXCLUSIVE_CHOICE`**. Engine assumes **nonnegative integers** and applies **hard bounds** `0 … PIVOT_PRODUCT_INT_CAP` (default **1_000_000**) on every int variable that appears in a `varprod_cmp` for **Z3** (see `DEFAULT_PIVOT_PRODUCT_INT_CAP` / env in code).
- **Division**: divisor must be numeric — not an unknown variable.

## PREEMPTION

For `BYPASS_RULE`, `FORCE_SATISFIED`, `FORCE_UNSATISFIED`: **`target_rule_id` required**, must be an **earlier** rule id (`R0001`…), and **must not** point at another `PREEMPTION`.

## Consistency rule for NL authors and agents

If WFM or rewrite steps produce English that **still** states a construct **outside** this contract (e.g. **multiple distinct products in one rule**, product of **boolean choice** fields, or **`ARITHMETIC_EVALUATION` `MULTIPLY`** with two variables), **extract may ABORT** or repair will force a rewrite. Prefer WFM/Agent 3 text that is already **encodable**—including **at most one** variable×variable comparison via **`varprod_cmp`** when needed—not merely “passed” in prose.
