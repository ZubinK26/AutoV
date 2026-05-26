# Dev plan: Temporal surrogates v1 (eight patterns, no new templates)

**Status:** Implemented (prompts, fixtures, CI tests; manual P10 run log optional).  
**Codename:** `temporal-surrogates-v1`  
**Depends on:** Core + vNext templates and extract integration ([`dev_plan_vnext_pipeline_integration_v1.md`](dev_plan_vnext_pipeline_integration_v1.md) — largely done). Complements [`dev_plan_scope_rewriter_prompt_hardening_v1.md`](dev_plan_scope_rewriter_prompt_hardening_v1.md) Workstream B (partially overlaps — this plan is the **complete** temporal track).

**Goal:** End-to-end support for **eight encodable “temporal” policy shapes** using **only existing** `template_class` values (core eight + vNext where applicable). No LTL/CTL, no event logs, no new IR types.

**Principle:** Pivot checks **one world** (variable assignment). “Before”, “then”, and “in order” mean **constraints on that snapshot**: ordered scalars, prerequisite booleans, finite phase enums, and implication chains—not true time evolution.

---

## 1. Fixed decisions (not options)

| # | Decision |
|---|----------|
| D1 | **No new `template_class`** for temporal logic. All eight patterns map to core and/or vNext templates already in the repo. |
| D2 | **Scope rewriter** must **stop treating** well-formed surrogates as “high friction → vague English → ABORT”. Tag `temporal_or_process_order` lines for **review**, not automatic dilution. |
| D3 | **One NL line → one rule** still holds. Sequences need **multiple lines** (implications, flags, or phase rules), not one compressed “A then B then C” blob unless disclosed as `partial_rewrites` + split guidance. |
| D4 | **Authoring contract** lives in [`improved-scope.md`](../improved-scope.md) + prompt addendum; extract/WFM/scope share the same surrogate cookbook. |
| D5 | **Deterministic CI:** eight NL→JSON golden pairs (no live Gemini required for merge gate). Optional live extract smoke behind `PIVOT_RUN_LLM_EXTRACT=1`. |
| D6 | **Z3 smoke** per pattern (minimal policy compiles + `sat` or documented `unsat`). |
| D7 | Patterns **T6** and **T7** may use **vNext** (`K_OF_N`, `EXHAUSTIVE_SWITCH`, `TABLE_BLOCK`); policies use **`policy_semantics_version` 1.1** when vNext appears. |
| D8 | **Tester/critic** judge temporal NL against **assessment linearization** (pre-lowering); compile view may show only `LOGICAL_IMPLICATION` chains—document in prompts. |

---

## 2. The eight temporal surrogate patterns (normative)

Each pattern has: **ID**, **intent**, **preferred NL shape**, **templates**, **anti-patterns**, **example rule count**.

### T1 — Scalar ordering (“X before Y” on comparable ints)

| Field | Spec |
|-------|------|
| **Intent** | Two time-like or rank-like quantities in the **same** evaluation must satisfy an order relation. |
| **NL shape** | “`start_x` must be strictly before `start_y`.” / “Rank of task A must be less than rank of task B.” |
| **Templates** | **`VARIABLE_RELATIONAL`** (`left_variable`, `right_variable`, `LT` / `LTE` / `GT` / `GTE`). |
| **Variables** | Integers (or comparable ints); name them explicitly in NL (`start_`, `rank_`, `deadline_`). |
| **Anti-patterns** | Vague “before processing” without scalar variables; real-time clocks across days without a single int model. |
| **Lines** | Typically **1** line → 1 rule. |

---

### T2 — Prerequisite gating (“B only if A” / “before milestone M”)

| Field | Spec |
|-------|------|
| **Intent** | An obligation or permission is active only when a guard flag or prior condition holds. |
| **NL shape** | “Refund may be issued only if identity verification has passed.” / “Step B is required only when step A is complete.” |
| **Templates** | **`LOGICAL_IMPLICATION`** (trigger = guard, required = obligation). Optional **`CONSTANT_RELATIONAL`** on flags. |
| **Variables** | Booleans or 0/1 ints: `identity_verified`, `step_a_complete`, `step_b_required`. |
| **Anti-patterns** | Single line “B after A” with no named guard; English-only “before evaluation begins” with no state variable. |
| **Lines** | **1–2** lines (guard definition + implication) if needed. |

