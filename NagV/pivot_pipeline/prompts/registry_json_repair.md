# Registry pass — JSON repair

You fix **one** invalid registry model output so it becomes a **single** valid JSON object for the identifier registry schema.

## Rules (strict)

1. Output **only** one JSON object. **No** markdown fences, **no** prose before or after.
2. **Escape** all JSON string values; never leave an unterminated string.
3. Top-level object must include **`canonical_variables`**: an array of objects, each with:
   - `id`: string (canonical variable slug)
   - `aliases`: optional array of strings
4. Preserve intent from the invalid output where readable; align entries to **`used_slugs`** in the diagnostic when obvious.
5. Do **not** add unrelated top-level keys.

## Common fixes

- Unescaped `"` inside descriptions → escape or shorten.
- Truncated output → close arrays and objects.
- Missing `canonical_variables` → build minimal entries for each slug that needs a canonical id.

---

## Used slugs (from IR)

<<<USED_SLUGS>>>

## Numbered policy lines (excerpt)

<<<NUMBERED_LINES>>>

## Invalid registry output (trimmed)

<<<INVALID_OUTPUT>>>

## Diagnostic

<<<DIAGNOSTIC>>>
