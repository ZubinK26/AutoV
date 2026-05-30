# Dev plan: Policy case strict semantics — tiering, derive, encoding (engine-wide)

**Status:** Implemented (2026-05-23) — **§8 resolved (§9 defaults, domain-agnostic)**  
**Priority:** P0  
**Problem:** Strict query reports `compatible` when an external source clearly fails requirements. Stated+CWA works on a small `unknown` set; mis-tiered “derived” + SAT witness + vacuous conditional encoding bypass policy intent.  
**Prerequisite:** v4 policy case pipeline (`dev_plan_external_world_tester_v4_policy_world_pipeline_v1.md` — implemented)  
**Domain:** **Policy-agnostic.** Applies to any `rules_extracted.json` + any unstructured or structured **external source** (CV, contract, incident report, audit memo, form, log). Backend Engineer / recruitment paths are **regression fixtures only**, never branching logic in engine code.

**Related:** Template suite vacuous-trigger issue (`dev_plan_k_of_n_way_b_in_place_enforcement_v1.md` — same root encoding); v4 §4.3 derive wording assumed witness = rule outputs (false in practice).

---

## 1. Vision (one paragraph)

**Strict** means: given what the **external source** **supports** (stated) and what it **does not mention** (grounded → false/0 at query), plus values **forced by the policy structure** on true rule outputs only, is the policy **satisfiable**? **Lenient** remains existential completion for exploration. **Derived** is only for variables the policy **computes** (aggregates, rule verdict flags), never for source evidence mis-labeled because it appears in a `required_condition`. **Conditional rules** must not be skippable via a free duplicate “enum” integer. **No domain branches** (not recruitment, not HR, not “CV-only”).

---

## 1b. Domain neutrality (engine contract)

| Concept | Engine term | Not tied to |
|---------|-------------|-------------|
| Input text | `external_source` / `policy_case_source` | résumé, job, candidate |
| Facts read from source | **grounded** / **stated** | skills, years, employer |
| Rule-computed slots | **derived** | aggregates named in one policy |
| “If context X then obligation Y” | **scoped rule** (trigger on discriminator vars) | role, position, product line, jurisdiction — names come from **that policy’s IR** |
| Optional operator context | **`case_scope`** in source envelope or CLI (generic JSON map var→value) | “this application is for job Z” hardcoding |

Every fix in this plan is defined over **IR shape** (`LOGICAL_IMPLICATION`, `K_OF_N`, `CONSTANT_RELATIONAL`, atom literals), not over English domains.

---

## 2. Problem summary (what went wrong)

| Layer | Intended | Actual (cv2 repro) |
|-------|----------|---------------------|
| **Tiering** | Derived = rule outputs | `classify_variable_tiers` marks vars in **any** `required_condition` head (+ all `CONSTANT_RELATIONAL` yields bools) as derived → years, languages, position treated as derived |
| **Derive** | Compute rule outputs from stated + policy | `derive_z3_witness` pins stated only, copies **all** derived-tier vars from **any** SAT model → values that merely make policy SAT |
| **Strict query** | stated + **sound** derived + unknown→false/0 | Trusts witness derived; CWA only on 6 grounded unknowns |
| **Encoding** | `IF role == X THEN req` enforces when case is in scope | String `X` → separate Int variable; model sets `position ≠ X` → implication **vacuous** → requirements never apply |
| **Compatible** | (human) source fails obligations | (code) ∃ assignment satisfying pathway — different question |

**User expectation (strict):** not found → false/0 **for all document-bound requirement variables**; derived = programmatically correct from rules; incompatible when CV cannot support obligations.

**Design intent (v4) was right; execution diverged** because tiering + witness derive + encoding do not match that intent.

---

## 3. Target semantics (engine contract)

### 3.1 Variable tiers (policy-agnostic)

