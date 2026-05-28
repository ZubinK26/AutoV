# Improved scope (time) — Pivot templates + temporal surrogates (for NL policy authoring)

**Purpose:** This document defines **every rule template**, the **total logical expressivity** of the pivot stack, and **eight temporal surrogate patterns (T1–T8)** for the **`temporal-version`** branch on PML. Use it when writing or rewriting **natural-language (NL) policies** so lines are encodable—including **process order**, **prerequisites**, and **phases**—using only the **sixteen** existing `template_class` values.

**Branch scope:** **`temporal-version`** = **`16-template-version`** plus injected temporal prompts (`temporal_surrogates_addendum.md`). **No new templates**; “temporal” means **named snapshot variables** (flags, order ints, phase enums), not LTL or event logs.

**Companion:** [`improved-scope.md`](improved-scope.md) is the same sixteen-template catalog **without** the temporal authoring track (for **`16-template-version`** only).

**Audience:** Humans and AI agents (scope rewriter, WFM, extract). Write **one clear English rule per line**. Extraction maps each line to exactly one `template_class`.

---

## How the template system fits together

| Layer | Count | Role |
|-------|-------|------|
| **Core templates** | 8 | What Z3 and `meta_scheme.json` actually compile. Always valid. |
| **Expansion (vNext) templates** | 8 | Optional **sugar** in `rules_extracted.json`. Automatically **lowered** to core templates before compile. |
| **Total authors may target** | **16** | Pick **one** template per NL line. |

**Pipeline flow (simplified):**

1. NL policy (one obligation per line, after WFM / scope rewrite).
2. Extract → `rules_extracted.json` (may contain expansion templates).
3. **Lowering** → only core eight remain for compile.
4. Meta-scheme + Z3 + synthetic English.

**Two views (important for reviewers, not for NL authors):**

- **Compile view** — lowered core IR (what Z3 sees).
- **Assessment view** — original expansion shape preserved for tester / critic (easier to match NL for `K_OF_N`, multi-term sums, tables).

Policies that use expansion templates should declare **`policy_semantics_version`: `"1.1"`** and **`pivot_ir_extensions`: `["vnext_8"]`** in the rules file (the pipeline adds this automatically on extract).

---

# Total logical expressivity (what this branch can express)

This section is the **full logical boundary** for policy authoring on **`temporal-version`**: everything in **`16-template-version`**, plus **how process-order English maps into the same sixteen templates**. Per-template detail is in Parts A–B; temporal patterns in **Part G**.

## Evaluation model

| Property | Meaning for authors |
|----------|-------------------|
| **Single world** | Each check is one **variable assignment** (one snapshot). There is **no** built-in time axis, event log, or “next state.” |
| **Decidable fragment** | Policies compile to **SMT-friendly** constraints (guarded linear integer arithmetic + finite Boolean structure), then **Z3 satisfiability** runs on pathways. |
| **Pathways** | Rules group into **evaluation pathways** (`applies_to`, `overrides`, `PREEMPTION`). Conditional **policy** logic is mostly **`LOGICAL_IMPLICATION`** / **`LOGICAL_IFF`** / **`ConditionExpr`** trees. |

## In scope — logical shapes you can write

All of the following must map into **one of sixteen templates** per NL line (Parts A–B). Combinations use **nesting inside conditions** or **multiple lines**, not invented template names.

