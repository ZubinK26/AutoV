# CrossCritic — JSON / schema repair

You fix **one** invalid CrossCritic model output so it becomes a **single** valid JSON object matching the cross-critic report schema.

## Rules (strict)

1. Output **only** one JSON object. **No** markdown fences, **no** prose before or after, **no** comments.
2. **Preserve** audit intent from the invalid output where readable; do **not** invent new findings unrelated to the original text.
3. **Escape** all JSON string values: use `\"` for internal double quotes; never leave an unterminated string.
4. Required top-level fields:
   - `verdict`: `"PASS"` or `"ISSUES"`
   - `compared_against`: `"processed_nl_and_linearized_model"`
   - `findings`: array (empty if `verdict` is `PASS`)
5. Each finding object (when present):
   - `id`: string (e.g. `"X001"`)
   - `severity`: `"info"` | `"warn"` | `"critical"`
   - `category`: `"outcome_split"` | `"preemption"` | `"inconsistency"` | `"other"`
   - `rule_ids`: array of strings (may be empty)
   - `explanation`, `recommendation`: strings (may be empty)
6. `audit_trail_bullets`: array of strings (may be empty).
7. `notes`: optional string.
8. Do **not** return a bare JSON array — wrap findings in the object above.

## Common fixes

- Model returned only a `findings` array → wrap with `verdict`, `compared_against`, etc.
- Unescaped `"` inside `explanation` → escape or shorten.
- Trailing comma, missing `}`, truncated output → complete the object.
- Wrong enum → use allowed literals exactly.

---

## Invalid model output (trimmed; may be empty if parse failed early)

<<<INVALID_OUTPUT>>>

## Diagnostic (machine-generated; fix these issues)

<<<DIAGNOSTIC>>>
