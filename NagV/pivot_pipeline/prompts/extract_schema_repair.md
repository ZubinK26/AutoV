# Pivot extract — schema / JSON repair (one rule)

You fix **one** invalid model output so it becomes a **single** valid Pivot IR JSON object for the given English line.

## Rules (strict)

1. Output **only** one JSON object. **No** markdown fences, **no** prose before or after, **no** comments.
2. Preserve the **meaning** of the input line. Do not swap triggers, actions, or variables.
3. The pipeline sets `rule_id` to `R` + zero-padded line index; you may omit `rule_id` or leave a placeholder — it will be overwritten.
4. `template_class` must be **literally** one of the eight allowed strings in **`extractor.md`** / encodability contract (`CONSTANT_RELATIONAL`, …, `LOGICAL_IFF`). **Never** invent names for “kinds” of rules described in English; remap to an allowed template (usually `LOGICAL_IMPLICATION` + `ConditionExpr`). If the line cannot be encoded without a new `template_class`, output **`ABORT: Ruleset exceeds decidable scope.`** instead of a fake type.
5. **v1 encodability:** No variable×variable products in `ARITHMETIC_EVALUATION`; use `varprod_cmp` in `ConditionExpr` only as in the contract. PREEMPTION `target_rule_id` rules as in the shared contract appended to the extractor prompt.

## PREEMPTION (common fix)

- For `action` ∈ `BYPASS_RULE`, `FORCE_SATISFIED`, `FORCE_UNSATISFIED`: **`target_rule_id` is required** — a string equal to an **`rule_id` of an earlier rule** in this policy (e.g. `R0003`). It **must not** point at another `PREEMPTION` rule.
- Use `null` **only** for `target_rule_id` when the extractor prompt explicitly allows it for this action (rare in current semantics).

## ConditionExpr

Nested objects must use `kind`: `atom`, `varcmp`, `varprod_cmp` (see contract), `and`, `or`, `not` as in the extractor spec; relational operators are uppercase tokens (`EQ`, `LT`, …).

---

## Original policy line (verbatim)

<<<LINE>>>

## Line index (for rule_id assignment)

<<<LINE_INDEX>>>

## Invalid model output (trimmed; may be empty if parse failed early)

<<<INVALID_OUTPUT>>>

## Diagnostic (machine-generated; fix these issues)

<<<DIAGNOSTIC>>>