| Family | What you can express | How it appears in IR |
|--------|----------------------|----------------------|
| **Ground comparisons** | Variable vs constant (`≤`, `=`, …) | `CONSTANT_RELATIONAL`, `INT_RANGE` (expansion) |
| **Variable–variable order** | Two ints comparable in the same world | `VARIABLE_RELATIONAL` |
| **Finite enumeration** | Variable ∈ finite list; switch on discriminant | `SET_INCLUSION`, `EXHAUSTIVE_SWITCH`, `BOUNDED_FORALL` |
| **Conditional obligations** | If trigger then requirement | `LOGICAL_IMPLICATION` (nested `and` / `or` / `not` / `atom` / `varcmp`) |
| **Biconditional** | Iff between two condition trees | `LOGICAL_IFF` |
| **Mutual exclusion** | Exactly one / at most one of flags | `EXCLUSIVE_CHOICE` |
| **Override earlier rules** | Bypass or force outcome of prior rule | `PREEMPTION` (single `target_rule_id` per line) |
| **Linear arithmetic** | One op per evaluation step vs limit | `ARITHMETIC_EVALUATION` (no var×var `MULTIPLY`) |
| **Weighted sums** | Σ coeff·var compared to limit (≤ **4** terms) | `SUM_THRESHOLD` |
| **Cardinality** | At least **k** of **n** conditions (n ≤ **10**) | `K_OF_N` |
| **Tabular decisions** | Rows / blocks of if-then (≤ **32** rows/cases) | `DECISION_TABLE_ROW`, `TABLE_BLOCK` |
| **Definitions** | Variable must satisfy defining condition | `DEFINED_AS` |
| **Single product bound** | One var×var comparison per rule | `varprod_cmp` inside `ConditionExpr` (integers, capped) |
| **Process order (surrogates)** | Prerequisites, step order, phases, k-of-n checks, time-like counters | **T1–T8** → same sixteen templates (Part G); **not** a separate logic |

### How “temporal” fits without a time axis

Pivot still evaluates **one world**. Phrases like “before”, “then”, and “in order” mean **constraints on that snapshot**:

- **Scalar order (T1):** `start_x` LT `start_y` → `VARIABLE_RELATIONAL`
- **Prerequisites (T2):** guard flag → obligation → `LOGICAL_IMPLICATION`
- **Step chains (T3):** “if B complete then A complete” → **n−1 lines**, **n−1** implications
- **Phases (T4, T7):** int-coded `phase` / `workflow_state` + switch or table rows
- **Exclusive stage (T5):** `EXCLUSIVE_CHOICE`
- **Verification threshold (T6):** `K_OF_N`
- **Counters (T8):** `INT_RANGE` on `retry_count`, `days_since_*`, etc.

**Do not** collapse “A then B then C” into one vague line — split into named booleans or phase ints (Part G).

**Nesting:** Boolean structure inside triggers and requirements uses **`ConditionExpr`** with max depth **8**; `and` / `or` need **at least two** children.

**Routing:** `rule_id` / `applies_to` / `overrides` group pathways; they are **not** a substitute for step-completion flags.

## Out of scope — outside this branch’s logical expressivity

Do **not** write NL that requires constructs below; extract should **ABORT** or scope-rewrite must reframe (see Part E).

| Outside expressivity | Examples |
|----------------------|----------|
| **New template names** | “decision_rule”, “policy_block”, invented `template_class` strings |
| **Unbounded quantification** | “for every customer”, infinite domains |
| **Non-linear / unconstrained math** | General polynomials, division by variables, unconstrained reals |
| **Multiple products per rule** | More than one `varprod_cmp` or var×var in `MULTIPLY` |
| **Oversized finite structures** | k-of-n with n > 10; sum with 5+ terms; tables/switches > 32 rows/cases |
| **True temporal logics** | LTL/CTL (“eventually”, “always”, “until”), event logs, multi-step simulation |
| **Unnamed sequence blobs** | One line “events a, b, c in order” with **no** `step_*_complete` or `phase` variables |
| **Calendar without int model** | “within 30 days” without `days_since_event` integer |

## Practical summary for generators

- **One English line → one `template_class`.**
- Prefer **expansion** templates when English matches (range, k-of-n, table, switch, sum).
- For **process / order** prose, apply **T1–T8** (Part G) — same sixteen templates, extra line splits.
- Stay inside **finite** lists, **linear** arithmetic, and **explicit** variable names.

---

## Shared rule envelope (every template)

Every rule, core or expansion, includes:

| Field | Meaning |
|--------|---------|
| **`rule_id`** | Stable id: `R0001`, `R0002`, … (often assigned by pipeline). |
| **`applies_to`** | `"GLOBAL"` or another rule’s id — controls pathway grouping. |
| **`overrides`** | `null` or a rule id this rule replaces in the pathway graph. |
| **`template_class`** | Exactly one of the sixteen names below (spelled with UPPERCASE and underscores). |

**Conditional logic** inside implications uses nested **`ConditionExpr`**: `atom`, `varcmp`, `varprod_cmp`, `and`, `or`, `not` (max depth **8**). AND/OR need **at least two** children.

---

# Part A — Core eight templates (compile target)