---

### T3 — Fixed total order A → B → C (implication chain)

| Field | Spec |
|-------|------|
| **Intent** | Completion of later steps implies completion of earlier steps (total order on flags). |
| **NL shape** | Separate lines: “If step B is complete then step A must be complete.” “If step C is complete then step B must be complete.” |
| **Templates** | **`LOGICAL_IMPLICATION`** × (n−1) for n steps; or **T4** phase enum alternative (below). |
| **Variables** | `step_a_complete`, `step_b_complete`, `step_c_complete` (booleans). |
| **Anti-patterns** | One line “events a, b, c must occur in order a, b, c” with no flags; collapsing default-order prose from source without `semantic_deltas`. |
| **Lines** | **n−1** lines for chain; or **1 + table** if using phase enum. |

---

### T4 — Finite phase / stage enum (ordered workflow state)

| Field | Spec |
|-------|------|
| **Intent** | Workflow is in exactly one of finitely many ordered stages; rules vary by stage. |
| **NL shape** | “Current phase must be one of: 1=init, 2=review, 3=closed.” + per-phase rules. |
| **Templates** | **`SET_INCLUSION`** or **`INT_RANGE`** on `phase`; **`EXHAUSTIVE_SWITCH`** (vNext) for per-value consequences; **`LOGICAL_IMPLICATION`** for transitions encoded as “if phase ≥ k …”. |
| **Caps** | ≤ **32** switch cases; domain ≤ **32** (vNext / contract). |
| **Anti-patterns** | Unbounded “current status” strings; string enums in atoms if Z3 sort expects int—prefer **int-coded** phases in NL. |
| **Lines** | **2+** (domain + at least one stage rule). |

---

### T5 — Exactly one active stage (mutual exclusion)

| Field | Spec |
|-------|------|
| **Intent** | At most one or exactly one of several modes/stages may be active. |
| **NL shape** | “Exactly one of draft_mode, review_mode, published_mode must be true.” |
| **Templates** | **`EXCLUSIVE_CHOICE`** (`exactly_one` / `at_most_one`, `variables[]`). |
| **Anti-patterns** | OR-of-flags without exclusivity; mixing with T3 without documenting overlap. |
| **Lines** | **1** line (+ separate implications per mode if needed). |

---

### T6 — Threshold of completed steps (“at least k of n verifications”) — ordering-adjacent

| Field | Spec |
|-------|------|
| **Intent** | Cardinality over conditions, common next to procedural policies (not strict sequence). |
| **NL shape** | “At least 3 of the following must hold: income verified, identity verified, address verified, employment verified, credit check passed.” |
| **Templates** | **`K_OF_N`** (vNext, preferred) or nested **`LOGICAL_IMPLICATION`** / OR-AND only for tiny n. |
| **Caps** | **n ≤ 10** clauses (`K_OF_N_MAX_CLAUSES`). |
| **Anti-patterns** | k-of-n with 15 undifferentiated bullets in one line—split clauses or ABORT. |
| **Lines** | **1** line (K_OF_N) or **n** lines (per-check implications) + **1** K_OF_N. |

---

### T7 — Phase-dependent rule table (switch / table block)

| Field | Spec |
|-------|------|
| **Intent** | Discriminant (e.g. `workflow_state`) determines which obligations apply. |
| **NL shape** | “When workflow_state is PENDING, approver must be assigned.” “When APPROVED, payment must be released.” (one line per row or one **`TABLE_BLOCK`**). |
| **Templates** | **`DECISION_TABLE_ROW`** / **`TABLE_BLOCK`** (vNext) or multiple **`LOGICAL_IMPLICATION`** with atoms on discriminant. |
| **Anti-patterns** | Mixing filesystem paths with phase rules in one unstructured line. |
| **Lines** | **1 per row** or **1 TABLE_BLOCK**. |

---

### T8 — Bounds on time-like counters (retries, deadlines as ints)

