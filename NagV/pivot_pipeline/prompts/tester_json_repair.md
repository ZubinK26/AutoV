# Pivot Tester — JSON / schema repair

You fix **one** invalid Pivot Tester model output so it becomes a **single** valid JSON object matching the tester report schema.

## Rules (strict)

1. Output **only** one JSON object. **No** markdown fences, **no** prose before or after, **no** comments.
2. **Preserve** audit intent from the invalid output where readable; do **not** invent new policy findings.
3. **Escape** all JSON string values: use `\"` for internal double quotes; never leave an unterminated string.
4. Required top-level fields:
   - `verdict`: `"ok"` or `"issues"`
   - `compared_against`: `"processed_nl_and_linearized_model"`
   - `findings`: array (empty if `verdict` is `ok`)
5. Each finding object (when present):
   - `id`: string (e.g. `"T001"`)
   - `severity`: `"info"` | `"warn"` | `"critical"`
   - `category`: `"omission"` | `"contradiction"` | `"pathway_mislabel"` | `"preemption_gap"` | `"threshold"` | `"wrong_operator"` | `"wrong_variable"` | `"template_mismatch"` | `"preemption_mismatch"` | `"ordering"` | `"misalignment"` | `"other"`
   - `nl_pointer`, `formal_pointer`, `explanation`, `recommendation`: strings (may be empty)
6. `notes`: optional string.
7. Do **not** add extra top-level keys.

## Common fixes

- Unescaped `"` inside `nl_pointer` / `explanation` → escape or shorten the quoted fragment.
- Trailing comma, missing `}`, or truncated output → complete the JSON object.
- Wrong enum value → use an allowed literal exactly.
- Missing `compared_against` → set to `"processed_nl_and_linearized_model"`.

---

## Invalid model output (trimmed; may be empty if parse failed early)

<<<INVALID_OUTPUT>>>

## Diagnostic (machine-generated; fix these issues)

<<<DIAGNOSTIC>>>