| Tier | Meaning | Phase-1 extract | Strict query |
|------|---------|-----------------|--------------|
| **grounded** | Evidence / applicant facts the document may support | `present` / `inferred` / `not_found` | stated value or **unknown → CWA false/0** |
| **derived** | Rule-computed only (not read from doc) | **No** phase-1 row | Fixed by **rule evaluation** (see §4.2), never free witness filler for strict |

**Derived set (v1 rule — answer Q1 in §8 before coding):**

- Every `K_OF_N.result_variable` (after lowering, include lowered names if catalog uses them).
- Bool variables that appear **only** as consequents / yields targets and **never** as atoms in `trigger_condition`, `clauses`, or `CONSTANT_RELATIONAL.variable` used as applicant evidence.
- **Exclude:** ints and bools in `required_condition` trees that represent applicant facts (years, skills, languages, APIs, DB flags).
- **Exclude:** `CONSTANT_RELATIONAL.variable` unless that variable is exclusively a `result_variable` (aggregate), not e.g. `applicant_has_git_experience`.

### 3.2 Strict world construction

```text
strict_world = stated
             ∪ evaluate_derived(stated, unknown_defaults= CWA on grounded not_found)
             ∪ unknown_grounded → false/0
```

- **No** `z3_witness` values for strict on derived tier.
- If derived evaluation cannot fix a derived var (e.g. stated+CWA contradicts rule), strict → **incompatible** (or `blocked_derive` — Q4).

### 3.3 Lenient (unchanged intent)

- Pin **stated** only; Z3 completes unknown + derived existentially.
- Witness labeled **non-authoritative** in report (`witness_note` already exists; strengthen wording).
- Optional: lenient incompatible while strict compatible → report flag `lenient_only_sat` (Q5).

### 3.4 Conditional / enum encoding (policy-agnostic)

When a policy uses `atom` with `variable = V` and string `value = "literal"` (role, mode, enum):

- **Compile or query shim** must prevent vacuous satisfaction by a free shadow variable.
- **Not** “pin Backend Engineer” — engine treats **all** such literals uniformly (§5).

### 3.5 Compatibility label (clarify product — Q6)

Document in README / report:

| Term | Meaning |
|------|---------|
| `compatible` | ∃ variable assignment: pathway formulas SAT |
| `incompatible` | policy ∧ strict_world UNSAT |
| (optional v1.1) `evidence_incomplete` | strict SAT but N grounded vars still `unknown` — not the same as pass |

---

## 4. Implementation plan (after §8 answered)

### Step 1 — Fix `classify_variable_tiers` (P0)

**File:** `pivot_pipeline/external_tester/variable_tiers.py`

- Replace `derived = heads | k_of_n_results | const_sat_bool` with §3.1 rule (exact formula locked in Q1).
- Add `collect_evidence_variables(rules)` — triggers, clauses, non-aggregate `CONSTANT_RELATIONAL.variable`, all `required_condition` **inputs** (vars used in atoms on the “evidence” side of rules — for `LOGICAL_IMPLICATION`, treat **required** subtree vars as evidence unless Q1 says otherwise).
- Export helper for tests + fill prompts (`variable_catalog.py` tier excerpt).

**Tests:** extend `test_classify_variable_tiers` with a **minimal synthetic policy** in `tests/fixtures/` (scoped implication + `K_OF_N` aggregate + global constant) — no production policy ids in tier logic.

**Acceptance:** On any policy, evidence atoms in triggers/clauses/required are **grounded**; `K_OF_N.result_variable` (and verdict-only bools per Q1b) are **derived**. Regression run optional: one real work-dir fixture.

---

### Step 2 — Strict derive: rule evaluation, not witness (P0)

**Files:** `world_builder.py`, new `derive_eval.py` (or `policy_derive.py`)

**Add** `evaluate_derived_strict(meta, rules, stated_pin, unknown_pin) -> list[DerivedAssignment]`:

