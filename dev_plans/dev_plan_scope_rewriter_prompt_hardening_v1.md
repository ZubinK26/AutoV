# Dev plan: Scope Rewriter prompt hardening (semantic drift + pivot scope)

## Context

[`scope_rewriter_pre_wfm.md`](../NagV/pivot_pipeline/prompts/scope_rewriter_pre_wfm.md) drives the pre-WFM agent. Empirical comparison of reference [`Evaluation_RUles_Processed.md`](../NagV/pivot_pipeline/inputs/Evaluation_RUles_Processed.md) to a generated [`latest.nl`](../NagV/exports/scope_rewriter/evaluation_rules_ref/scope_rewriter/latest.nl) showed:

1. **Semantic drift** — omissions, weakened modals (must / iff / exclusively), compressed enumerations, dropped optional clauses, and premature `snake_case` formalization without equivalence disclosure.
2. **Residual scope mismatch** — many lines remain **downstream** OUT_OF_SCOPE for WFM Agent 3 / extract because their **semantic type** is procedural, temporal, comparative, or artifact-generation-heavy, not because the file violates “one line per rule.”

This plan covers **prompt + JSON contract** changes only (no mandatory code changes for v1; optional schema extensions listed).

## Goals (v1)

- Reduce **silent** semantic change: every material delta must appear in **`semantic_deltas`** or **`partial_rewrites`**, and **`strict_equivalence_achievable`** must reflect honest tradeoffs.
- Reduce **avoidable** pivot friction: the model should **surface** high-friction line types and prefer **faithful surrogates** (state-shaped) or **explicit non-equivalence** over short prose that still fails WFM.

## Non-goals (v1)

- Guarantee WFM PASS or extract success (still depends on model + reference).
- Replace Phase 0 WFM or post-hoc scope rewrite loops.
- Chunked / multi-turn document passes (see parent plan [dev_plan_pre_wfm_scope_rewriter_v1.md](dev_plan_pre_wfm_scope_rewriter_v1.md) Phase P4).

---

## Workstream A — Semantic drift (prompt + sidecar)

### A1. Coverage and “no silent drops”

- Add explicit instructions: every **substantive** obligation in the reference (paragraph, numbered item, or bullet under a `---` block) must map to **at least one** output line **or** appear in **`partial_rewrites`** with a reason (cannot express in v1 / merged intentionally with citation of merged source spans).
- Forbid removing standalone rules such as “follow official task specification for the week/task” unless the merger target is named in **`semantic_deltas`**.

### A2. Modality and logic preservation

- Short **deontics appendix** in the system prompt (abstract wording): preserve **must / may / must not**, **if and only if** vs **only if**, **must apply** vs **is permitted**, **exclusively**, **regardless of final score**, **valid** / **specific** qualifiers when they change who/when something binds.
- Explicit **anti-pattern**: do not weaken biconditionals into permissions or one-way conditionals without flagging `strict_equivalence_achievable: false`.

### A3. Enumerations and “such as” lists

- When the source lists **examples or mandatory facets** (e.g. evaluation ordering steps, Task 04 artifact classes, Project evidence checks), either preserve the list **or** compress only with **mandatory** `partial_rewrites` entries per dropped facet and set `strict_equivalence_achievable: false` if fidelity is not guaranteed.

### A4. Optional / permissive / “plus” norms

- Instruct: clauses containing **optional**, **permitted**, **may**, **considered a plus** must survive in some form; do not delete for brevity. If pivot shape forces softening, disclose in **`semantic_deltas`**.

### A5. Formal identifiers (`snake_case`)

- **Default** output is plain English policy sentences. Introduce **only** when necessary for disambiguation; if used, **`semantic_deltas`** must state that identifiers are **representation choices**, not new obligations.

### A6. Sidecar schema extensions (prompt-level contract)

Extend the **required JSON** (document in prompt; implement in `ScopeRewriterLLMOutput` when coding):

- `modality_notes` (array of strings): e.g. “Source used iff penalty; output kept iff.”
- `omissions_check` (array of strings): “Every `---` section represented: A,B,C” or explicit gaps.
- `enumerations_compressed` (array of objects): `{ "topic": "…", "kept": "…", "dropped_facets": ["…"] }`

---

## Workstream B — Pivot scope awareness (prompt + sidecar)