| Field | Spec |
|-------|------|
| **Intent** | Numeric limits on counters used as temporal surrogates (retry count, day index). |
| **NL shape** | “Retry count must be between 0 and 5 inclusive.” / “Days since purchase must be at most 30.” |
| **Templates** | **`INT_RANGE`** (vNext) or **`CONSTANT_RELATIONAL`** / pair of relations. |
| **Anti-patterns** | “Within 30 days” without defining `days_since_event` int; duration without a scalar model. |
| **Lines** | **1** line. |

---

## 3. Pattern → template quick map

| ID | Primary templates | vNext? |
|----|-------------------|--------|
| T1 | `VARIABLE_RELATIONAL` | No |
| T2 | `LOGICAL_IMPLICATION`, `CONSTANT_RELATIONAL` | No |
| T3 | `LOGICAL_IMPLICATION` | No |
| T4 | `SET_INCLUSION`, `EXHAUSTIVE_SWITCH`, `INT_RANGE`, `LOGICAL_IMPLICATION` | Yes |
| T5 | `EXCLUSIVE_CHOICE` | No |
| T6 | `K_OF_N` | Yes |
| T7 | `TABLE_BLOCK`, `DECISION_TABLE_ROW`, `LOGICAL_IMPLICATION` | Yes |
| T8 | `INT_RANGE`, `CONSTANT_RELATIONAL` | Yes (range) |

---

## 4. Implementation phases (complete checklist)

### Phase 0 — Documentation (source of truth)

| Task | File / action |
|------|----------------|
| P0.1 | Add **Part G: Temporal surrogates (in scope)** to [`improved-scope.md`](../improved-scope.md) — copy normative §2 from this plan (human-readable). |
| P0.2 | Add § to [`NagV/pivot_pipeline/PIVOT_TEMPLATE_SYSTEM.md`](../NagV/pivot_pipeline/PIVOT_TEMPLATE_SYSTEM.md) §5 “Expressivity”: temporal **surrogates in scope** vs **temporal logics out of scope**. |
| P0.3 | Update [`NagV/pivot_pipeline/ARCHITECTURE.md`](../NagV/pivot_pipeline/ARCHITECTURE.md) one paragraph: no time axis; eight surrogate patterns documented in `improved-scope.md`. |
| P0.4 | Cross-link this plan from [`dev_plans/VNEXT_OPERATOR_REMINDERS.md`](VNEXT_OPERATOR_REMINDERS.md) or README. |

**Acceptance:** A new author can read `improved-scope.md` only and write encodable temporal NL.

---

### Phase 1 — Shared prompt addendum (single cookbook)

**Add** `NagV/pivot_pipeline/prompts/temporal_surrogates_addendum.md`:

- One-page summary of T1–T8.
- Per-pattern: preferred English templates, variable naming, line-splitting rules.
- Explicit **“do not ABORT”** when NL already matches a surrogate row.
- Link to full examples in `temporal_surrogates_examples.md` (optional second file).

**Wire injection** (same pattern as encodability contract):

| Consumer | How |
|----------|-----|
| Scope rewriter | Append after encodability contract in [`scope_rewriter_agent.py`](../NagV/pivot_pipeline/scope_rewriter_agent.py) `_build_system_prompt`. |
| Extract | Append in [`extract.py`](../NagV/pivot_pipeline/extract.py) `_extract_prompt_template` after vNext addendum. |
| WFM scope rewrite chunks | Append in [`extract_scope_rewrite.py`](../NagV/pivot_pipeline/extract_scope_rewrite.py) or WFM pivot profile loader if centralized. |
| Extract ABORT scope rewrite | Append in [`extract_scope_rewrite.py`](../NagV/pivot_pipeline/extract_scope_rewrite.py) scope rewrite prompt builder. |

**Add** `paths.py`:

```python
def read_temporal_surrogates_addendum() -> str: ...
```

**Acceptance:** All four consumers receive identical temporal text; no drift between agents.

---

### Phase 2 — Scope rewriter (pre-WFM) — highest leverage

