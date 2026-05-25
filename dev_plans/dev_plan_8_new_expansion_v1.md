# Dev plan: 8 new expansion templates (Pivot IR vNext fragment)

**Status:** planning only — **not implemented** by this document.  
**Codename:** `8-new-expansion`  
**Goal:** Add eight **additive**, **capped**, **lowering-based** rule templates so more real policy idioms are maintainable, while preserving today’s satisfiability story (finite attributes, conservative SMT).

---

## 1. Principles (apply to every item)

- **Additive:** Existing `MetaScheme` / rules without new templates behave unchanged.
- **Lower first:** New templates compile to a **known-safe core** (today’s `ConditionExpr` + existing rule shapes, or a documented minimal extension agreed in Phase 0).
- **Caps everywhere:** Max row count, max list length, max unfolding size, max definition depth — enforced at validate time with clear errors.
- **Version gate:** Bump `policy_semantics_version` (or introduce `pivot_ir_extensions` manifest) so old tooling rejects unknown templates early.
- **Test matrix:** For each template — unit tests for lowering, IR round-trip, Z3 smoke, one template-suite instance, extract golden (optional) and repairer denylist updates.

---

## 2. Implementation order (increasing integration risk)

Ship in this order so the pipeline hardens incrementally:

| Phase | Template | Rationale |
|-------|----------|-----------|
| A | `INT_RANGE` | Pure sugar → relational atoms; touches few layers. |
| B | `DECISION_TABLE_ROW` | Single-row implication sugar; proves lowering + extract path. |
| C | `TABLE_BLOCK` | Multi-row emission; tests id allocation and determinism. |
| D | `BOUNDED_FORALL` | List unfold; cap-driven explosion control. |
| E | `K_OF_N` | Cardinality / PB or explicit unfold; Z3 path validation. |
| F | `EXHAUSTIVE_SWITCH` | Interacts with exclusivity + pathways; needs pathway compiler review. |
| G | `DEFINED_AS` | DAG on definitions + sorts + precheck; cross-cutting. |
| H | `SUM_THRESHOLD` | Arithmetic surface + performance; last. |

Parallel **cross-cutting** tracks (can overlap late phases): extract prompts, repairer prompt slices, `meta_scheme_to_markdown` / critic hints, registry variable discovery, precheck heuristics.

---

## 3. Per-template checklist

For **each** of the eight, complete at minimum:

1. **Schema** — Pydantic model in `ir.py` (or extension module), `template_class` discriminator, `extra=forbid`.
2. **Validate** — Structural validation + cap enforcement (constants in `pivot_pipeline/constants.py` or template-local caps).
3. **Lower** — Pure function: `TemplateX → list[AtomicRule]` or `→` augmented condition IR; **no** LLM in lowering.
4. **Compile integration** — Either merge lowered rules **before** `build_meta_scheme`, or extend `load_rules_and_compile` with a **pre-pass** that expands new templates into core rules (prefer single entrypoint).
5. **Z3** — Ensure `z3_compile` only sees core constructs after lowering; add fixture policy per template.
6. **Extract** — Prompt section + JSON schema for Phase extract (optional: start with “manual JSON only” + tests, then LLM).
7. **Repairer** — Denylist + one minimal example per template; compile-feedback compatible.
8. **Synthetic / critic** — How backtranslate names the construct; critic guidance so DRIFT isn’t spurious.
9. **Template suite** — One executable instance per template in `template_suite` tests or exports.
10. **Docs** — `PIVOT_TEMPLATE_SYSTEM.md` section + “out of scope” reminder.

---

## 4. Template specifications (concise)

### A. `INT_RANGE`

- **Fields (conceptual):** `variable`, `lo`, `hi` (inclusive), same `BaseRule` envelope.
- **Lowering:** `AND` of `GTE`/`LTE` atoms (or equivalent `CONSTANT_RELATIONAL` pair) per sort rules.
- **Risks:** Open bounds, wrong inclusive/exclusive semantics — document and test edge `lo==hi`.

### B. `DECISION_TABLE_ROW`