### B1. Per-line (or per-cluster) encodability tagging

- Require the model to classify each output line (or a parallel array in JSON) into **one primary** type, for example:

  - `state_constraint` — static predicated facts, thresholds, caps.
  - `arithmetic_threshold` — numeric comparisons, piecewise caps.
  - `enumeration` — closed sets, forbidden literals.
  - `temporal_or_process_order` — before/after, fixed evaluation order (**high WFM friction**).
  - `comparative_judgment` — best/most/relevant without a defined metric (**high friction**).
  - `artifact_or_filesystem` — must generate paths, directory layout (**high friction**).
  - `mixed` — split required or flag `strict_equivalence_achievable: false`.

- Instruct: **high-friction** types must either be **rewritten toward `state_constraint`** with explicit surrogates **or** left honest with `partial_rewrites` / false strict equivalence — not laundered into a short ambiguous sentence.

### B2. Temporal and procedural templates (abstract)

- **Temporal:** Prefer state predicates over “before evaluation begins” unless truly equivalent; if not, nearest rewrite + flag.
- **Procedural priority (A then B then C):** Either enumerate as rigid state machine hints the stack can digest **or** admit non-equivalence; forbid one-line “priority order” summaries that drop “default expectation” / first-second-third structure when the source had them.

### B3. Comparative / superlative rules

- Require **explicit scalarization** or **finite disjunction** of allowed outcomes, or declare nearest surrogate + `strict_equivalence_achievable: false`. Forbid dropping **valid**, **exclusively**, **specific**, **complete** when present in source without a delta note.

### B4. Artifact generation vs policy content

- Distinguish “**what grades/feedback must contain**” from “**which files must exist on disk**.” If the stack cannot encode filesystem obligations, classify as `artifact_or_filesystem` and either surrogate to report content rules or disclose partial compliance.

### B5. Self-audit fields (optional but recommended)

- `high_friction_line_indices` (1-based into `plain_rules` split lines): lines the model expects WFM may mark OUT_OF_SCOPE.
- `suggested_human_review_focus` (array): short strings (“branch winner rule”, “Task 04 structure”, “Project iff penalty”).

---

## Prompt file edits (concrete locations)

1. **`NagV/pivot_pipeline/prompts/scope_rewriter_pre_wfm.md`**  
   - Insert **Workstream A** rules after the role block.  
   - Insert **Workstream B** rules + encodability taxonomy before the output JSON table.  
   - Expand the **JSON schema** subsection with new keys (A6, B5).

2. **Keep encodability injection** as today: full **`v1_policy_encodability_contract.md`** appended at runtime in code ([`scope_rewriter_agent.py`](../NagV/pivot_pipeline/scope_rewriter_agent.py)); the prompt should **reference** that file by name and say “do not contradict.”

---

## Code follow-ups (after prompt text stabilizes)

| Item | Purpose |
|------|---------|
| `ScopeRewriterLLMOutput` in [`scope_rewriter_agent.py`](../NagV/pivot_pipeline/scope_rewriter_agent.py) | Add optional Pydantic fields for A6/B5 so validation accepts richer sidecars. |
| Unit tests | Golden JSON fixtures with new fields; regression that old minimal JSON still parses (defaults). |
| [`dev_plan_pre_wfm_scope_rewriter_v1.md`](dev_plan_pre_wfm_scope_rewriter_v1.md) | Cross-link this doc under “Phased delivery” as **P1b prompt hardening**. |

---

## Verification (manual)

1. Re-run Scope Rewriter on `Evaluation_RUles_Processed.md`; compare new `latest.nl` + sidecar to source using the same checklist as the chat review (modality, omissions, enumerations, iff, optional audit CSV, week/task spec rule).
2. Run Phase 0 WFM on new `latest.nl` with `--interactive-policy` and record **COUNT** of OUT_OF_SCOPE lines vs previous run (informative, not a hard gate).

---

## Done when

- Prompt updates are merged and reviewed for **no example-specific leakage** (only abstract patterns).
- Sidecar contract documents new fields; parser accepts them (when code updated).
- At least one **before/after** comparison note exists (issue comment or dev log) showing drift markers improved on the evaluation reference corpus.

---

## Ready

This dev plan is **ready for execution** starting with edits to `scope_rewriter_pre_wfm.md`, then Pydantic/sidecar alignment and tests.
