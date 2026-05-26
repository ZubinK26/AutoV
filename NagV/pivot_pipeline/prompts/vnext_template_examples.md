# vNext expansion templates — minimal valid examples

Used by extract/repair prompts. All rules include `rule_id`, `applies_to` (`GLOBAL` default), optional `overrides`. Compile lowers these to **core eight** before Z3.

**`SUM_THRESHOLD`:** at most **4** terms in `terms[]` (never 5+).

### `INT_RANGE`

```json
{ "rule_id": "R0001", "template_class": "INT_RANGE", "variable": "score", "lo": 0, "hi": 100, "yields": "SATISFIED" }
```

### `DECISION_TABLE_ROW`

```json
{
  "rule_id": "R0002",
  "template_class": "DECISION_TABLE_ROW",
  "trigger_condition": { "kind": "atom", "variable": "flag", "operator": "EQ", "value": 1 },
  "required_condition": { "kind": "atom", "variable": "outcome", "operator": "GTE", "value": 0 }
}
```

### `TABLE_BLOCK`

```json
{
  "rule_id": "R0003",
  "template_class": "TABLE_BLOCK",
  "table_id": "T1",
  "rows": [
    {
      "trigger_condition": { "kind": "atom", "variable": "a", "operator": "EQ", "value": 1 },
      "required_condition": { "kind": "atom", "variable": "b", "operator": "EQ", "value": 1 }
    }
  ]
}
```

### `BOUNDED_FORALL`

```json
{
  "rule_id": "R0004",
  "template_class": "BOUNDED_FORALL",
  "iter_variable": "role",
  "domain": ["admin", "user"],
  "required_condition": { "kind": "atom", "variable": "role", "operator": "NEQ", "value": "" }
}
```

### `K_OF_N`

```json
{
  "rule_id": "R0005",
  "template_class": "K_OF_N",
  "k": 2,
  "clauses": [
    { "kind": "atom", "variable": "p", "operator": "EQ", "value": 1 },
    { "kind": "atom", "variable": "q", "operator": "EQ", "value": 1 }
  ]
}
```

### `EXHAUSTIVE_SWITCH`

```json
{
  "rule_id": "R0006",
  "template_class": "EXHAUSTIVE_SWITCH",
  "discriminant_variable": "mode",
  "cases": [
    {
      "value": "ON",
      "consequence": { "kind": "atom", "variable": "active", "operator": "EQ", "value": 1 }
    }
  ],
  "default_consequence": { "kind": "atom", "variable": "active", "operator": "EQ", "value": 0 }
}
```

### `DEFINED_AS`

```json
{
  "rule_id": "R0007",
  "template_class": "DEFINED_AS",
  "variable": "threshold",
  "definition": { "kind": "atom", "variable": "threshold", "operator": "GTE", "value": 5 }
}
```

### `SUM_THRESHOLD` (multi-term, max 4)

```json
{
  "rule_id": "R0008",
  "template_class": "SUM_THRESHOLD",
  "terms": [
    { "coeff": 2, "variable": "units" },
    { "coeff": 1, "variable": "hours" }
  ],
  "relational_operator": "LTE",
  "limit": 100,
  "yields": "SATISFIED"
}
```
