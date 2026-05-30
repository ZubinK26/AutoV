# External world fill — phase 1 (grounded only)

You receive a **numbered source document** and a **subset of the variable catalog** (grounded tier only).

Output **one JSON object**:

```json
{
  "schema_version": "1",
  "batch_id": "<batch id>",
  "variables_requested": ["var_a", "var_b"],
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

## Rules

1. Output **only** variables listed under `variables_requested` — one row each, same order as listed.
2. **`present`**: value explicitly in cited lines.
3. **`inferred`**: value clearly follows from cited lines; cite lines used.
4. **`not_found`**: no basis in the document; omit `value`; empty `provenance`.
5. Do **not** invent values — use `not_found` when unsupported.
6. Line numbers are 1-based (`L1:`, `L2:`).
7. JSON only (no markdown fences).
