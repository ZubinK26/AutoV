# Pivot WFM chunk scope rewrite

Pivot WFM (Phase 0) produced a handoff that **does not cover every rule line** in this chunk: some global indices are missing from PASS/REWRITE rows, BLOCK/OUT_OF_SCOPE, merged, or dropped.

Rewrite this chunk so each rule line is independently expressible for pivot profile WFM (clear, one main constraint per line where possible; avoid packing multiple independent obligations into one English sentence unless the source already does so compactly).

## File / indices

- **File label:** <<<FILE_LABEL>>>
- **Global 0-based indices in this chunk:** <<<CHUNK_INDEX_RANGE>>>
- **Number of rules (must preserve):** <<<CHUNK_RULE_COUNT>>>

## Authoritative source rules (original NL; meaning anchor)

<<<CHUNK_RULES_JSON_ARRAY>>>

## Working baseline (current text per line for this pass)

<<<WORKING_BASELINE_JSON_ARRAY>>>

**Revision mode:** <<<REVISION_MODE>>>

- **full** — Improve every line relative to the working baseline and the coverage diagnostics; each output line may differ from the baseline.
- **subset** — Only the local 0-based positions listed in <<<REVISE_LOCAL_INDICES_LIST>>> must change materially to fit encodability and fix coverage; **other positions must stay exactly** as in the working baseline (the pipeline will enforce this even if you drift).

## Operator notes for revised lines only (untrusted hints)

<<<OPERATOR_NOTES_BLOCK>>>

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

- `rewritten_rules` length **must equal** <<<CHUNK_RULE_COUNT>>> (same order as the baseline).
- Under **subset** mode, slots whose local index is **not** in <<<REVISE_LOCAL_INDICES_LIST>>> must equal the working baseline at that index (string-for-string); the caller will overwrite those slots from the baseline if needed, but you should still align to avoid confusion.
- Under **full** mode, each line may change; stay faithful to the authoritative source rules above unless a change is required for encodability or coverage.
- Each string is one English policy rule line.
- Prefer wording that avoids OUT_OF_SCOPE in pivot WFM (no unsupported arithmetic, no variable×variable products, etc.).