1. Build `strict_partial = stated_pin ∪ CWA(unknown_grounded)`.
2. For each derived-tier variable `d`, compute value by **policy-local rules** (order per Q2):
   - **K_OF_N:** evaluate clauses against partial world (k-of-n on clause atoms); set `result_variable` true/false per engine semantics (reuse lowering eval or mirror `execute_z3` on single-rule probe — Q2).
   - **Bool verdict flags:** only if defined by rules whose triggers are **active** under §5 encoding (see Step 3).
3. Do **not** call full-policy SAT to fill derived slots.

**Wire:** `build_policy_case_world(..., derive_mode=...)`:

| Mode | Behavior |
|------|----------|
| `z3_witness` (default today) | Keep for **lenient path / legacy** or rename `witness_explore` |
| **`strict_eval` (new default for strict query)** | Use `evaluate_derived_strict` for `policy_case_world.json` → strict query |
| `llm_glossary` | Unchanged optional |

**Env:** `PIVOT_CASE_DERIVE_MODE=strict_eval|z3_witness|llm_glossary` — default **`strict_eval`** after migration (Q3).

**Tests:**

- Fixture: stated minimal facts, unknown clause flags → 0, derived aggregates false → strict **incompatible** on synthetic policy when Step 3 active.
- `test_derive_z3_witness` remains but not used for strict query assembly.

**Acceptance:** one weak-source regression fixture → strict **incompatible**; one strong-source → compatible — **no** `if policy_id ==` branches.

---

### Step 3 — Encoding: enum / role literals (P0)

**Problem (simple):** `applicant_position == backend_engineer` is compiled as `Int(applicant_position) == Int(backend_engineer)` with **two** variables. SAT can set them unequal so **if-then rules never apply**.

**Generic fixes (pick one in Q7 — implement one, document others as rejected):**

| Option | Where | Idea |
|--------|-------|------|
| **A. Literal IntVal** | `z3_compile.py` `_scalar_to_z3` / `encode_condition` | String atom values that are policy constants → fixed `IntVal` / hashed enum int in **same** variable slot; no second variable |
| **B. Enum sort** | `variable_sorts` + compile | Declared sort `Enum` for named variables; world must use canonical enum value |
| **C. Query-time pathway activation** | `policy_query.build_query_world` | For variables appearing in `EQ` with string literal in **≥1** rule trigger, add **activation constraint** for “case under evaluation”: pin `V` to literal’s canonical int **only in external tester / template scenario paths** (compile unchanged) |
| **D. Implication semantics change** | `encode_rule` | Use `And(trigger, required)` instead of `Implies(trigger, required)` for pathway **must_satisfy** — **large blast radius**; likely reject |

**Recommendation for plan (pending Q7):** **A + catalog** — harvest literal strings per variable from rules; compile `EQ` to compare variable to `IntVal(hash(literal))` or registry slug id; single variable.

**Also apply to:** `pivot_pipeline/template_suite/execute_z3.py` worlds (same vacuous issue in template boundary tests).

**Tests:**

- Policy with one `LOGICAL_IMPLICATION` role gate + years GTE 2; world `{applicant_position: canonical, years: 1}` → **UNSAT**; `{years: 2}` → SAT.
- Regression: existing `test_z3_compile` / template suite SAT smoke still pass.

**Acceptance:** gen_004-style boundary (years 1/2/3) fails at 1 **without** policy-specific pins when role world uses same canonical value.

---

### Step 4 — Strict query assembly (P1)

**File:** `policy_query.py` / `world_to_z3.py`

- `build_query_world` for strict: use **strict_eval** derived list only; never merge witness derived.
- Trace: `derive_mode`, `derived_source: strict_eval`, list derived vars.
- Report: split `defaulted_variables` vs `derived_variables` vs `stated_variables`.

---

### Step 5 — Fill + provenance alignment (P1)

**Files:** `fill_orchestration.py`, prompts `external_world_extract_phase1.md`

- Phase-1 batches only **grounded** (already); after tier fix, years/langs appear in extract catalog.
- Provenance: still **stated only** — do not require quotes for derived.
- Optional completeness: warn if >X% grounded `not_found` for a policy with only conditional globals (Q5).