| Task | Detail |
|------|--------|
| P2.1 | Edit [`scope_rewriter_pre_wfm.md`](../NagV/pivot_pipeline/prompts/scope_rewriter_pre_wfm.md): under `temporal_or_process_order`, add **“when encodable per temporal_surrogates_addendum, rewrite to state-shaped lines; do not summarize away order.”** |
| P2.2 | Require **split** of T3 into multiple `plain_rules` lines with explicit `step_*_complete` or `phase` int. |
| P2.3 | Optional sidecar field `temporal_surrogate_applied`: array of `{ "line_index", "pattern_id": "T1"|…|"T8" }` — document in prompt; implement in `ScopeRewriterLLMOutput` (optional, `extra=ignore` on unknown). |
| P2.4 | Update [`dev_plan_scope_rewriter_prompt_hardening_v1.md`](dev_plan_scope_rewriter_prompt_hardening_v1.md) — mark Workstream B temporal bullets as **superseded by** this plan’s P2. |

**Verification:** Re-run scope rewriter on [`Evaluation_RUles_Processed.md`](../NagV/pivot_pipeline/inputs/Evaluation_RUles_Processed.md); count OUT_OF_SCOPE lines **before/after** on same WFM settings.

**Acceptance:** Sidecar lists `temporal_surrogate_applied` where used; `plain_rules` uses named flags/ints for former “priority order” prose.

---

### Phase 3 — Encodability contract + WFM

| Task | Detail |
|------|--------|
| P3.1 | Edit [`v1_policy_encodability_contract.md`](../NagV/pivot_pipeline/prompts/v1_policy_encodability_contract.md): new section **“Temporal surrogates (in scope)”** — bullet list T1–T8; clarify **not** LTL; prerequisite lines use `LOGICAL_IMPLICATION`. |
| P3.2 | Edit [`wfm_scope_rewrite.md`](../NagV/pivot_pipeline/prompts/wfm_scope_rewrite.md) / pivot WFM Agent 3 profile: “OUT_OF_SCOPE must not be used for T1–T8 shapes when rewritten per addendum.” |
| P3.3 | Document in WFM operator docs (if any) that **process order** lines should emerge as **multiple** normalized lines after Agent 3. |

**Acceptance:** WFM OUT_OF_SCOPE rate drops on temporal-heavy `latest.nl` fixtures (manual metric).

---

### Phase 4 — Extract + schema repair + ABORT rewrite

| Task | Detail |
|------|--------|
| P4.1 | [`extractor.md`](../NagV/pivot_pipeline/prompts/extractor.md): subsection **“Temporal surrogates”** — map each pattern to template; forbid ABORT when pattern matches. |
| P4.2 | [`extract_schema_repair.md`](../NagV/pivot_pipeline/prompts/extract_schema_repair.md): same mapping for repair pass. |
| P4.3 | [`scope_rewrite.md`](../NagV/pivot_pipeline/prompts/scope_rewrite.md) (post-ABORT): instruct rewriter to emit **T1–T8 shaped** English, not generic simplification. |
| P4.4 | Extract validation: no code change required if templates already registered; ensure error messages mention temporal addendum on unknown shape failures (optional helper text in `ExtractValidationError`). |

**Acceptance:** `validate_rule_dict` accepts golden JSON for all eight patterns (Phase 5).

---

### Phase 5 — Repairers + LLM gates

| Task | Detail |
|------|--------|
| P5.1 | [`repairer_piv_semantic.md`](../NagV/pivot_pipeline/prompts/repairer_piv_semantic.md) / structural: “temporal NL → implication chains / VARIABLE_RELATIONAL; do not delete prerequisite structure.” |
| P5.2 | Append temporal addendum to repairer bundle in [`repairer_piv_agent.py`](../NagV/pivot_pipeline/repairer_piv_agent.py) (or reference from `temporal_surrogates_addendum.md` only once). |
| P5.3 | [`tester_pivot_semantic.md`](../NagV/pivot_pipeline/prompts/tester_pivot_semantic.md): category `ordering` includes **step prerequisite** and **scalar before** mismatches; assessment view shows flags. |
| P5.4 | [`cross_critic.md`](../NagV/pivot_pipeline/prompts/cross_critic.md): do not treat prerequisite chains as “duplicate obligations” if NL requires order. |
| P5.5 | [`test_repairer.md`](../NagV/pivot_pipeline/prompts/test_repairer.md): preserve temporal structure in approved fixes. |

