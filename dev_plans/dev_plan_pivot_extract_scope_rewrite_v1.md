# Dev plan: pivot extract ABORT → in-scope rewrite + confirm + WFM (v1)

## Goal

When Phase 1 extraction returns **ABORT** (line not encodable in pivot v1 IR), optionally run a **scope rewrite agent** that proposes an English rule **within v1 expressivity**, documents **semantic deltas**, shows the proposal in the console for **human confirmation**, and on **accept** runs the proposal through **pivot WFM** (Agents 1–3, same as Phase 0) before **re-trying extraction** for that line. Repeat up to a bounded budget so more of a ruleset can complete without hand-editing JSON.

## Non-goals (v1)

- No automatic accept; always confirm when interactive mode is on.
- No change to core IR or Z3 encoder; rewrites must stay within existing templates and linearity rules.
- No merge of scratch WFM handoffs into the main Phase 0 manifest (scratch dirs are under `work_dir/wfm_rewrite_scratches/`).

## Design

1. **`scope_rewrite` prompt + JSON output**  
   Fields: `rewritten_line` (one rule, plain English), `semantic_deltas` (string array), `fidelity_notes` (short string). Constraints echoed from extractor: no variable×variable multiply; prefer surrogate scalar variables (e.g. `total_estimated_cost`) when products are disallowed.

2. **`run_pivot_wfm_one_line`** (`pivot_wfm/wfm_one_line.py`)  
   Write one line to a temp NL file under `work_dir/wfm_rewrite_scratches/<id>/`, run `run_pivot_wfm_until_complete` with `rules_per_chunk=1`, `aggregate_pivot_wfm_nl`, return first `statement_nl`.

3. **`extract_with_abort_rewrite_loop`** (`pivot_pipeline/extract_rewrite_loop.py`)  
   Sequential extract only (`extract_one_line`). On `ExtractAbort`, if interactive flag: call scope rewrite → print proposal → `input_fn` yes/no. On yes: WFM line → replace `lines[i]` → retry (same `line_index` / `rule_id`). On no: re-raise. Cap attempts per line via `PIVOT_EXTRACT_REWRITE_MAX_ATTEMPTS` (default 3).

4. **Orchestrator** (`run.py`)  
   New args: `interactive_extract_abort`, `input_fn`. When true and LLM extract path: use loop; persist `extract_rewrite_log.jsonl` and refresh `phase0_normalized_nl.txt` + `rules_source.txt` from final `lines`.

5. **CLI**  
   `--interactive-extract-abort` enables the loop (default off for CI/batch).

## Done when

- Interactive run can recover from ABORT lines like `a * b <= c` by proposing a surrogate-variable form, user accepts, WFM normalizes, extraction continues.
- Batch behavior unchanged without the flag.
- Unit tests with mocked LLM, WFM, and `input_fn`.
