# Pivot WFM chunk scope rewrite

Pivot WFM (Phase 0) produced a handoff that **does not cover every rule line** in this chunk: some global indices are missing from PASS/REWRITE rows, BLOCK/OUT_OF_SCOPE, merged, or dropped.

Rewrite the **whole chunk** so each rule line is independently expressible for pivot profile WFM (clear, one main constraint per line where possible; avoid packing multiple independent obligations into one English sentence unless the source already does so compactly).

## File / indices

- **File label:** <<<FILE_LABEL>>>
- **Global 0-based indices in this chunk:** <<<CHUNK_INDEX_RANGE>>>
- **Number of rules (must preserve):** <<<CHUNK_RULE_COUNT>>>

## Current rules (in order)

<<<CHUNK_RULES_JSON_ARRAY>>>

## Coverage diagnostics

<<<COVERAGE_SUMMARY>>>

## Handoff row summary (from WFM JSON)

<<<HANDOFF_LINE_SUMMARY>>>

## Normative v1 encodability (shared with extract)

Rewrites must keep each line **encodable** under this contract (same limits as pivot extract):

<<<V1_ENCODABILITY>>>

## Output

Return **only** a JSON object (no markdown, no code fences). Keys:

- `rewritten_rules`: array of strings — length must match <<<CHUNK_RULE_COUNT>>>.
- `semantic_notes`: optional array of strings — brief meaning tradeoffs per rewrite if any.

**Requirements:**

- `rewritten_rules` length **must equal** <<<CHUNK_RULE_COUNT>>> (same order as the current rules).
- Each string is one English policy rule line (same meaning as the input at that position, modulo explicit notes).
- Prefer wording that avoids OUT_OF_SCOPE in pivot WFM (no unsupported arithmetic, no variable×variable products, etc.).
