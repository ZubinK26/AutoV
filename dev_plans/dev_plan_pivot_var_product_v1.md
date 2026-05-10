# Dev plan: variable × variable product in pivot IR (v1)

## Contract (agreed restrictions)

All eight items below are in scope; **point 6** is spelled out explicitly.

1. **Sorts** — Only **integer** variables may appear as factors in a product (aligned with normalized nonnegative-integer semantics for v1).

2. **Sign** — Factors are **nonnegative integers** (`v ≥ 0`) unless a later pass introduces stricter per-field lower bounds.

3. **Global hard cap** — Any variable that may appear in a product is subject to **`0 ≤ v ≤ G`** with **`G = 1_000_000` (`10^6`)**, enforced in the **compiler / Z3 encoding** (not LLM-chosen). Optional: **`PIVOT_PRODUCT_INT_CAP`** (or reuse a single `PIVOT_INT_VAR_CAP`) env override with safe clamping in code.

4. **Product shape** — **At most one binary product in the entire rule**: `v1 * v2`, with **no** nested multiplication (`(a*b)*c`), and **no** sums of products (`a*b + c*d`) in v1.

5. **Relational leaf** — The product appears only as **one relational comparison**: **`v1 * v2` ⊴ `rhs`**, where **`⊴` ∈ RelationalOperator** (`EQ`, `NEQ`, `LT`, `LTE`, `GT`, `GTE`) and **`rhs`** is either **another variable** or a **numeric constant**.

6. **Boolean context (explicit)** — The comparison in (5) is a **single leaf** in **`ConditionExpr`**, exactly like **`atom`** / **`varcmp`** today. That leaf may be wrapped by existing **`and` / `or` / `not`**, subject to **`CONDITION_EXPR_MAX_DEPTH`** (currently **8**). So: **relational** at the leaf, **propositional** nesting above it—no conflict between “boolean” and “≤, ==, …”.

7. **Backward compatibility** — **Optional** extension: add a **new discriminant** on **`ConditionExpr`** (recommended) *or* a narrowly scoped new rule template if extract must express a top-level obligation without `LOGICAL_IMPLICATION`. Existing JSON and code paths **unchanged** when the new shape is absent.

8. **Semantics deferred** — v1 assumes factors are **already normalized**; **no** units, rounding, or divisibility model (precheck / critic handle weak signals only).

---

## IR design

### Recommended: new `ConditionExpr` variant

Add a sibling to `atom` / `varcmp`, e.g.:

- **`kind`:** `"varprod_cmp"` (name TBD; keep short in JSON).
- **`left_variable`**, **`right_variable`** — factor names (must be `int` in `variable_sorts` after registry).
- **`operator`** — `RelationalOperator`.
- **`rhs`** — discriminated or tagged union: **either** `{ "kind": "var", "variable": "..." }` **or** `{ "kind": "const", "value": <int> }` (forbid `bool`/string for v1 unless you extend sorts later).

**Depth:** `condition_depth` treats `varprod_cmp` as a **leaf** (base + 1), same as `atom` / `varcmp`.

**Per-rule validation** — detailed in **§ Compliance validation (mandatory)** below (single canonical place for rules).

### Optional: top-level rule template

If extract/WFM need **“obligation”** without an implication wrapper, add e.g. **`VARIABLE_PRODUCT_RELATIONAL`** mirroring **`VARIABLE_RELATIONAL`** but with two factors and `rhs`. Only add if needed; otherwise `LOGICAL_IMPLICATION` with tautological trigger is a stopgap **not** recommended.

If this optional template is added, **every field** it introduces (`left_variable`, `right_variable`, `rhs`, etc.) must be covered by the **same** compliance checks as `varprod_cmp` (sorts, caps, one-product-per-rule at rule level, no duplicate encoding).

---

## Compliance validation (mandatory)

Whenever **`varprod_cmp`** (or the optional top-level product rule template) is **present** in the ruleset, the pipeline must **fail closed** with a **clear, stable error message** if any check below fails. Do **not** rely on the LLM or Z3 alone.

### When validation runs

