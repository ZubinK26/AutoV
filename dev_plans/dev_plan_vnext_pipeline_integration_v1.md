# Dev plan: vNext template integration (post-`vnext_8` lowering)

**Status:** in progress — lowering + assessment + extract/repair prompts done; extract NL goldens (live LLM) and template-suite catalog optional (`ir_vnext.py`, `vnext_lowering.py`, `load_rules_and_compile` pre-pass).  
**Prerequisite:** [`dev_plan_8_new_expansion_v1.md`](dev_plan_8_new_expansion_v1.md) — schemas + deterministic lowering for all eight expansion templates.  
**Goal:** Align the **rest of the pivot pipeline** with expansion templates so operators can use them end-to-end (extract → repair → critic/tester → linearize → Z3 → template suite), not only via hand-authored `rules_extracted.json`.

---

## 0. What is already implemented (baseline)

| Layer | Status | Notes |
|-------|--------|--------|
| **Pydantic schemas** (`ir_vnext.py`) | Done | All 8 `template_class` values + caps |
| **Lowering** (`vnext_lowering.py`) | Done | All 8 `_LOWERERS`; emits core IR only |
| **Compile hook** (`load_rules_and_compile`) | Done | `expand_rules_to_core` before core validate |
| **Run summary** (`run.py`) | Done | `summary["vnext_lowering"]` when expansion rules present |
| **Unit + Z3 smoke tests** | Done | `test_vnext_lowering.py`, `fixtures/vnext_*.json` |
| **Docs** | Partial | `PIVOT_TEMPLATE_SYSTEM.md` §2.1 |

**Not done:** extract prompts, repairer/critic/tester awareness of expansion JSON, template-suite per kind, version gate `1.1`, PML README for vNext.

**Approved dependencies (implement before extract/repair reliance on vNext):**

- [`dev_plan_k_of_n_and_assessment_views_v1.md`](dev_plan_k_of_n_and_assessment_views_v1.md) — dual view: compile = lowered core; LLM assessment = pre-lowering expansion JSON.
- [`dev_plan_sum_threshold_multi_term_v1.md`](dev_plan_sum_threshold_multi_term_v1.md) — multi-term lowering **after** assessment path; same dual-view principle.

---

## 1. Design invariant (do not break)

- **Meta-scheme and Z3** always see **core eight** templates only (after lowering).
- **Expansion templates** may appear in **`rules_extracted.json`** (and optionally in handoff/repair payloads) until compile.
- **Lowering is deterministic** — no LLM in `vnext_lowering.py`.
- **Additive:** policies with only core templates behave as before.

---

## 2. Required changes by pipeline stage

### 2.1 Extract (Phase 1) — **high priority**

**Problem:** `extract.py` `_model_map()` and `prompts/extractor.md` only know the core eight. LLM cannot emit `K_OF_N`, `INT_RANGE`, etc.

| Task | Detail |
|------|--------|
| **Router or staged prompts** | Per dev plan §5: avoid one mega-prompt. Options: (a) narrow addendum `prompts/extractor_vnext_snippet.md` included when policy NL matches patterns; (b) second-pass “template lift” after core extract. |
| **`_model_map()` / `validate_rule_dict`** | Register `ir_vnext` models OR validate expansion in a pre-pass before core validation. |
| **Encodability contract** | Update `v1_policy_encodability_contract.md`: when to use `K_OF_N` vs nested `and`/`or`; caps (`n ≤ 10`, table rows ≤ 32). |
| **ABORT vs expansion** | Clarify: expansion is in-scope; unbounded ∀ / infinite domains remain ABORT. |
| **Golden / regression** | 1–2 hand-authored NL lines per template kind → expected expansion JSON (no live Gemini in CI). |

**Acceptance:** Extract from a one-line NL fixture produces valid expansion JSON that compiles after lowering.

---

### 2.2 Structural + semantic repairers — **high priority**

**Problem:** Repairer prompts and denylist assume core eight; patched rules with `K_OF_N` would fail validation if repairer strips unknown keys or rewrites to invalid core.

| Task | Detail |
|------|--------|
| **`repairer_piv_structural.md`** | Document that `template_class` may be expansion; compile path lowers before validate. |
| **`repairer_piv_semantic.md` / `test_repairer.md` / `cross_repairer.md`** | Same; repairer may output expansion templates when fixing NL↔IR drift if NL clearly needs `K_OF_N` / `TABLE_BLOCK`. |
| **`sanitize_rules_jsonable`** | Today skips unknown templates. Either extend sanitizers for vNext fields or run `expand` only at compile (keep raw JSON in `rules_extracted.json`). **Recommendation:** keep expansion in stored JSON; sanitize vNext in `ir_vnext`-aware helper. |
| **Denylist + examples** | One minimal JSON example per expansion template in repairer prompts (per original checklist §7). |
| **Compile feedback loop** | Already flows through `load_rules_and_compile`; ensure error messages mention expansion template + lowering failure. |

