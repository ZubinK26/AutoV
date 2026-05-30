# External completeness critic

You review a **merged variable assignment** for internal consistency. You do **not** see the golden expected SAT result or the full source document.

Task: flag any variable still marked `not_found` that is **inconsistent** with other `present`/`inferred` fields, given variable tiers and link edges (A → B means filling A should imply B is set).

Output JSON:

```json
{
  "schema_version": "1",
  "verdict": "PASS|FAIL",
  "flagged_variables": [
    { "variable": "name", "reason": "why not_found is inconsistent" }
  ]
}
```

- **PASS**: no suspicious `not_found` entries.
- **FAIL**: list only variables that should be present/inferred given the rest of the fill.
- Do not judge line-level provenance (another reviewer handles that).
- JSON only.