These are the **fundamental** shapes. If no expansion template fits, use these.

### 1. `CONSTANT_RELATIONAL`

**Meaning:** One integer (or comparable scalar) variable compared to a **fixed constant**, with an outcome when the comparison holds.

**Typical NL:**

- “Score must be at most 100.”
- “Age shall not equal 0.”

**Lowers to:** *(unchanged — already core)*

**When to use:** Single variable bound to a number. Prefer **`INT_RANGE`** (expansion) when the NL says an **inclusive range** `[lo, hi]` on one variable.

---

### 2. `SET_INCLUSION`

**Meaning:** A variable must be **in** or **not in** a **finite list** of allowed values.

**Typical NL:**

- “Region must be one of: US, EU, UK.”
- “Status must not be in {blocked, deleted}.”

**Lowers to:** *(unchanged)*

---

### 3. `VARIABLE_RELATIONAL`

**Meaning:** Compare **two variables** to each other (not to a constant).

**Typical NL:**

- “Start date must be before end date.”
- “Allocated budget must be greater than or equal to spent budget.”

**Lowers to:** *(unchanged)*

---

### 4. `ARITHMETIC_EVALUATION`

**Meaning:** One arithmetic step on a variable, then compare to a limit.

- Operators: `ADD`, `SUBTRACT`, `MULTIPLY`, `DIVIDE`.
- **Multiply:** second operand must be a **number**, not another variable.
- **Divide:** divisor must be numeric.

**Typical NL:**

- “Twice the unit count must not exceed 50.” (one var × coeff compared to limit)

**Lowers to:** *(unchanged)*

**When to use:** **One** linear term vs a bound. For **sum of several weighted terms** (2·A + 3·B ≤ L), prefer expansion **`SUM_THRESHOLD`**.

---

### 5. `LOGICAL_IMPLICATION`

**Meaning:** **If** trigger **then** required — the workhorse for conditional obligations.

**Typical NL:**

- “If the request is high risk, then human approval must be required.”
- “When account type is premium, service tier must be at least 2.”

**Lowers to:** *(unchanged)*

**When to use:** Most if-then policies. Nested AND/OR/NOT live **inside** trigger and required. For **k-of-n** (“at least 3 of these 5 conditions”), prefer **`K_OF_N`** instead of a huge manual OR-of-ANDs tree.

---

### 6. `PREEMPTION`

**Meaning:** When a guard holds, **override** an **earlier** rule: force it satisfied/unsatisfied, or bypass it.

**Typical NL:**

- “If emergency flag is set, bypass the normal spending cap rule.”

**Fields:** `preempting_condition`, `action` (`BYPASS_RULE` | `FORCE_SATISFIED` | `FORCE_UNSATISFIED`), `target_rule_id` (single earlier rule id).

**Lowers to:** *(unchanged)*

**Note:** To bypass **multiple** earlier rules under the same guard, write **several** `PREEMPTION` lines (one target each), not one line with a list of targets.

---

### 7. `EXCLUSIVE_CHOICE`

**Meaning:** Among listed variables, **exactly one** or **at most one** may be “active” (boolean-style flags).

**Typical NL:**

- “Exactly one of standard, expedited, or overnight shipping mode must be selected.”

**Lowers to:** *(unchanged)*

---

### 8. `LOGICAL_IFF`

**Meaning:** Left and right conditions are **equivalent** (if and only if).

**Typical NL:**

- “Approval is required if and only if amount exceeds the threshold.”

**Lowers to:** *(unchanged)*

---

# Part B — Expansion eight templates (vNext, optional)

Use these when the **English line** clearly matches the pattern and **caps** below. They make policies easier to read and extract; the engine still compiles **core** IR underneath.

**Caps summary:**

| Template | Limit |
|----------|--------|
| `TABLE_BLOCK` | ≤ 32 rows |
| `BOUNDED_FORALL` | ≤ 32 domain values |
| `K_OF_N` | 1 ≤ k ≤ n, **n ≤ 10** clauses |
| `EXHAUSTIVE_SWITCH` | ≤ 32 cases |
| `SUM_THRESHOLD` | **1–4** terms (never 5+ on one line) |
| `DEFINED_AS` | Acyclic; condition depth ≤ 8 |

---

### 9. `INT_RANGE`

**Meaning:** One integer variable must lie in an **inclusive** range `[lo, hi]`.

