# Dev plan: targeted WFM chunk scope rewrite (partial retry after reject)

## Problem

In **pivot Phase 0** interactive flow, when **WFM chunk line coverage** fails and the operator runs **chunk scope rewrite**, the CLI shows a **full-chunk** proposal (one rewritten line per rule in the chunk). If the operator answers **no** to “Accept rewrite and re-run WFM?”, the implementation **immediately calls the rewriter again** with the **same pre-rewrite** `chunk_rules` and **no record** of which lines from the rejected proposal were acceptable.

That causes **wasted LLM work** and **unnecessary semantic drift**: lines the operator was fine with can be rewritten again arbitrarily, even when the operator only wanted to fix **one** line (or a subset) and even if they provided **comments keyed to specific global indices**.

**Desired behavior:** Rejection means “do not apply this bundle as a whole,” not “throw away all per-line judgments.” Only lines the operator **explicitly targets** (by **global rule index** and optional **comment**) should be revised on the next attempt; **all other lines** in the chunk should remain **exactly** as in the **last proposed** rewrite (or fall back to current working text when there was no prior proposal).

## Scope (v1)

| In scope | Out of scope |
|----------|----------------|
| `NagV/pivot_wfm/run_wfm_phase.py` loop after `run_wfm_chunk_scope_rewrite` | Pre-WFM Scope Rewriter human loop (separate UX) |
| `NagV/pivot_wfm/wfm_chunk_scope_rewrite.py` + `NagV/pivot_pipeline/prompts/wfm_scope_rewrite.md` | Changing WFM Agents 1–3 core prompts |
| Operator input: global indices + optional comments; deterministic merge with baseline | Rich TUI / web UI |

## Current behavior (reference)

- On “no”, the inner `while True` continues and calls `run_wfm_chunk_scope_rewrite(chunk_rules, ...)` again — **baseline text is always** `chunk_rules` (original chunk source), **not** the last LLM proposal.
- `run_wfm_chunk_scope_rewrite` has **no** parameter for operator feedback or pinned lines.

## Design

### 1. Baseline and “pinned” lines

Introduce a **revision baseline** for the chunk, per retry:

- **`baseline_chunk`**: `list[str]`, length = chunk size, aligned with `chunk_rules` indices within the chunk.
- **Initialization:** before the first rewrite call in a given coverage-failure episode, `baseline_chunk = list(chunk_rules)`.
- **After a rejected proposal** `last_proposal: list[str]` (same length): store it in the loop closure.
- **After operator specifies targeted indices** `revise_global: set[int]` (global indices in `[start, end)`):
  - **Pinned lines:** all positions `j` where `global_idx = start + j` **not** in `revise_global` must appear **verbatim** in the final merged output for that retry.
  - **Revised lines:** for `j` where `start + j ∈ revise_global`, take text from the **new** LLM output (or from operator edit in a later phase).

**Enforcement:** Prefer **code-side merge** after the LLM returns: for every pinned index `j`, set `out[j] = baseline_chunk[j]` regardless of what the model emitted for that slot. This avoids relying on the model to “copy verbatim” unpinned lines (models still drift).

If the operator chooses **full regen** (empty revise set or explicit “all”), do not pin: `baseline_chunk` for the prompt can stay `chunk_rules` or the previous proposal per product decision (see §4).

### 2. Operator UX (TTY)

After **no** on “Accept rewrite and re-run WFM?”:

1. Explain: only lines you list will be changed; others stay as in the **last proposed** rewrite (or current source if there was no proposal yet).
2. Prompt: **global** indices (comma-separated, ranges optional, e.g. `3` or `3,7` or `3-5`) **within this chunk**, or **Enter** = treat as **full chunk regen** (current behavior, no pinning).
3. For each index in `revise_global`, optional short comment (or one multiline block with lines like `12: fix iff modality`).
4. Optional: `[s] Skip regen` / `[g] Give up` to align with existing escape hatches.

Log structured choices to `work_dir` (e.g. `pivot_wfm_chunk_rewrite_operator_log.jsonl`) with: chunk span, `last_proposal` hash, `revise_global`, comments, timestamps.

### 3. Prompt and API changes

**`run_wfm_chunk_scope_rewrite`** (signature sketch):

```text
run_wfm_chunk_scope_rewrite(
    chunk_rules,  # original chunk source (still needed for grounding)
    *,
    baseline_for_model: list[str],  # what the model should treat as current text per line
    revise_local_indices: frozenset[int] | None,  # subset of range(n); None = all
    operator_notes_by_local_index: dict[int, str] | None,
    ...
)
```

**`wfm_scope_rewrite.md`:**

- State that `<<<CHUNK_RULES_JSON_ARRAY>>>` is the **authoritative original** chunk.
- Add placeholder for **working baseline** (JSON array) — same length — the model revises **only** slots listed in `<<<REVISE_LOCAL_INDICES>>>` (or “all”).
- For revised slots, apply **`<<<OPERATOR_NOTES>>>`** (structured text) when present.
- Instruct: for non-revised slots, output must match baseline (even with code merge, keeps model focused).

**Alternative (smaller prompt change):** keep a single rules array but pass **merged instruction block** only listing lines to change plus operator notes; still apply **post-merge** pins for robustness.

### 4. When operator says “no” without listing indices

- **First rejection** (no `last_proposal`): optional prompt: “Enter indices to revise, or Enter for **full** regen.” Full regen ↔ `revise_global = all`, baseline_for_model = `chunk_rules` (today’s behavior).
- **Subsequent rejections** with **empty** revise set: treat as **full regen** OR **re-prompt** (“you must list at least one index or confirm full regen”) — pick one and document; recommendation: **confirm** full regen to avoid accidental pin-all.

### 5. Tests

- **Unit:** merge helper — given mock LLM output that changes every line, pinned indices restore `baseline_chunk`.
- **Integration (mocked LLM):** sequence: propose A → reject → target index `{start+1}` only → assert prompt contains operator note / revise set; assert merged chunk matches A on other lines.
- **Regression:** accepting **yes** still replaces `all_rules` slice exactly as today.

## Risks

| Risk | Mitigation |
|------|------------|
| Operator confuses local vs global index | Prompt shows **global** numbers consistently (already `start + i` in display). |
| Model ignores notes | Code merge handles pins; notes only affect revised slots; retry budget unchanged. |
| Stale `last_proposal` after manual file edit | Rare in Phase 0 loop; document that external edits require `--reset-progress`. |

## Done when

- After **no**, the operator can constrain the **next** rewrite to **only** referenced indices; other lines equal **last proposal** (post-merge guaranteed).
- Logs record targeted retries for audit.
- Prompt + pytest cover merge and at least one mocked multi-round flow.

## Related files

- `NagV/pivot_wfm/run_wfm_phase.py` — interactive rewrite loop
- `NagV/pivot_wfm/wfm_chunk_scope_rewrite.py` — LLM call + parse
- `NagV/pivot_pipeline/prompts/wfm_scope_rewrite.md` — rewriter instructions
