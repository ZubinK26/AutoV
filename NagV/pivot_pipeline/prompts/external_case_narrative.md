# External case — operator narrative

Summarize policy-case evaluation for a busy reviewer.

## Input

JSON bundle with:

- `pathway_id`, `tier1_complete`, `missing` variables
- tier-1 strict compatibility (if run)
- tier-2 programmatic summary (if any)
- tier-3 speculative suggestions (if any)

## Output

Write plain Markdown (no JSON):

1. **Document evaluation (tier 1)** — what was extracted, what is missing for a real verdict, and the strict compatibility result if tier-1 ran.
2. **Programmatic what-if (tier 2)** — which gaps were filled by rules and the hypothetical compatibility.
3. **Speculative guesses (tier 3)** — list guesses with line cites; stress they are **not provenance-verified**.

Keep under 400 words. Use bullet lists for missing variables.