**Typical NL (encourage this phrasing):**

- “Variable `score` must be between 1 and 100 inclusive.”
- “Retry count must be from 0 to 5.”

**Lowers to:**

- If `lo == hi`: one **`CONSTANT_RELATIONAL`** (`EQ`).
- Else: two **`CONSTANT_RELATIONAL`** rules — `GTE` lo and `LTE` hi (helper ids like `R0001__gte`, `R0001__lte`).

**Prefer over:** Two separate “must be ≥ lo” / “must be ≤ hi” lines unless you want them as separate policy statements.

---

### 10. `DECISION_TABLE_ROW`

**Meaning:** A **single** decision-table row: if trigger, then requirement.

**Typical NL:**

- “If customer tier is gold, then discount percent must be at least 10.”

**Lowers to:** One **`LOGICAL_IMPLICATION`** (same `rule_id` as the row).

**Prefer over:** A generic if-then line when you want to signal **tabular** intent; use **`TABLE_BLOCK`** when multiple rows share one table.

---

### 11. `TABLE_BLOCK`

**Meaning:** Several decision rows grouped under one `table_id`, shared routing (`applies_to` / `overrides`).

**Typical NL (write as one logical table, one line per row still OK):**

- Table “Pricing”: row 1 — if quantity > 100 then apply bulk flag; row 2 — if region is EU then apply VAT flag.

**Lowers to:** One **`LOGICAL_IMPLICATION`** per row, with deterministic ids (`R0003__T1_r00`, …).

**Prefer over:** Many unrelated rule ids with no table grouping when the NL is clearly one table.

---

### 12. `BOUNDED_FORALL`

**Meaning:** For **each** value in a **finite** domain, some condition must hold (instantiated per value).

**Typical NL (encourage finite lists):**

- “For each role in {analyst, reviewer, approver}, that role must satisfy the clearance check.”
- “For every status code in [1, 2, 3], the corresponding flag must be set.”

**Lowers to:** One **`LOGICAL_IMPLICATION`** per domain value (trigger fixes the iter variable to that value).

**Not in scope:** “For all users in the company” without a finite list — **ABORT** or rewrite to a finite enumeration.

---

### 13. `K_OF_N`

**Meaning:** **At least k** of **n** conditions must hold (cardinality / voting threshold).

**Typical NL (strong candidate for expansion):**

- “At least 3 of the following must be true: income verified, identity verified, address verified, employment verified, credit check passed.”
- “Two out of three risk signals must fire before escalation.”

**Lowers to:** One **`LOGICAL_IMPLICATION`** whose required side is a large OR-of-ANDs (DNF unfold). Correct for Z3; hard to read in compile view — assessment view keeps the readable `K_OF_N` block.

**Caps:** **n ≤ 10** clauses; **1 ≤ k ≤ n**.

**Prefer over:** Manually writing disjunctive normal form in nested AND/OR unless n is tiny (≤ 3).

---

### 14. `EXHAUSTIVE_SWITCH`

**Meaning:** Switch on a **discriminant** variable; each case value implies a consequence; optional default when no case matches.

**Typical NL:**

- “Switch on deployment mode: when ON then monitoring is active; when OFF then monitoring is inactive; otherwise monitoring is inactive.”

**Lowers to:**

- **`SET_INCLUSION`** for coverage of case values (when needed).
- One **`LOGICAL_IMPLICATION`** per case (trigger = discriminant equals case value).
- Optional default row: trigger = discriminant **not** in any case value.

**Note:** Need **at least two** cases (or use default + cases) so OR-coverage is valid.

**Prefer over:** Unrelated if-then lines that are clearly one enum switch.

---

### 15. `DEFINED_AS`

**Meaning:** A variable is **defined** by a condition it must satisfy (definitional constraint).

**Typical NL:**

- “Variable `eligible_threshold` is defined as: must be at least 5.”
- “The effective limit is defined as the maximum of the base limit and the floor.” *(only if encodable as a single condition in v1)*

**Lowers to:** One **`LOGICAL_IMPLICATION`** (tautology-style trigger + definition as required).

---

### 16. `SUM_THRESHOLD`

**Meaning:** A **weighted sum** of variables compared to a limit (linear inequality).

**Typical NL (encourage explicit sum phrasing):**