| Stage | Purpose |
|--------|---------|
| **IR parse / `model_validate`** | JSON shape, types, `rhs` XOR (var vs const), `operator` ∈ `RelationalOperator`, leaf fields non-empty, no unknown `kind`. |
| **`load_rules_and_compile` (pre–`build_meta_scheme`)** | **Full contract** on the parsed `AtomicRule` list: counts, sorts, forbidden pairings, depth. **Always run** this pass (cheap tree walk); branching on “any varprod present” is optional for perf only. |
| **After `registry_pass_from_nl_and_rules`** | Re-run **sort / name** checks if validation depends on canonical slugs or filled `variable_sorts` (see below). |
| **Repairer / extract rewrite output** | Same gate as extract JSON before compile—**no** path may skip it. |
| **Z3 encode (defensive)** | If a `varprod_cmp` reaches `encode_condition` without prior validation, **assert** or raise (implementation choice); prefer catching errors earlier. |

### Checklist (maps to contract §1–§8)

| # | Contract | Validator behavior |
|---|----------|-------------------|
| **1** | Int factors only | For each `varprod_cmp`, **`left_variable`** and **`right_variable`** must appear in **`variable_sorts`** with value **`"int"`**. If `rhs` is variable mode, **`rhs.variable`** must also be **`"int"`**. **Reject** if sort missing or **`"bool"`** (strings/enums not allowed as factors or numeric rhs in v1). |
| **2** | Nonnegative factors | **No separate NL check.** Enforcement = **Z3 bounds** `0 ≤ v` for every int var participating in a product (factors + int rhs when var). Validation stage should **record** that these vars are in the “product-bounded” set so encode cannot skip bounds. |
| **3** | Global hard cap **G** | All vars in the product-bounded set must get **`0 ≤ v ≤ G`** in Z3. **Parse-time:** optional **sanity** on `rhs` **constant**: reject if not an **integer** or if absurdly out of engineered range (recommend: allow any int constant for comparisons like `<= 1000`, but **clamp env `G`** only for **variables**; document that literal rhs may be smaller than `G` and that **`a*b` max magnitude is `G²`**). If team wants stricter literals, add **`|const| ≤ G*G`** or policy-specific cap—spell out in implementation. |
| **4** | One binary product per rule | For **each** `AtomicRule`, depth-first walk **all** embedded `ConditionExpr` fields (`trigger_condition`, `required_condition`, `preempting_condition`, `left`, `right`, nested `and`/`or`/`not`). Count **`varprod_cmp`** nodes. **Require `count ≤ 1`**. **Reject** if **>1**. **Reject** duplicate product encoding: same rule must **not** combine `varprod_cmp` with **`ARITHMETIC_EVALUATION` + `MULTIPLY` + variable `operand_2`** (keep v1 **single** sanctioned var×var encoding). |
| **5** | Single relational leaf | Enforced by **schema**: only `left_variable`, `right_variable`, `operator`, `rhs`—**no** child `ConditionExpr` inside the product leaf; no nested multiply. |
| **6** | Boolean context / depth | Run existing **`condition_depth`** on every `ConditionExpr` subtree **after** union includes `varprod_cmp` (leaf depth +1). **Reject** if **> `CONDITION_EXPR_MAX_DEPTH`**. |
| **7** | Backward compatibility | **Purely legacy rulesets unchanged in behavior.** The validator **may always run** (recommended); for rules with **no** `varprod_cmp` (and no optional product template), product-specific checks are **vacuous** (e.g. count = 0). **Reject** only when a rule **uses** the new encoding and violates contract. Same for optional **`VARIABLE_PRODUCT_RELATIONAL`** if added—treat as “product present” for that rule. |
| **8** | Semantics deferred | **No** validator for units/rounding; optional **lint**: rhs const must be **integral** type (not float) in v1 to match “normalized int” story—**reject** float literals in `varprod_cmp.rhs` if pydantic allows. |

### Additional structural lint (recommended)

- **Distinct slug names:** Optionally **warn** or **allow** `left_variable == right_variable` (squaring); if allowed, document. Recommend **allow** (e.g. `area` conceptual).  
- **Empty / whitespace variable names:** Reject via existing string validation.  
- **Reserved rule ids / pathway refs:** No change unless pathway walk assumes condition shape—grep and extend.

### Error surface

- Prefer **one** module, e.g. **`validate_var_product_rules(rules, variable_sorts) -> None`**, raising **`ValueError`** (or project-specific `ExtractValidationError`) with messages like:  
  `R0004: at most one varprod_cmp per rule (found 2)`  
  `R0004: varprod_cmp factor 'cost' has sort 'bool', expected 'int'`  
  `R0004: variable×variable MULTIPLY must use kind 'varprod_cmp', not ARITHMETIC_EVALUATION`

### Tests (extend § Tests)