**Acceptance:** Repairer tests (mock) can patch a broken T2/T3 rule back to valid IR without stripping guards.

---

### Phase 6 — Fixtures + deterministic tests (CI gate)

**Directory:** `NagV/pivot_pipeline/tests/fixtures/temporal_surrogates/`

| File | Content |
|------|---------|
| `temporal_surrogates_manifest.json` | Index: `{ "pattern_id", "nl_line", "rules_file" }` × 8 |
| `t1_scalar_order_rules.json` | Single `VARIABLE_RELATIONAL` |
| `t2_prerequisite_rules.json` | `LOGICAL_IMPLICATION` + flags |
| `t3_chain_rules.json` | 2× `LOGICAL_IMPLICATION` chain |
| `t4_phase_switch_rules.json` | `EXHAUSTIVE_SWITCH` + `SET_INCLUSION` (≥2 cases) |
| `t5_exclusive_rules.json` | `EXCLUSIVE_CHOICE` |
| `t6_k_of_n_rules.json` | `K_OF_N` k=2, n=4 |
| `t7_table_block_rules.json` | `TABLE_BLOCK` 2 rows |
| `t8_int_range_rules.json` | `INT_RANGE` on retry_count |

**Tests** — `NagV/pivot_pipeline/tests/test_temporal_surrogates.py`:

| Test | Assert |
|------|--------|
| `test_temporal_golden_validate[T1..T8]` | `validate_rule_dict` + `parse_rules_document` + `load_rules_and_compile` |
| `test_temporal_z3_smoke[T1..T8]` | `run_z3_check` → `sat` (world provided in fixture meta if needed) |
| `test_temporal_nl_manifest_covers_eight_patterns` | manifest has 8 entries |
| `test_improved_scope_mentions_all_pattern_ids` | optional doc regression |

**NL golden file** — `extract_temporal_nl_golden.json` (parallel to `extract_vnext_nl_golden.json`):

- One entry per T1–T8 with `nl_line` + `expected_rules` (array).

**Acceptance:** `pytest NagV/pivot_pipeline/tests/test_temporal_surrogates.py` green in CI without API keys.

---

### Phase 7 — Template suite (executable regression)

| Task | Detail |
|------|--------|
| P7.1 | `tests/fixtures/template_suite_temporal_t2_prerequisite_suite.json` — `scenario` / `decision_query` on guard flags. |
| P7.2 | One suite per pattern **or** one combined `template_suite_temporal_smoke.json` pointing at minimal rules per pattern (8 scenarios). |
| P7.3 | `tests/test_template_suite_temporal.py` — all pass. |

**Acceptance:** Template executor reports 0 failed for temporal smoke suite.

---

### Phase 8 — Template generator (vNext + temporal worlds)

| Task | Detail |
|------|--------|
| P8.1 | Extend [`template_generator.md`](../NagV/pivot_pipeline/prompts/template_generator.md): when rules contain prerequisite chains or `K_OF_N`, generate worlds that set `step_*_complete` / verification flags consistently. |
| P8.2 | Extend [`template_generator_context.py`](../NagV/pivot_pipeline/template_generator_context.py): list variables from temporal-shaped rules (flags in trigger/required). |

**Acceptance:** On a T3 policy work dir, generated suite includes at least one world violating order (unsat) and one satisfying chain (sat).

---

### Phase 9 — Optional live extract e2e

| Task | Detail |
|------|--------|
| P9.1 | `test_extract_temporal_live.py` — parametrized over `extract_temporal_nl_golden.json`; `pytest.mark.skipif(not os.getenv("PIVOT_RUN_LLM_EXTRACT"))`. |
| P9.2 | Document in README and [`VNEXT_OPERATOR_REMINDERS.md`](VNEXT_OPERATOR_REMINDERS.md). |

**Acceptance:** Operator can run one command to validate Gemini extract chooses expected template family.

---

### Phase 10 — End-to-end manual playbook

| Step | Command / action |
|------|------------------|
| M1 | Scope-rewrite reference doc with new prompt → `latest.nl` |
| M2 | `pivot-pipeline --input latest.nl --work-dir … --with-tester` (optional) |
| M3 | Compare `rules_extracted.json` for T2/T3/T6 shapes on lines that were procedural in old runs |
| M4 | Record before/after OUT_OF_SCOPE counts in `dev_plans/temporal_surrogates_run_log.md` (create at verification time) |