- “Twice the unit count plus three times the hour count must be at most 120.”
- “The sum of base fee and surcharge must not exceed the cap of 1000.”

**Fields:** `terms[]` as `{ coeff, variable }`, `relational_operator`, `limit`, `yields`.

**Caps:** **At most 4 terms** per rule. More than four summands → split into **another NL line** or simplify.

**Lowers to:**

- **1 term:** one **`CONSTANT_RELATIONAL`** or one **`ARITHMETIC_EVALUATION`** (if coeff ≠ 1).
- **2–4 terms:** chain of **`ARITHMETIC_EVALUATION`** helper rules (accumulator variables) + final **`CONSTANT_RELATIONAL`** on the sum vs limit.

**Prefer over:** Several separate arithmetic rules that do **not** express a single sum constraint.

---

# Part C — Lowering map (expansion → core)

Quick reference for what the compiler ends up with:

| Expansion template | Becomes (core) |
|--------------------|----------------|
| `INT_RANGE` | `CONSTANT_RELATIONAL` (1–2 rules) |
| `DECISION_TABLE_ROW` | `LOGICAL_IMPLICATION` (1) |
| `TABLE_BLOCK` | `LOGICAL_IMPLICATION` (one per row) |
| `BOUNDED_FORALL` | `LOGICAL_IMPLICATION` (one per domain value) |
| `K_OF_N` | `LOGICAL_IMPLICATION` (1, large condition) |
| `EXHAUSTIVE_SWITCH` | `SET_INCLUSION` + `LOGICAL_IMPLICATION` per case (+ default) |
| `DEFINED_AS` | `LOGICAL_IMPLICATION` (1) |
| `SUM_THRESHOLD` | `ARITHMETIC_EVALUATION` chain + `CONSTANT_RELATIONAL` (1–4 terms) |

Core templates **never** lower further — they are the floor.

---

# Part D — NL authoring guide (encourage expansion where it fits)

When rewriting or drafting policy lines:

1. **One line, one rule** — do not combine unrelated obligations.
2. **Name variables** in `snake_case` consistently (they become IR slugs).
3. **Prefer expansion templates** when the English pattern matches (table, k-of-n, finite forall, switch, sum, range).
4. **State finite sets explicitly** — lists, ranges, and enumerations (not “all employees”).
5. **Split** policies that need more than **4 sum terms**, more than **10** k-of-n clauses, or more than **32** table rows / switch cases.
6. **Preemption:** one bypass target per line; duplicate the line for multiple targets.
7. **Products of two variables** (e.g. budget × risk): one product per rule, both factors visible in the **if** part when possible (`varprod_cmp` rules).

**Phrases that signal expansion templates:**

| If the policy says… | Lean toward template |
|---------------------|----------------------|
| “between X and Y inclusive” | `INT_RANGE` |
| “at least k of the following” | `K_OF_N` |
| “for each X in {…}” | `BOUNDED_FORALL` |
| “switch on / case when / depending on mode” | `EXHAUSTIVE_SWITCH` |
| “table row: if … then …” (many rows) | `TABLE_BLOCK` |
| “2×A + 3×B ≤ L” / “weighted sum” | `SUM_THRESHOLD` |
| “is defined as” | `DEFINED_AS` |
| ordinary if-then | `LOGICAL_IMPLICATION` |
| “before” / rank order on named ints | T1 → `VARIABLE_RELATIONAL` |
| “only if” / prerequisite | T2 → `LOGICAL_IMPLICATION` |
| “A then B then C” (sequence) | T3 → **multiple** `LOGICAL_IMPLICATION` lines |
| workflow phase / stage | T4 / T7 → `EXHAUSTIVE_SWITCH`, `TABLE_BLOCK`, … |
| exactly one active mode | T5 → `EXCLUSIVE_CHOICE` |
| at least k verifications | T6 → `K_OF_N` |
| retry / days counter bound | T8 → `INT_RANGE` |

---

# Part G — Temporal surrogates (T1–T8, in scope)

Pivot has **no time axis** — only **one-world** constraints. Patterns below use **existing** templates only (no new `template_class`).

