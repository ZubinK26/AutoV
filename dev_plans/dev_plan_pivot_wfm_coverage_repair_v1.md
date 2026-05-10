# Dev plan: Pivot WFM coverage repair loop (M-next)

## Goal

Phase 0 (`pivot_wfm/run_wfm_phase.py`) currently commits each WFM chunk after a single registry handoff. A **post-aggregate** count gate (`enforce_wfm_rule_coverage`) catches silent merges/drops, but only after all chunks finish. We add a **per-chunk coverage repair loop** so operators can detect gaps early, rewrite chunk scope for WFM, retry WFM with a fixed budget, and only then choose abort, drop missing rules from the in-memory ruleset, or explicitly proceed with **raw-NL injection** for missing indices.

## Terminology

- **Chunk**: `rules_per_chunk` lines from the parsed NL file, numbered with **global** 0-based `line_index` in handoffs (same convention as `format_chunk_for_wfm` / Agent 2 numbering \(N = line_index + 1\)).
- **Forward line**: handoff row with `agent3_verdict` in `{PASS, REWRITE}` and non-empty `statement_nl`.
- **Coverage OK**: the set of `line_index` values for forward lines in the handoff equals exactly `range(chunk_start, chunk_end)`.

## Detection

After each `run_wfm_registry_e2e` for a chunk, load the handoff JSON and compute:

- `expected_indices = {chunk_start, …, chunk_end - 1}`
- `forward_indices` from qualifying rows
- `missing = expected - forward`
- `duplicates` if any `line_index` appears more than once

Any non-empty `missing`, `duplicates`, or **extra** forward indices outside the chunk range ⇒ coverage not OK.

## Repair flow (interactive)

When `--interactive-policy` (or extract-interactive alias used for the same bucket in `run_pivot_pipeline`) is set and coverage fails:

1. Log a JSON line to `pivot_wfm_coverage_log.jsonl` (bundle id, chunk range, missing indices, WFM attempt number).
2. If **WFM attempt count** `< PIVOT_WFM_COVERAGE_MAX_WFM_ATTEMPTS` (default **3**):
   - Call **`wfm_scope_rewrite`** LLM prompt with the current chunk rules + coverage diagnostics.
   - Show the proposed `rewritten_rules` (must match chunk length).
   - On operator accept: splice rewritten text into the in-memory `all_rules` slice, rebuild chunk user text, **run WFM again** (new bundle id / handoff file).
   - Operators can refuse proposals until they accept one or choose **give-up** (see below).
3. When WFM attempts reach the budget **or** the operator gives up on rewrites **without** a successful coverage handoff, show the **final chunk**:

   - **`[a]` Abort** → raise `PivotPipelineUserAbort`.
   - **`[d]` Drop** missing global indices: remove those strings from `all_rules` (pop from high index down), append JSON lines to `pivot_wfm_dropped_rules.jsonl`, reset the WFM attempt budget for the **same** `next_rule_index`, recompute `chunk_end`, and run WFM on the shortened chunk (indices shift globally for later rules; committed handoffs keep old `line_index` values — consistent with prior chunks already written).
   - Type **`PROCEED_INCOMPLETE`** (same token as the global gate) → **patch** the handoff JSON: for each missing index, ensure a forward row with `statement_nl = all_rules[idx]` and `agent3_verdict = PASS`, with `scope_report` documenting `pivot_wfm_coverage_injection`. Re-validate coverage; then commit chunk.

## Non-interactive behavior

If coverage fails and `interactive_policy` is false: Phase 0 exits with code **3** (`blocked_wfm_chunk_coverage` in run summary) and does **not** advance `next_rule_index`.

## Post–Phase 0 gates

`enforce_wfm_rule_coverage` remains the **final** backstop. If rules were **dropped** in Phase 0, `run_pivot_pipeline` writes **`pivot_wfm_effective_source.nl`** (join of the final in-memory `all_rules`) and uses that path as the **source** for the count gate so trimmed policies can pass without double consent. If there were no drops, behavior is unchanged (compare against `--input`).

## Env / CLI

| Mechanism | Purpose |
|-----------|---------|
| `PIVOT_WFM_COVERAGE_MAX_WFM_ATTEMPTS` | Max WFM invocations per chunk before the final menu (default `3`). |
| `--interactive-policy` | Enables repair loop + final chunk menu; already documented for other gates. |

## Files

| File | Role |
|------|------|
| `NagV/pivot_wfm/handoff_coverage.py` | Parse handoff, build `ChunkCoverageReport`, patch inject. |
| `NagV/pivot_wfm/wfm_chunk_scope_rewrite.py` | LLM chunk rewrite (JSON `rewritten_rules`). |
| `NagV/pivot_pipeline/prompts/wfm_scope_rewrite.md` | Prompt template. |
| `NagV/pivot_wfm/run_wfm_phase.py` | Integrate loop, logging, drops, effective source write. |
| `NagV/pivot_pipeline/run.py` | Pass `interactive_policy` / `input_fn`; abort handling; effective source for coverage gate. |

## Risks / follow-ups

- Resuming from `nl_chunk_progress.json` after **drops** can desync from the on-disk NL hash; operators should use a fresh `--work-dir` or `--reset-progress` after dropping rules in Phase 0.
- PROCEED_INCOMPLETE injection bypasses Agent 2/3 normalization for missing lines; downstream phases must tolerate rawer NL.

## Validation

- Unit tests for `analyze_chunk_handoff_coverage` and inject patch (no WFM/LLM).
- Manual: run pivot pipeline with a chunk that produces merged/dropped lines; confirm prompts, retries, and gate behavior.