- Each **rejection** above gets at least **one** negative test fixture (parse/compile fails with expected substring).  
- Positive: **single** `varprod_cmp` under `and`/`or`, int sorts, compiles.  
- Registry: remap then validate (sorts still int post-alias).

---

## Z3 encoding (`z3_compile.py`)

1. **Bounds** — For every variable referenced as a factor or as `rhs` when `rhs` is a variable, assert **`0 ≤ x ≤ G`** (reuse shared helper; avoid duplicate constraints if already implied—Z3 tolerates duplicates or use a `bounded_int_vars` set).

2. **Product atom** — Encode **`left * right` ⊴ `rhs_expr`** with `Int` variables; use standard relational Z3 ops. **Nonnegative factors** should be **asserted** (or implied by bounds from 0).

3. **`encode_condition`** — Dispatch on `kind == "varprod_cmp"` alongside `atom` / `varcmp` / `and` / `or` / `not`.

4. **Tests** — Sat model where product constraint is binding; unsat when violated; **unknown** regression smoke on pathological cases optional.

---

## Pathway / policy shell (`pathway_compiler.py`, etc.)

- Ensure **pathway compilation** and **PREEMPTION / must_satisfy_all** logic **does not** assume conditions are only `atom`/`varcmp`. Any walker that collects rule IDs or flattens conditions must **descend** into the new `kind` (usually generic `ConditionExpr` recursion already does; **verify**).

---

## Registry (`registry_pass.py`)

- Extend **`collect_used_slugs`** / **`walk`** / **`apply_registry_to_rules`** to remap **`left_variable`**, **`right_variable`**, and **`rhs.variable`** for `varprod_cmp`.

---

## Extract / WFM / repairer

- **Extract JSON validation** — Pydantic validates shape; **§ Compliance validation** is the source of truth for semantic/rule constraints (do not assume Pydantic alone is enough).
- **Prompts** — `v1_policy_encodability_contract.md` (and WFM extract scope if needed): document **`varprod_cmp`**, caps, “one per rule,” nonnegative int story.
- **Repairer prompts** — Structural/semantic repair must **recognize** the new kind and **not** strip it.

---

## Deterministic artifacts

- **`backtranslate.py` / `synthetic_en.md`** — Today’s markdown is rule-list–centric; if critic relies on `synthetic_en.md`, add a short human-readable line per rule that uses `varprod_cmp`, or extend rendering to dump condition structure (minimal: “rule X uses var×var comparison”).
- **`precheck.py`** — Optionally extend **numeric heuristic** to include **constants** appearing in `varprod_cmp` rhs (low priority).

---

## Tests (minimum)

| Area | Cases |
|------|--------|
| **IR parse** | Valid / invalid (two `varprod_cmp` in one rule → reject). |
| **Compliance** | See **§ Compliance validation**: sort mismatches, `varprod_cmp` + forbidden `ARITHMETIC_MULT`, bad `rhs`, depth overflow. |
| **`condition_depth`** | `not (and atom varprod)` within cap. |
| **Z3** | Sat with `a*b <= K`; unsat counterprop; bounded model. |
| **Registry** | Slug remap on factor + rhs var. |
| **Golden extract** | Optional: one fixture JSON round-trip through `load_rules_and_compile`. |

---

## Rollout

**Rollout** here means the **order of implementation/enablement**: what lands in the repo first vs later, so dependencies (e.g. validation before LLM emission) stay safe.

1. Land **IR + Z3 + tests** behind no extract emission (construct only in tests).
2. Land **`validate_var_product_rules`** (or equivalent) and wire it into **`load_rules_and_compile` / extract / repairer** **before** prompts invite the LLM to emit `varprod_cmp` (safety gate first, then open emission).
3. Update **registry walk** + **pathway** sweep (grep for `kind ==` / `ConditionExpr` switches).
4. Ship **prompt / contract** updates so LLM may emit the shape.
5. Monitor Z3 **time / unknown**; tune **`G`** or caps via env if needed.

---

## Out of scope (v1)

- Units, rounding, division,mixed real/int.
- Multiple products per rule or polynomial constraints.
- Relaxing **`ARITHMETIC_EVALUATION`** `MULTIPLY` guard for var×var **without** the new `ConditionExpr` leaf (prefer **one** sanctioned encoding).

---

## Status

**Plan ready** — v1 `varprod_cmp` implemented: IR, `validate_var_product_rules`, Z3 bounds + encode, registry walk, encodability contract + tests (`pivot_pipeline/tests/test_var_product_ir.py`).
