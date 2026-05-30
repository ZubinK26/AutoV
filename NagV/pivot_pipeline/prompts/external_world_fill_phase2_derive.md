# External world fill — phase 2 (derived tier)

You receive **phase 1 grounded assignments** and a **rule glossary**. You do **not** receive the source document.

Set **derived** variables only: outcomes and aggregates defined by the compiled policy (implication heads, K-of-N results, bool flags fixed by relational rules).

Output JSON:

```json
{
  "schema_version": "1",
  "assignments": [
    {
      "variable": "<name>",
      "sort": "int|bool",
      "status": "present|inferred",
      "value": true,
      "provenance": { "line_numbers": [1], "quotes": ["DERIVED: rule R0007 from b2b_saas_experience_years=3"] },
      "rationale": "DERIVED: one sentence referencing rule ids and phase-1 variables"
    }
  ]
}
```

## Rules

1. Output **only** variables listed for this phase.
2. Use **`inferred`** when value follows from phase-1 facts + glossary rules.
3. Use **`present`** only if phase-1 facts directly encode the outcome (rare).
4. **Do not** use `not_found` — every listed variable must have a value.
5. Provenance: `line_numbers` may be `[1]`; `quotes` must start with `DERIVED:` and cite rule ids / phase-1 variable names (no document lines).
6. JSON only.