| ID | Intent | Preferred NL | Templates | Lines |
|----|--------|--------------|-----------|-------|
| **T1** | Scalar ordering | `start_x` must be before `start_y` | `VARIABLE_RELATIONAL` | 1 |
| **T2** | Prerequisite gating | B only if A / guard flag | `LOGICAL_IMPLICATION` | 1–2 |
| **T3** | Total order on steps | If B complete then A complete; … | `LOGICAL_IMPLICATION` × (n−1) | **n−1** lines |
| **T4** | Finite phase enum | `phase` in {1,2,3} + per-phase rules | `SET_INCLUSION`, `INT_RANGE`, `EXHAUSTIVE_SWITCH` | 2+ |
| **T5** | One active mode | Exactly one of draft/review/published | `EXCLUSIVE_CHOICE` | 1 |
| **T6** | At least k of n checks | At least 3 of: … verified … | `K_OF_N` (n≤10) | 1 |
| **T7** | Phase-dependent table | When state PENDING, … | `TABLE_BLOCK` / row implications | 1+ |
| **T8** | Counter bounds | retry_count between 0 and 5 | `INT_RANGE` | 1 |

**Authoring rules:**

- Use `snake_case` flags: `step_a_complete`, `identity_verified`, `refund_may_be_issued`.
- Use int-coded `phase` / `workflow_state` (not unbounded status strings).
- **Split T3** — never one line “a, b, c in order” without flags.
- vNext in T4, T6, T7, T8 → **`policy_semantics_version` 1.1** + `pivot_ir_extensions: ["vnext_8"]`.

**Scope rewriter:** Tag `temporal_or_process_order` lines but **rewrite to surrogates**; optional sidecar `temporal_surrogate_applied: [{ "line_index", "pattern_id": "T1"|…|"T8" }]`.

**Prompt cookbook:** [`NagV/pivot_pipeline/prompts/temporal_surrogates_addendum.md`](NagV/pivot_pipeline/prompts/temporal_surrogates_addendum.md) · **Examples:** [`NagV/pivot_pipeline/prompts/temporal_surrogates_examples.md`](NagV/pivot_pipeline/prompts/temporal_surrogates_examples.md)

---

# Part E — Out of scope (do not write NL that requires these)

Extract / rewrite should **ABORT** or push scope rewrite unless the line is reframed:

- New invented template names (“decision_rule”, “policy_block”, …).
- Unbounded quantification (“for every customer”, infinite domains).
- More than **one** variable×variable product per rule (use a single `varprod_cmp` or rewrite).
- Variable × variable in **`ARITHMETIC_EVALUATION` MULTIPLY**.
- More than **4** terms in one sum rule.
- More than **10** clauses in one k-of-n rule.
- Non-linear arithmetic, unconstrained strings, or **LTL/CTL / event logs** (T1–T8 surrogates are **in scope**; true temporal logics are not).

---

# Part F — Related project docs

| Doc | Content |
|-----|---------|
| [`improved-scope.md`](improved-scope.md) | Sixteen-template catalog without temporal track (`16-template-version`) |
| [`NagV/pivot_pipeline/PIVOT_TEMPLATE_SYSTEM.md`](NagV/pivot_pipeline/PIVOT_TEMPLATE_SYSTEM.md) | Full technical reference + examples |
| [`NagV/pivot_pipeline/prompts/v1_policy_encodability_contract.md`](NagV/pivot_pipeline/prompts/v1_policy_encodability_contract.md) | Normative limits for WFM / extract |
| [`NagV/pivot_pipeline/prompts/extractor_vnext_addendum.md`](NagV/pivot_pipeline/prompts/extractor_vnext_addendum.md) | Extractor hints for vNext |
| [`NagV/pivot_pipeline/prompts/temporal_surrogates_addendum.md`](NagV/pivot_pipeline/prompts/temporal_surrogates_addendum.md) | Injected T1–T8 cookbook |
| [`dev_plans/dev_plan_temporal_surrogates_v1.md`](dev_plans/dev_plan_temporal_surrogates_v1.md) | Temporal implementation plan |
| [`dev_plans/VNEXT_OPERATOR_REMINDERS.md`](dev_plans/VNEXT_OPERATOR_REMINDERS.md) | Operator checklist |

---

*This file is the **scope-oriented** catalog for **`temporal-version`** NL authoring: total logical expressivity + sixteen templates + T1–T8 temporal surrogates. Lowering: `vnext_lowering.py`.*
