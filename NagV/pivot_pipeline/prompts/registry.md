# Identifier registry (batch)

You receive numbered English policy lines and JSON for rules already extracted (abbreviated listing of variable names in use).

Propose a **canonical variable registry**: synonymous phrases or alternate slugs should map to **one** canonical `snake_case` id.

## Output

Return **only** JSON (no markdown). Shape:

{ "canonical_variables": [ { "id": "days_since_purchase", "aliases": ["days", "num_days"], "line_hints": [1] } ] }

- `id`: canonical `snake_case` name; prefer reusing names already present in `used_slugs` when they mean the same thing.
- `aliases`: strings (spaces or underscores ok) that should normalize to `id`.
- `line_hints`: optional 1-based line indices.

If no aliasing is needed: { "canonical_variables": [] }

## Numbered lines

<<<NUMBERED_LINES>>>

## Used slugs (from extraction)

<<<USED_SLUGS>>>
