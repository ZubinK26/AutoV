# Dev plan: K_OF_N assessment readability + vNext assessment views (v1)

**Status:** **Approved** (operator sign-off).  
**Problem:** Programmatic lowering of `K_OF_N` (and multi-term `SUM_THRESHOLD` when added) can produce core IR that is **correct for Z3** but **hard for LLM critics/testers** to match against processed NL.  
**Principle:** **Compile always uses lowered core IR.** **Assessment always uses an expansion-preserving view** for **all** vNext templates in `rules_extracted.json`. No runtime flag; no alternate lowering strategies.

---

## 1. Decisions (fixed — not options)

| # | Decision |
|---|----------|
| D1 | **Z3 / meta-scheme / synthetic compile path** continues to call `expand_rules_to_core` before `load_rules_and_compile`. |
| D2 | **Tester, cross-critic, and pivot critic** receive an **assessment rules view** built from **pre-lowering** `rules_extracted.json` (expansion templates intact). |
| D3 | **`K_OF_N` compile lowering stays** the current DNF-in-one-`LOGICAL_IMPLICATION` implementation until a separate Z3 perf ticket; readability is fixed by D2, not by changing DNF. |
| D4 | **Multi-term `SUM_THRESHOLD` is deferred** until D2 exists; when implemented, lowering may use accumulator rules, but **assessment linearization will print the `SUM_THRESHOLD` block as-authored**, not the accumulator chain. |
| D5 | New artifact on disk: **`linearized_model_for_assessment.txt`** (expansion-preserving). Existing **`linearized_model_for_cross_critic.txt`** is renamed in behavior: produced from assessment view, not from post-lowering rules. |

---

## 2. Why this plan exists

- Pathway compiler **ANDs** all active rules. “At least k of n” cannot become n separate pathway rules without changing semantics.
- Therefore **compile** must keep **one** combined constraint for `K_OF_N` (DNF or future PbGe).
- LLMs **cannot** be required to equate processed NL with a giant OR/AND tree in linearized output.
- Therefore **assessment** must **not** linearize the DNF blob; it must linearize the **source** `K_OF_N` object (k, n, numbered clauses).

**SUM_THRESHOLD (multi-term):** Lowering to a chain of `ARITHMETIC_EVALUATION` + helper ids is **less** readable than a single `SUM_THRESHOLD` JSON. **Confirm:** multi-term lowered form is **not** more LLM-friendly than the expansion form. Assessment view (D2/D4) is **required** before shipping multi-term lowering.

---

## 3. Implementation steps

### Step 1 — Assessment linearization module

**Add** `pivot_pipeline/assessment_linearize.py`:

- Input: `rules: list[dict]` (pre-expand JSON).
- For each rule:
  - **Core eight:** delegate to existing `linearize_rules` per-rule formatter (reuse logic).
  - **`K_OF_N`:** emit one block:
    ```text
    [R001] K_OF_N at_least k=3 of n=10
      clause 1: <short atom/condition summary>
      clause 2: ...
    ```
  - **`TABLE_BLOCK`:** emit table header + one line per row (no suffix explosion in assessment view).
  - **`INT_RANGE`, `BOUNDED_FORALL`, `EXHAUSTIVE_SWITCH`, `DEFINED_AS`, `DECISION_TABLE_ROW`:** structured summary (not lowered shape).
  - **`SUM_THRESHOLD`:** emit `terms[]` as human list (when multi-term exists later, show all terms here).

**No LLM** in this module.

### Step 2 — Wire pipeline outputs

**In** `run.py` (and `repair_apply` refresh paths):

1. Keep `expand_rules_to_core` only inside `load_rules_and_compile`.
2. Before tester / cross-critic / linearize gates:
   - `assessment_linearized = build_assessment_linearized(rules)` from **current** `rules` list in memory (pre-expand).
3. Write **`linearized_model_for_assessment.txt`** (new) and set **`linearized_model_for_cross_critic.txt`** content from **assessment** view (same file body; cross-critic path reads this).
4. **Tester** (`run_pivot_tester`): pass `assessment_linearized`, not post-lowering linearization.

**In** `run_summary.json`:

- `assessment_linearized_path`
- `vnext_lowering` (unchanged, compile-only stats)

### Step 3 — Pivot critic input

