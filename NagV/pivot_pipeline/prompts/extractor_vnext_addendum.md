# Extract addendum — vNext expansion templates (optional)

Use these **only when** the policy line clearly matches the pattern **and** caps below are satisfied. Otherwise encode with **core eight** templates (`LOGICAL_IMPLICATION`, `CONSTANT_RELATIONAL`, …) from the main extractor spec.

**Compile path:** expansion rules are **lowered to core IR** before Z3; you may keep expansion shape in extract output.

## Allowed expansion `template_class` values (exact spelling)

`INT_RANGE`, `DECISION_TABLE_ROW`, `TABLE_BLOCK`, `BOUNDED_FORALL`, `K_OF_N`, `EXHAUSTIVE_SWITCH`, `DEFINED_AS`, `SUM_THRESHOLD`

Do **not** invent other names. Still **ABORT** for unbounded domains, infinite quantification, or constructs outside core + this list.

## When to prefer expansion vs core

| NL pattern | Prefer | Not |
|------------|--------|-----|
| Integer in inclusive range `[lo, hi]` | `INT_RANGE` | Two separate `CONSTANT_RELATIONAL` unless trivial |
| Single table row: if trigger then require | `DECISION_TABLE_ROW` | — |
| Multiple rows same table / shared `applies_to` | `TABLE_BLOCK` (`rows[]`) | Many unrelated rule ids |
| “For each role in {A,B,…}” finite set | `BOUNDED_FORALL` | Open-ended “for all users” |
| “At least **k** of **n** conditions” / k-of-n | `K_OF_N` | Giant hand-built `and`/`or` only if n ≤ 3 and k small |
| Switch / case on enum discriminant | `EXHAUSTIVE_SWITCH` | Unrelated implications |
| “Variable X is defined as …” | `DEFINED_AS` | — |
| Sum of weighted terms vs limit (e.g. 2·a + 3·b ≤ L) | `SUM_THRESHOLD` | Chaining many `ARITHMETIC_EVALUATION` rules |

## Caps (hard — exceeding → ABORT or split lines)

| Template | Cap |
|----------|-----|
| `INT_RANGE` | `lo ≤ hi`; span within engine limit |
| `TABLE_BLOCK` | ≤ **32** rows |
| `BOUNDED_FORALL` | domain list ≤ **32** values |
| `K_OF_N` | **1 ≤ k ≤ n**, **n ≤ 10** clauses |
| `EXHAUSTIVE_SWITCH` | ≤ **32** cases; distinct case values |
| `SUM_THRESHOLD` | **1–4** terms (`terms[]`); each `coeff` bounded; **never 5+ terms** — split into another rule line |
| `DEFINED_AS` | acyclic definition; `ConditionExpr` depth ≤ 8 |

## `SUM_THRESHOLD` (normative)

- `terms`: `[{ "coeff": <int>, "variable": "<slug>" }, ...]` — **at most 4** entries.
- `relational_operator`: `EQ` | `NEQ` | `LT` | `LTE` | `GT` | `GTE`
- `limit`: integer constant
- `yields`: `SATISFIED` | `UNSATISFIED` (default `SATISFIED`)

Example (three terms):

```json
{
  "template_class": "SUM_THRESHOLD",
  "terms": [
    { "coeff": 2, "variable": "units" },
    { "coeff": 3, "variable": "hours" },
    { "coeff": 1, "variable": "fee" }
  ],
  "relational_operator": "LTE",
  "limit": 100,
  "yields": "SATISFIED"
}
```

## `K_OF_N` (minimal)

For **GLOBAL** mandatory NL (“every applicant must satisfy at least k of n”), include **`result_variable`** on the same rule (Way B — do not add a second rule for the same NL line):

```json
{
  "rule_id": "R0007",
  "template_class": "K_OF_N",
  "applies_to": "GLOBAL",
  "k": 2,
  "result_variable": "meets_example_requirement",
  "clauses": [
    { "kind": "atom", "variable": "a", "operator": "EQ", "value": 1 },
    { "kind": "atom", "variable": "b", "operator": "EQ", "value": 1 },
    { "kind": "atom", "variable": "c", "operator": "EQ", "value": 1 }
  ]
}
```

(Full field list per template: see `prompts/vnext_template_examples.md` in repairer bundle; extract uses same shapes.)