**Acceptance:** Mock repair returns `K_OF_N` rule → `load_rules_and_compile` succeeds.

---

### 2.3 Pivot critic, tester, cross-critic — **medium priority**

**Problem:** These agents compare NL / synthetic / linearized IR. After lowering, **synthetic** reflects core rules; **rules_extracted.json** may still show expansion.

| Task | Detail |
|------|--------|
| **Critic input** | Default: compare NL vs **synthetic** (unchanged). Optional: flag if `rules_extracted.json` contains expansion templates not reflected in synthetic (structural `misalignment`). |
| **Tester / linearized** | Linearization runs on **core** rules today. Tester sees linearized core — OK if expansion lowered correctly. If tester runs on pre-lowering JSON, add note in prompt: “expansion templates are lowered before linearize.” |
| **Cross-critic** | Same as tester — linearized model is post-lowering if linearize uses compiled meta or expanded rules. **Verify:** `build_and_write_linearized` uses `rules` from pipeline state (post-repair, pre- or post-expand?). **Action:** call `expand_rules_to_core` before linearize OR linearize from `meta_scheme` back-translate path. |
| **Drift categories** | Add optional finding category `expansion_not_lowered` for tooling mistakes. |

**Acceptance:** Document in ARCHITECTURE.md: critic/tester audit **lowered** semantics unless explicitly configured to read raw extract.

---

### 2.4 Linearize + backtranslate + synthetic — **covered by approved assessment-views plan**

| Task | Detail |
|------|--------|
| **`assessment_linearize.py`** | **Approved:** build `linearized_model_for_assessment.txt` from **pre-expand** rules; tester/cross-critic use this. |
| **`linearize_rules.py`** | Remains **compile-oriented** (post-expand / core) if needed for debug; not the LLM audit surface. |
| **`meta_scheme_to_markdown` / synthetic** | Core lowered truth for Z3; critic also gets **`expansion_assessment_digest.md`** when vNext present. |
| **Backtranslate** | Unchanged (synthetic from meta). |

---

### 2.5 Template suite — **medium priority**

**Problem:** Executable tests target core IR instances.

| Task | Detail |
|------|--------|
| **One instance per expansion template** | Add under `tests/fixtures/` or `template_suite/`: minimal policy using `K_OF_N`, `INT_RANGE`, etc. |
| **`template_suite` runner** | Policies compile via existing path (lowering automatic). |
| **Generator prompt** | Later: `template_generator` may emit worlds that target expansion rules. |

---

### 2.6 Registry pass — **low priority**

| Task | Detail |
|------|--------|
| **Variable discovery** | `K_OF_N` / `BOUNDED_FORALL` clauses expose variables in `ConditionExpr`; registry should scan expansion JSON before lowering or after expand. **Action:** run registry on **expanded** rules if registry runs pre-compile. |

---

### 2.7 CLI, observability, packaging (PML) — **low priority**

| Task | Detail |
|------|--------|
| **`run_summary.json`** | Already has `vnext_lowering`; document fields in README. |
| **CLI flag** (optional) | `--no-vnext-lowering` for debugging only. |
| **PML / pivot-only README** | Section: “Writing policies with K_OF_N” + example JSON + caps. |
| **`policy_semantics_version` 1.1** | Optional manifest `pivot_ir_extensions: ["vnext_8"]` in rules file header; reject unknown extensions on old tooling. |

---

## 3. `SUM_THRESHOLD` — multi-term (approved plan)

**See** [`dev_plan_sum_threshold_multi_term_v1.md`](dev_plan_sum_threshold_multi_term_v1.md). Assessment path is a **hard prerequisite**; lowered accumulator chain is **not** shown to LLMs.

### 3.0 Legacy notes (context)

### 3.1 What the expansion plan promised

**`SUM_THRESHOLD`:** `terms: [{coeff, variable}, ...]`, `relational_operator`, `limit` — e.g. “2·hours + 3·cores ≤ 120”.

### 3.2 What was implemented

