# External world fill agent

You receive a **numbered source document** and a **variable catalog** for a compiled policy.
Output **one JSON object** matching `ExternalWorldFillV1` (schema_version `"1"`).

## Default: whole-policy compatibility (`scenario`)

Predict whether the **full compiled policy** can hold together with the facts you extract, after execute-time defaults for unstated fields.

At execute time, every `not_found` variable becomes **bool `false`** or **int `0`** (closed-world defaults). Your `assignments` must still list every catalog variable; use `not_found` when the document gives no basis.

**`golden.sat`:**

| Value | Meaning |
|-------|---------|
| `true` | This case should be **compatible** with the full policy (policy ∧ world is satisfiable). |
| `false` | These facts should **contradict** the policy (no satisfying completion under defaults). |

Do **not** include `query` when `template_kind` is `"scenario"`.

```json
{
  "schema_version": "1",
  "instance_id": "<id>",
  "template_kind": "scenario",
  "golden": { "sat": true },
  "assignments": [
    {
      "variable": "<name>",
      "sort": "int|bool",
      "status": "present|inferred|not_found",
      "value": 0,
      "provenance": { "line_numbers": [1], "quotes": ["verbatim excerpt"] },
      "rationale": "one sentence"
    }
  ]
}
```

## Legacy: single-rule probe (`decision_query`)

Only when explicitly asked for `decision_query` mode:

```json
{
  "schema_version": "1",
  "instance_id": "<id>",
  "template_kind": "decision_query",
  "query": { "decision_metric": "rule", "rule_id": "R0001" },
  "golden": { "decision": "satisfied" },
  "assignments": [ "... same assignment rules ..." ]
}
```

Use the supplied active rule id list for `query.rule_id`. Unmentioned variables are **omitted** from the Z3 world (solver free) in this mode only.

## Assignment rules (all modes)

1. **Every catalog variable** must appear exactly once in `assignments`.
2. **`present`**: value stated explicitly in cited lines.
3. **`inferred`**: value follows clearly from cited lines; cite the lines you used.
4. **`not_found`**: no basis in the document; omit `value`; empty `provenance`.
5. **Line numbers** are 1-based (`L1:`, `L2:` prefixes).
6. Use **only** variable names from the catalog.
7. Do **not** invent values without cited support — use `not_found`.
8. Output **JSON only** (no markdown fences).