---

### Step 6 — Docs + diagrams (P2)

| Doc | Update |
|-----|--------|
| `external_world_tester_overview.md` | Strict vs lenient; derived definition; compatible ≠ hiring pass |
| `dev_plan_external_world_tester_v4_*.md` | Addendum pointer — §4.3 witness superseded for strict |
| `pivot_pipeline/README.md` | `PIVOT_CASE_DERIVE_MODE`, encoding note |
| `ARCHITECTURE.md` | Tier + strict_eval + literal encoding |

---

### Step 7 — Verification matrix (fixtures, not production edits)

| Case | Strict expected |
|------|-----------------|
| Strong-source fixture (any domain) | compatible (or high-unknown warning — Q6) |
| Weak-source fixture (any domain) | **incompatible** under strict when global facts are not over-extracted (issue-tracking-only synthetic world) |
| Weak-source + LLM fill infers git/writing `present` | strict may stay **compatible** — engine honors stated facts; scoped rules inactive if `applicant_position` is `unknown` (Q8a) |
| Tiny synthetic tier fixture | `ok`-style verdict bool derived; evidence ints grounded |
| Template boundary with scoped discriminator | decisions reflect enforced trigger when literal encoding + world pin active |

---

## 5. Position / conditional encoding — is there a fix? (answer for §3 user question)

**Yes — generic engine fix, not “pin Backend Engineer.”**

The bug is: **string policy literals became a second free integer variable**, so “if role is X” can be false while the case still satisfies the pathway.

**Fix class:** ensure literals in `EQ`/`NEQ` atoms refer to **constants in the same variable’s domain**, not a shadow variable (§4 Step 3). Applies to **any** policy with role/mode/category gates (recruitment, insurance, BE, etc.).

**Interaction with strict world:** once encoding is fixed, **scoped** rules apply when **discriminator variables** in triggers are grounded to the literal in the IR (from stated extract, **`case_scope`**, or CWA — see Q8). No special case for any one policy id or source type.

---

## 6. Stated + derived in strict — design reaffirmed

| Question | Answer |
|----------|--------|
| Was stated+derived the right idea? | **Yes** |
| What went wrong? | **Derived tier contained evidence vars**; **derive used full-policy SAT witness** instead of rule evaluation |
| Fix | **Narrow derived tier** + **`strict_eval` derive** + **encoding** so conditionals fire when evidence says in-scope |

---

## 7. Non-goals (v1)

- Changing pivot extract / Tester NL alignment.
- Obligation checklist UX (“3/9 requirements met”) — separate product.
- Auto-fixing fill LLM under-extraction (warn only P2).
- `compatible` rename breaking CI without migration shim (Q6).

---

## 8. Resolved decisions (2026-05-23)

| ID | Resolution |
|----|------------|
| **Q1** | **(b)** Derived = `K_OF_N.result_variable` ∪ bool vars **not** in evidence. Evidence = trigger/clause atoms + **int** atoms in `required_condition` + non-aggregate `CONSTANT_RELATIONAL.variable` (bool consequents are **not** evidence). |
| **Q2** | **(a)** `strict_eval`: evaluate `K_OF_N` clause atoms against partial world in Python (`k` satisfied count); bool verdict-only via material `Implies(trigger, required)` when needed. |
| **Q3** | **`strict_eval` default**; `z3_witness` retained as `PIVOT_CASE_DERIVE_MODE=z3_witness` for one release. |
| **Q4** | **Short-circuit:** if policy ∧ stated-pin alone is UNSAT → `incompatible` before derive (with explanation). |
| **Q5** | **Report flag** `strict_incompatible_lenient_compatible` on addendum/report when lenient SAT and strict UNSAT (no hard fail). |
| **Q6** | Keep **`compatible` / `incompatible`**; add `coverage.high_unknown_rate` warning when grounded `not_found` / unknown ratio exceeds threshold (env, default off). |
| **Q7** | **(A)** Harvest string atom literals from IR; encode as fixed `IntVal` on the **left-hand** variable (no shadow int per literal). |
| **Q8** | **(a)+(b):** CWA when discriminator not grounded; optional generic **`case_scope`** on `ExternalSourceEnvelope` / source JSON (var → value, literals use harvested int ids). No domain-specific env flags. |

