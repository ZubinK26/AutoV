# Pivot — Agent 2 chunk line budget (normative)

**Applies only** when this pipeline runs **WFM profile = pivot** (Appended to Agent 2 system instructions at runtime.)

The user message for each chunk includes a **numbered list of source rules** for that chunk. Let **N** be the number of those lines (also given in the `[Pivot pipeline — Agent 2 output shape]` footer when present).

## Non‑negotiable output shape

1. Your **SUCCESS** output must be a numbered list with **exactly N** lines: `1.` through `N.`, in order.
2. **One input line → exactly one output line.** Line *k* in your output is the decomposition of **only** source rule *k* — **not** a merge of two sources, **not** a split of one source into two outputs.
3. **Do not** “fully decompose” one source rule into multiple numbered lines. Extra lines break downstream handoff coverage (each source index must map to **one** forward row). If one source rule cannot be expressed in one line within the compound-operator budget, output **`LIMIT_EXCEEDED`** for the chunk per the standard schema — **do not** add extra SUCCESS lines.
4. Decomposition **within** that single line still follows the global Agent 2 rules and counterexamples (e.g. do not illegitimately split conditionals).

This **overrides** the generic urge to “split into the smallest sub-statements” **when** that would increase the line count above **N**.
