# Dev plan: Multi-term `SUM_THRESHOLD` lowering (v1)

**Status:** **Approved** — depends on [`dev_plan_k_of_n_and_assessment_views_v1.md`](dev_plan_k_of_n_and_assessment_views_v1.md) (assessment path merged first).  
**Goal:** Support `terms: [{coeff, variable}, ...]` with **2–4 terms** (cap), lower to core IR for Z3, and keep **LLM assessment readable** via expansion-preserving linearization (not the accumulator chain).

---

## 1. Fixed decisions

| # | Decision |
|---|----------|
| S1 | **`SUM_THRESHOLD_MAX_TERMS = 4`** everywhere (schema, lowering, extract, prompts). No separate “8-term schema” cap. |
| S2 | **Lowering** emits a **linear accumulator chain** of core rules with deterministic helper `rule_id`s (`R001__sum_acc0`, …). |
| S3 | **Assessment** prints the **original** `SUM_THRESHOLD` block (all terms, operator, limit). Testers/critics **never** see the accumulator chain in linearized input. |
| S4 | **Single-term** behavior unchanged (one `CONSTANT_RELATIONAL` or one `ARITHMETIC_EVALUATION`). |
| S5 | No new `template_class`; still `SUM_THRESHOLD` in extract JSON. |

---

## 2. Lowering algorithm (programmatic)

For `terms = [t0, t1, …, t{n-1}]`, `relational_operator`, `limit`:

1. **Term 0:** `ARITHMETIC_EVALUATION` — `operand_1 = t0.variable`, `MULTIPLY` if `coeff != 1`, compare to a **temporary bound** or store in named intermediate via paired rules.
2. **Term i>0:** `ADD` previous accumulator int to `ti` contribution (MULTIPLY if needed).
3. **Final rule:** `CONSTANT_RELATIONAL` or `ARITHMETIC_EVALUATION` on **`Rbase__sum`** vs `limit` with `relational_operator`.

**Implementation detail (fixed):**

- Emit helper **synthetic variable names** in conditions only where core IR allows (use rule-local naming in `rule_id` suffixes, not new schema fields).
- Cap: **reject** `len(terms) > 4` at validate with clear error (or keep schema 8 but lowering cap 4 — **lowering cap 4** is normative).
- All emitted rules use same `applies_to` / `overrides` as source `SUM_THRESHOLD` rule; only first helper carries `overrides` from parent.

**File:** extend `lower_sum_threshold()` in `vnext_lowering.py`; add unit tests mirroring `test_int_range_*`.

---

## 3. Assessment (mandatory — not optional)

Reuse `assessment_linearize.py` from assessment-views plan:

```text
[R008] SUM_THRESHOLD 2*units + 3*hours LTE 100
  term 1: coeff=2 variable=units
  term 2: coeff=3 variable=hours
  limit: 100
```

No reference to `__sum_acc0` in assessment output.

---

## 4. Implementation order

| Step | Work |
|------|------|
| 1 | Merge assessment-views plan (Steps 1–5) |
| 2 | Implement `lower_sum_threshold` multi-term (cap 4) + tests |
| 3 | Z3 smoke fixture `vnext_sum_threshold_3term_rules.json` |
| 4 | Update `PIVOT_TEMPLATE_SYSTEM.md` §2.1 (multi-term allowed) |
| 5 | Extract addendum (integration plan) — when NL says “sum of …” use `SUM_THRESHOLD` |

---

## 5. Acceptance criteria

- [ ] 3-term fixture compiles and `run_z3_check` → `sat`.
- [ ] Assessment linearization shows three terms; does **not** list `__sum_acc*` rule ids.
- [ ] 5-term input fails at validate with actionable message.
- [ ] Single-term policies unchanged (regression).

---

## 6. Non-goals

- More than 4 terms in lowering v1.
- Native “sum” node in core eight templates.
- Showing accumulator chain to pivot critic as primary text (appendix may mention “lowered to N core rules” in one line only).