**Acceptance:** Documented run log shows improvement on at least one real corpus.

---

## 5. Code changes summary (nothing optional for “complete”)

| Area | Change |
|------|--------|
| `paths.py` | `read_temporal_surrogates_addendum()` |
| `scope_rewriter_agent.py` | Inject addendum in system prompt |
| `extract.py` | Inject addendum |
| `extract_scope_rewrite.py` | Inject addendum (ABORT + chunk paths) |
| `scope_rewriter_agent.py` | Optional `temporal_surrogate_applied` on sidecar model |
| Prompts | 10 files listed in Phases 1–5 |
| Docs | `improved-scope.md`, `PIVOT_TEMPLATE_SYSTEM.md`, `ARCHITECTURE.md` |
| Tests | `test_temporal_surrogates.py`, `test_template_suite_temporal.py`, fixtures × 10+ |
| Template gen | `template_generator.md`, `template_generator_context.py` |

**No change required:** `vnext_lowering.py`, pathway compiler, Z3 encoder (unless fixture reveals sort bug for string phases—then fix fixtures to use ints).

---

## 6. Explicit non-goals (this plan)

- New templates: `TEMPORAL_BEFORE`, `EVENT_SEQUENCE`, etc.
- LTL / CTL / “eventually” / “always” / “until”.
- Multi-step simulation or event logs over time.
- Calendar dates as strings without int encoding.
- Automatic inference of order from English without named variables (LLM must still extract explicit structure).
- Nagini / CPMpy paths (Pivot-only plan).

---

## 7. Acceptance criteria (integration complete)

- [ ] `improved-scope.md` documents T1–T8 with NL examples and line-splitting rules.
- [ ] `temporal_surrogates_addendum.md` injected into scope rewriter, extract, and scope-rewrite prompts.
- [ ] `v1_policy_encodability_contract.md` states temporal surrogates are **in scope** (not ABORT-by-default).
- [ ] Eight deterministic fixture policies compile; eight Z3 smokes pass.
- [ ] Eight NL goldens validate via `validate_rule_dict` without LLM.
- [ ] Template suite temporal smoke passes.
- [ ] Tester/repairer/cross-critic prompts mention prerequisite / ordering checks on assessment view.
- [ ] Optional: live extract e2e behind env flag documented.
- [ ] Manual run log on evaluation reference corpus (informative OUT_OF_SCOPE delta).
- [ ] `pytest NagV/pivot_pipeline/tests` green.

---

## 8. Suggested implementation order

| Order | Phase | Risk |
|-------|-------|------|
| 1 | P0 Documentation | Low |
| 2 | P1 Shared addendum + `paths.py` | Low |
| 3 | P6 Fixtures + tests (drives correctness) | Low |
| 4 | P2 Scope rewriter | Medium |
| 5 | P3 WFM + contract | Medium |
| 6 | P4 Extract + ABORT rewrite | Medium |
| 7 | P5 Repairer + gates | Low |
| 8 | P7 Template suite | Low |
| 9 | P8 Template generator | Low |
| 10 | P9 Live extract e2e | High (optional) |
| 11 | P10 Manual playbook | Low |

---

## 9. References

| Doc | Role |
|-----|------|
| [`improved-scope.md`](../improved-scope.md) | Author-facing template + temporal catalog (extend in P0) |
| [`dev_plan_scope_rewriter_prompt_hardening_v1.md`](dev_plan_scope_rewriter_prompt_hardening_v1.md) | Prior partial temporal guidance |
| [`dev_plan_vnext_pipeline_integration_v1.md`](dev_plan_vnext_pipeline_integration_v1.md) | T4, T6, T7, T8 vNext templates |
| [`dev_plans/VNEXT_OPERATOR_REMINDERS.md`](VNEXT_OPERATOR_REMINDERS.md) | Operator checklist |

---

## 10. Ready

This plan is **ready for execution** starting with **P0 + P1 + P6** (docs, addendum, tests), then **P2–P5** (prompts), then **P7–P10** (suite, generator, manual verification).