See §8.1 for Q8 semantics. **Implementation proceeds under this table.**

### 8.1 Q8 in domain-neutral terms

Many policies contain **scoped obligations**: `IF <discriminator> == <literal> THEN <requirement>` (discriminator names and literals are whatever that policy defines: `mode`, `region`, `tier`, `applicant_class`, …).

When the **external source** does not ground a discriminator variable:

| Option | Behavior | Tradeoff |
|--------|----------|----------|
| **Q8a (default strict)** | CWA → false/0 → trigger false → scoped consequent **not enforced** | Honest: “source didn’t establish context X.” Global/unconditional rules still enforced. May report `scoped_rules_inactive: [rule_ids]` |
| **Q8b** | Operator supplies **`case_scope`** (JSON map in `policy_case_source.json` or CLI) pinning discriminators to literals **already used in IR** | Same engine for any domain; not hardcoded fields |
| **Q8c** | Treat absent discriminator as **incompatible** for the whole case | Harshest; conflates “silent on context” with “failed obligation” |

**v1 default: Q8a + Q8b optional.** Phase-1 extract attempts to ground all **grounded-tier** discriminators from any source type. If still `not_found`, strict does not invent context unless `case_scope` is provided. **No** `PIVOT_CASE_ASSUME_BACKEND_ENGINEER`-style env vars.

**Not in scope:** assuming every run is “for” one named policy title; requiring CV sections; recruitment ontology.

---

## 9. Suggested default answers (if you want to move fast)

| ID | Proposed default |
|----|------------------|
| Q1 | (b) `result_variable` + bool vars only in consequents not in evidence atoms |
| Q2 | (a) Python k-of-n on clause atoms for strict_eval; Z3 probe fallback for complex lowered shapes |
| Q3 | `strict_eval` default; `z3_witness` alias kept one release |
| Q4 | Short-circuit incompatible with explanation “stated facts contradict policy” |
| Q5 | Report `strict_incompatible_lenient_compatible` flag, no hard fail |
| Q6 | Keep `compatible`; add `coverage.warnings` for high unknown rate |
| Q7 | (A) literal IntVal in `z3_compile` + harvest in `variable_catalog` |
| Q8 | **Q8a + Q8b:** CWA when discriminator not in source; optional generic `case_scope` map in source envelope / CLI to pin trigger literals (harvested from IR, not domain-coded) |

---

## 10. File touch list (estimate)

| File | Change |
|------|--------|
| `external_tester/variable_tiers.py` | Tier algorithm |
| `external_tester/derive_eval.py` | **new** strict derive |
| `external_tester/world_builder.py` | Wire strict_eval |
| `external_tester/policy_query.py` | Strict assembly only |
| `external_tester/world_to_z3.py` | Optional activation pins (if Q7=C) |
| `z3_compile.py` | Literal encoding (if Q7=A) |
| `external_tester/variable_catalog.py` | Literal harvest for fill prompts |
| `tests/test_external_tester.py` | Tier, strict_eval, encoding, cv2 fixture |
| `tests/test_policy_query_strict.py` | **new** optional |
| `prompts/external_world_extract_phase1.md` | Grounded catalog wording |
| Docs §6 | |

---

## 11. Rollout

1. **Defaults locked:** §9 (Q8 = Q8a + optional `case_scope`).
2. Implement Steps 1 → 3 → 2 → 4 (encoding before strict_eval if scoped rules depend on it).
3. Regression: one weak + one strong external source against one policy work-dir (fixture paths in tests, not engine branches).
4. Re-run template suite where worlds pin scoped discriminators using canonical literals from IR harvest.
