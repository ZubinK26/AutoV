# Dev plan: Query templates + Z3 diagnostics (Pivot pipeline v1)

## Goals

1. **Scenario / query templates** — Second JSON family (parallel to rule IR) describing **state**, **optional extra constraints**, and **expected** `sat` / `unsat` (or `unknown`), parsed deterministically (Pydantic) and checked against the same **MetaScheme** + encoder as today.
2. **Extended Z3 runs in the main pipeline** — Beyond a single `check()`, run **lightweight automatic diagnostics** on every policy build, persist structured results next to `z3_result.json`.

## Part A — Query templates (future implementation)

| Piece | Role |
|-------|------|
| **Schema** `QueryCaseV1` | `case_id`, `assumptions[]` (variable name + literal or relational atom), optional `extra_constraints` reusing subset of ConditionExpr, `expect` ∈ `{sat, unsat, unknown}`, optional `notes`. |
| **Harness** `run_query_case(meta, case) -> QueryCaseResult` | `build_solver`, `push`, assert assumptions as equalities/inequalities on `variable_sorts`, `check()`, compare to `expect`, optional model excerpt / unsat signal. |
| **Batch** | `cases.json` or `.jsonl`; CLI `--query-cases path`; results → `z3_query_results.jsonl`. |
| **LLM** | Prompt: NL test description → **one** JSON object; validate; optional repair loop (same pattern as extract). |
| **Generality** | No per-policy Python; only shared schema + encoder + prompts. Coverage bound by cases written/generated. |

**Follow-ups:** UNSAT core (requires tracked assertions); incremental `push`/`pop` suites; property templates (“∀ scenarios where F, policy ⊢ G”) encoded as search over finite case grids.

## Part B — Standard Z3 diagnostics (pipeline, this rollout)

Run after `build_solver` + first `check()`:

| Diagnostic | Purpose |
|------------|---------|
| **`elapsed_ms`** | Wall time for `check()`. |
| **`model_verified`** (if `sat`) | `model.eval(policy_formula, model_completion=True)` is identically true — catches inconsistent encoder/model plumbing. |
| **`statistics`** | If available from solver, stringified stats for debugging slow/odd policies. |
| **`reason_unknown`** | If status is `unknown`, capture solver reason when exposed. |

Persist in **`z3_result.json`** (extend in place; keep `status`, `model_excerpt`, `unsat` keys).

**Out of scope v1:** full proof obligations, LIA completeness arguments, expensive quantifier alternation.

## Part C — Pivot WFM chunk cardinality (related bug)

Coverage assumes **exactly one** handoff forward row per **source** chunk rule (global `line_index` range). Agent 2 **over-decomposition** (6+ lines for a 5-rule chunk) yields `extras=[…]` even when every line is PASS. Mitigation: append a **pivot-only footer** to chunk user text requiring **exactly N** numbered Agent 2 lines matching the chunk. See `pivot_chunk_agent2_cardinality_footer` in code.

## Success criteria

- [x] `z3_result.json` contains timing + `model_verified` when `sat` (see `run_z3_check`).
- [ ] Query-case schema + `run_query_case` harness + CLI (later PR).
- [x] Pivot chunk text includes Agent 2 cardinality footer (`_format_pivot_chunk_text`).
