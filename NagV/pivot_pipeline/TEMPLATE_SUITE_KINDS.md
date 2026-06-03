# Template suite kinds — what each test does (plain language)

**Audience:** Showcase, onboarding, diagram labels.  
**Example policy:** Backend Engineer 2 — `exports/pivot_runs/Backend_Engineer2_v1_wfm/template_suite_generated.json`.

Two different “template” ideas are easy to mix up:

| Concept | Where it lives | What it is |
|---------|----------------|------------|
| **Policy IR `template_class`** | `rules_extracted.json` | How each **rule line** is encoded (`LOGICAL_IMPLICATION`, `K_OF_N`, …) — see [`PIVOT_TEMPLATE_SYSTEM.md`](PIVOT_TEMPLATE_SYSTEM.md). |
| **Template suite `template_kind`** | `template_suite_generated.json` | Eight **test shapes** the generator fills; Z3 runs each instance and compares to **golden** expectations. |

This document is about the **suite** side only.

**Related:** [`prompts/template_generator.md`](prompts/template_generator.md) (golden shapes), [`template_suite/execute_z3.py`](template_suite/execute_z3.py) (executor), [`README.md`](README.md) (CLI flags).

---

## The eight `template_kind` values

### 1. `scenario`

**What it tests:** “If I plug in this candidate profile, can the **whole policy** still hold at once?”

**How:** Z3 checks **policy ∧ world** — is there any satisfying assignment? Golden: `"sat": true` or `false`.

**BE2 example (`scenario_valid_candidate`):** Strong-ish profile (5 years, Python, REST, Postgres, Git, tests, code review, English). Expect **`sat: true`** — a person who meets the hiring bar is *possible* under the model.

**Showcase line:** “The formal policy isn’t internally broken; this candidate shape is admissible.”

---

### 2. `decision_query`

**What it tests:** “For this world, is **one specific rule** (or bool) **satisfied or not**?”

**How:** Build policy ∧ world; if SAT, read that rule’s truth value in the model. Golden: `"decision": "satisfied"` or `"unsatisfied"`.

**BE2 example (`query_experience_threshold`):** World with exactly **2 years** experience; query **R0001** (≥2 years). Expect **satisfied** — boundary-at-minimum case.

**Showcase line:** “Threshold rules behave at the cut point.”

---

### 3. `rule_attribution`

**What it tests:** “When I ask about rule X, **which rules** does the engine report as satisfied in the model?”

**How:** Same as decision query, plus list **all rule ids** that evaluate true (not only the queried one).

**BE2 example (`attr_database_requirement`):** Query **R0004** (database). Golden expects only `["R0004"]`, but the engine often returns **every** rule that’s true in a rich world — that’s why this instance **failed** in `template_run_report.json` (attribution vs pathway “all satisfied”).

**Showcase line:** “Who gets ‘credit’ for satisfaction — useful for debugging, picky about golden lists.”

---

### 4. `boundary`

**What it tests:** “As I move **one variable** through three values, how does **one rule’s** decision change?”

**How:** `world_base` + axis variable at values `[v1, v2, v3]` → three worlds → three decisions. Golden: three `"satisfied"` / `"unsatisfied"` labels.

**BE2 example (`boundary_years_exp`):** `years_backend_experience` = **1, 2, 3**; query **R0001**. Golden: **unsatisfied, satisfied, satisfied** — below 2 fails, at/above 2 passes.

**Showcase line:** “The ≥2 years rule actually flips at the threshold.”

---

### 5. `counterfactual_flip`

**What it tests:** “If I change **one thing** in an otherwise good profile, does the **target rule** flip from satisfied → unsatisfied (or does the whole world become impossible)?”

**How:** Run **base** world and **mutant** world; compare decisions on the queried rule. Golden: `expect_flip: true` or `mutant_unsat: true` when turning off English makes the policy impossible, not just one rule false.

**BE2 example (`flip_english_requirement`):** Same profile except `candidate_can_write_technical_english: false`. Query **R0008**. Expect base **satisfied**, mutant breaks policy (**flip** or **mutant UNSAT**) — catches “hard implication on `is_candidate`” encoding issues.

**Showcase line:** “Flipping one requirement really matters; encoding isn’t vacuous.”

---

### 6. `obligation_inventory`

**What it tests:** “Does the compiled model expose the **right list of obligations** on the default pathway?”

**How:** Minimal world (often just `is_candidate: true`); golden lists `obligations` with rule ids matching `meta_scheme` **`must_satisfy_all`** (R0001–R0008).

**BE2 example (`inventory_all_rules`):** Expect all **eight** rules on the hiring pathway — sanity check that nothing was dropped at compile time.

**Showcase line:** “The pathway still says ‘all eight requirements must hold.’”

---

### 7. `sat_unsat`

**What it tests:** “Is this world **compatible** or **impossible** with the full policy?” (Coarser than `scenario`; golden uses `"expect": "sat"` / `"unsat"`.)

**How:** Same SAT check as scenario, different golden field name.

**BE2 example (`unsat_insufficient_exp`):** `years_backend_experience: 0` only (plus `is_candidate`). Expect **`unsat`** — zero years can’t satisfy a policy that requires ≥2 on the pathway.

**Showcase line:** “Obviously bad profiles are rejected by the solver.”

---

### 8. `pairwise`

**What it tests:** “Do **two small changes** that should be equivalent for this rule produce the **same** outcome?”

**How:** Shared `world` + `query_a` fragment + `query_b` fragment; same top-level `query` (rule id). Golden: `expect_equal: true` — decisions for A and B must match.

**BE2 example (`pairwise_language_choice`):** Python true / Java false vs Python false / Java true; query **R0002** (any one language). Expect **equal** — either language alone should satisfy the OR.

**Showcase line:** “Disjunctive ‘Python OR Java’ doesn’t secretly favor one atom.”

---

## How the generator uses them

With `--with-template-generator`, the LLM fills **instances** under these fixed kinds using **only** variable names and rule ids from your policy. It aims for **at least one instance per kind** when the policy is rich enough — the BE2 suite includes **all eight**.

| Artifact | Path (BE2 run) |
|----------|----------------|
| Generated suite | `NagV/exports/pivot_runs/Backend_Engineer2_v1_wfm/template_suite_generated.json` |
| Pass/fail report | `NagV/exports/pivot_runs/Backend_Engineer2_v1_wfm/template_run_report.json` |
| Failed-instance detail | `NagV/exports/pivot_runs/Backend_Engineer2_v1_wfm/template_failure_bundles.json` |

Failures often mean **golden vs engine semantics** (especially `rule_attribution`) or **IR shape** (especially `counterfactual_flip`), not “Z3 is broken.”

---

## Quick reference table

| `template_kind` | One-line test |
|-----------------|---------------|
| `scenario` | Whole policy + world: SAT or not? |
| `decision_query` | One rule satisfied/unsatisfied in this world? |
| `rule_attribution` | Which rule ids are satisfied in the model? |
| `boundary` | Three values on one axis → three rule decisions |
| `counterfactual_flip` | One-field change → rule flips or world UNSAT |
| `obligation_inventory` | Pathway `must_satisfy_all` list matches golden |
| `sat_unsat` | World compatible vs impossible (expect sat/unsat) |
| `pairwise` | Two equivalent tweaks → same decision on one rule |

---

*Document version: 2026-05-23*