**Extend** critic payload:

- **Primary:** `synthetic_en.md` (from core meta — unchanged).
- **Appendix:** when `rules_extracted.json` contains any vNext template, add **`expansion_assessment_digest.md`** (auto-generated from Step 1, same content as assessment linearized or shortened).

**Update** `prompts/pivot_critic.md`:

- When appendix present: “NL may align with expansion digest; synthetic reflects lowered compile form; do not treat DNF unfold as a second policy—treat appendix as authoritative for K_OF_N / TABLE_BLOCK shape.”

### Step 4 — Tester / cross-critic / test-repairer prompts

**Update** `tester_pivot_semantic.md`, `cross_critic` prompt, `test_repairer.md`:

- State compared artifact: **`processed NL` vs `linearized_model_for_assessment` (expansion-preserving)**.
- Explicit: **Do not** expect line-by-line match to DNF lowered compile IR.

### Step 5 — Tests

| Test | Assert |
|------|--------|
| `test_assessment_linearize_k_of_n` | Fixture `K_OF_N` → output contains `at_least k=2`, ten clause lines, **no** giant `OR(` nesting |
| `test_tester_uses_assessment_linearized` | Mock path passes assessment string into tester |
| `test_compile_still_lowers_k_of_n` | `load_rules_and_compile` still succeeds; meta has one `LOGICAL_IMPLICATION` for k-of-n fixture |
| Regression | Existing `test_vnext_lowering` unchanged |

### Step 6 — Documentation

- `PIVOT_TEMPLATE_SYSTEM.md` §2.1: two views (compile vs assessment).
- `ARCHITECTURE.md`: diagram box “assessment linearize (pre-expand)”.
- `dev_plan_vnext_pipeline_integration_v1.md`: reference this plan as **approved dependency** for extract/repair work.

### Step 7 — Multi-term `SUM_THRESHOLD` (separate approved track)

**Gate:** Steps 1–5 merged first. See also [`dev_plan_sum_threshold_multi_term_v1.md`](dev_plan_sum_threshold_multi_term_v1.md).

**Same principle as D1–D5:** compile = accumulator lowering; assessment = as-authored `terms[]` list.

---

## 4. Which templates need the dual view?

| Template | Lowered form hard for LLMs? | Use assessment view (D2)? |
|----------|----------------------------|---------------------------|
| `K_OF_N` | **Yes** (DNF blob) | **Required** |
| `SUM_THRESHOLD` (2+ terms) | **Yes** (accumulator chain) | **Required** when multi-term ships |
| `SUM_THRESHOLD` (1 term) | No (one comparison) | Yes (uniform path; cheap) |
| `INT_RANGE` | No | Yes (uniform) |
| `DECISION_TABLE_ROW` | No | Yes (uniform) |
| `TABLE_BLOCK` | No (often clearer lowered) | Yes (uniform; nicer table layout in assessment) |
| `BOUNDED_FORALL` | No | Yes (uniform) |
| `EXHAUSTIVE_SWITCH` | No | Yes (uniform) |
| `DEFINED_AS` | No | Yes (uniform) |

**Decision:** Implement **one** assessment linearization path for **every** vNext rule, not only `K_OF_N`. Only two templates are *critical* for LLM quality; the rest follow the same path for consistency and simpler pipeline logic (no “is this template special?” branching at call sites).

---

## 5. Out of scope (this plan)

- Changing pathway AND semantics.
- Replacing DNF `K_OF_N` lowering with PbGe in `z3_compile` (future perf/clarity ticket, not required for assessment).
- Extract/repair emitting vNext templates (covered by integration dev plan).

---

## 6. Acceptance criteria

- [ ] `K_OF_N` policy: tester and cross-critic receive assessment linearization with **readable** k/n/clause list.
- [ ] Same policy: Z3 compile still passes via lowered core.
- [ ] Pivot critic receives expansion digest when vNext present; prompt instructs how to use it.
- [ ] No new runtime flag; behavior is always dual-view per D1–D5.
- [ ] All pivot_pipeline tests green.

---

## 7. Approval record

**Approved:** dual-view assessment for all vNext templates; `K_OF_N` DNF compile lowering unchanged; multi-term `SUM_THRESHOLD` gated on assessment path (see linked dev plan).