- **Fields:** `trigger_condition` (conjunctive normal form or single `ConditionExpr` AND tree), `required_condition` or linkage to yields-style outcome per existing encodings.
- **Lowering:** `LOGICAL_IMPLICATION` with same `rule_id` / pathway behavior as today.
- **Risks:** None critical if lowering is one-to-one.

### C. `TABLE_BLOCK`

- **Fields:** `rows: list[DECISION_TABLE_ROW-like payload]`, shared `applies_to`, optional `table_id` for traceability.
- **Lowering:** Deterministic `rule_id` suffix from `(table_id, row_index)`; stable sort order.
- **Risks:** Row count cap; duplicate triggers — validate or warn.

### D. `BOUNDED_FORALL`

- **Fields:** `iter_var` or implicit binding, `domain: list[Scalar]` (capped), `body` template parametrized — **simplest v1:** body is `required_condition` pattern with placeholder replaced by each domain value, or per-value `trigger_condition`.
- **Lowering:** `AND` over instantiated conditions (or instantiated implications).
- **Risks:** Domain size; extract must emit finite lists only.

### E. `K_OF_N`

- **Fields:** `k`, `clauses: list[ConditionExpr]` (bool-like or atom conditions), cap `n ≤ N_MAX`.
- **Lowering:** Either pseudo-Boolean encoding in Z3 layer or explicit DNF for small n only.
- **Risks:** Combinatorics — **hard cap** `N_MAX` (e.g. 8–10); document O(choose(n,k)).

### F. `EXHAUSTIVE_SWITCH`

- **Fields:** `discriminant_var`, `cases: list[{value, consequence}]`, optional `default_consequence`.
- **Lowering:** Mutual exclusivity + coverage (`EXCLUSIVE_CHOICE`-like or disjoint atoms) + implications per case; align with pathway `must_satisfy_all`.
- **Risks:** Pathway compiler and preemption interaction — **golden tests** for “exactly one case” and missing-case UNSAT.

### G. `DEFINED_AS`

- **Fields:** `variable`, `sort`, `definition` (restricted expression: no circular refs), optional `depends_on` list for tooling.
- **Lowering:** Introduce **helper** variable + `LogicalIff` or definitional equality encoding already supported by Z3 backend; or substitute everywhere (prefer helper + acyclic check).
- **Risks:** Cycles, sort mismatches — **DAG validation**; extend `variable_sorts` and precheck “constants in NL” heuristics.

### H. `SUM_THRESHOLD`

- **Fields:** `terms: list[{coeff, variable}]`, `operator`, `limit` (all int), cap count and coefficient range.
- **Lowering:** Single inequality over sum of ints (extend only if Z3 encoding supports; else `ARITHMETIC_EVALUATION` chain).
- **Risks:** Performance — cap terms; avoid mixing bools without explicit 0/1 lifting.

---

## 5. Cross-cutting workstreams

- **Policy semantics version** — Bump `POLICY_SEMANTICS_VERSION_DEFAULT` or parallel extension flag; migration notes for stored JSON.
- **Sanitizer** — Extend `sanitize_rules_jsonable` for new keys only (pattern established in `ir.py`).
- **LLM strategy** — Prefer **per-phase narrow prompts** or template **router** to limit simultaneous template vocabulary; avoid one 40-page mega-prompt.
- **Observability** — Log lowering stats (rows expanded, definitions count) in `run_summary` for debugging.

---

## 6. Acceptance criteria (program-wide)

- All eight templates have **deterministic lowering tests** and **Z3 smoke** on a minimal policy.
- No regression on existing `pytest` for pivot_pipeline / pivot_wfm.
- At least **one** template-suite scenario per template; optional **e2e** extract policy for 2–3 templates only initially.
- Documentation lists **in-scope** vs **out-of-scope** (unbounded ∀, raw string theories, etc.).

---

## 7. Explicit non-goals (this plan)

- General first-order / temporal logics, ML-learned scoring inside core IR, unrestricted string matching in Z3.
- Automatic grounding of unbounded entity sets (orgs, people) without a finite registry.

---

## 8. Ready to execute?

When you pick this up: start **Phase A** in a feature branch, merge lowering tests before enabling extract prompts; roll forward through H with version bumps as needed.

**This file is ready** as `dev_plans/dev_plan_8_new_expansion_v1.md`.