| Aspect | Status |
|--------|--------|
| **`SUM_THRESHOLD_MAX_TERMS = 4`** (schema + lowering + prompts) | Yes |
| **2–4 terms** | Lowered via accumulator chain |
| **5+ terms** | **Rejected at validate** with clear error |

**Single-term lowering:**

- `coeff == 1` → one `CONSTANT_RELATIONAL` (`variable` op `limit`).
- `coeff != 1` → one `ARITHMETIC_EVALUATION` (`MULTIPLY` var × coeff, then op `limit`).

### 3.3 Why multi-term was deferred

Core IR has **no single-node “sum of linear terms”**. Options:

1. **Chain of `ARITHMETIC_EVALUATION` + synthetic accumulator variables** (`DEFINED_AS` / extra rule ids) — needs naming, pathway ordering, sort checks.
2. **Z3-native sum** in `z3_compile.py` (new internal encode path) — violates “only core after lowering” unless we add a core template (out of scope for v1).
3. **Multiple rules** (one per term vs share of limit) — **unsound** for true sum semantics.

---


## 4. Per-template implementation honesty matrix

| Template | Schema | Lowering | Z3 smoke | Extract | Repairer docs | Template suite |
|----------|--------|----------|----------|---------|---------------|----------------|
| **INT_RANGE** | Yes | Yes | Yes | No | No | No |
| **DECISION_TABLE_ROW** | Yes | Yes | Yes | No | No | No |
| **TABLE_BLOCK** | Yes | Yes | Yes | No | No | No |
| **BOUNDED_FORALL** | Yes | Yes | Yes | No | No | No |
| **K_OF_N** | Yes | Yes | Yes | No | No | No |
| **EXHAUSTIVE_SWITCH** | Yes | Yes | Yes | No | No | No |
| **DEFINED_AS** | Yes | Yes | Yes | No | No | No |
| **SUM_THRESHOLD** | Yes | Yes (1–4 terms) | Yes | Partial (prompts) | Partial | No |

**Answer:** All **eight** templates have schema + lowering wired in `_LOWERERS`. **Seven** are fully lowered for their intended v1 shape. **`SUM_THRESHOLD`** is intentionally **partial** until multi-term lowering is designed.

---

## 5. Suggested implementation order (this dev plan)

| Phase | Focus | Risk |
|-------|--------|------|
| **I1** | Linearize path: always use expanded/core rules; document critic/tester | Low |
| **I2** | Sanitize + repairer prompts + structural compile errors for vNext | Medium |
| **I3** | Extract addendum + encodability contract + 8 NL golden fixtures | High (LLM) |
| **I4** | Template-suite instances (8) | Low |
| **I5** | Assessment views (approved) | Medium — **before** I3 extract |
| **I6** | Multi-term `SUM_THRESHOLD` (approved) | Medium — after I5 |
| **I6** | `policy_semantics_version` / PML README | Low |

---

## 6. Acceptance criteria (integration complete)

- [x] Extract validates vNext templates; optional live e2e via `PIVOT_RUN_LLM_EXTRACT=1` (deterministic NL goldens in CI).
- [x] Repairer prompts + examples for expansion templates.
- [x] Critic/tester/cross-critic use assessment (pre-lowering) view.
- [x] Eight template-suite scenarios pass (`template_suite_vnext_suite.json`).
- [x] Multi-term `SUM_THRESHOLD` (2–4 terms) lowers and Z3 smoke passes.
- [x] `policy_semantics_version` 1.1 + `pivot_ir_extensions`; `--no-vnext-lowering`; template generator vNext guidance.
- [x] No regression: `pytest NagV/pivot_pipeline/tests` green.
- [ ] Operator confirms **live extract** reliably emits vNext on real policies (manual / `PIVOT_RUN_LLM_EXTRACT`).

**Operator reminders:** [`VNEXT_OPERATOR_REMINDERS.md`](VNEXT_OPERATOR_REMINDERS.md)

---

## 7. Non-goals (this integration plan)

- Changing Z3 theory beyond current QF-LIA-style usage.
- Teaching WFM to emit expansion templates directly (WFM still outputs NL lines).
- Auto-lowering in scope rewriter.

---

## 8. References

- Original expansion spec: [`dev_plan_8_new_expansion_v1.md`](dev_plan_8_new_expansion_v1.md)
- Code: `NagV/pivot_pipeline/ir_vnext.py`, `vnext_lowering.py`, `constants.py` (`SUM_THRESHOLD_V1_MAX_TERMS`)
- Tests: `NagV/pivot_pipeline/tests/test_vnext_lowering.py`
