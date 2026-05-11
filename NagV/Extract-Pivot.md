1. The Atomic Templates (Extraction Layer)

The system maps declarative Natural Language into **eight** mutually exclusive JSON template classes for v1 (six core **plus** `EXCLUSIVE_CHOICE`, `LOGICAL_IFF`), plus two routing keys for graph compilation. `LOGICAL_IMPLICATION` uses a nested **`ConditionExpr`** (AND/OR/NOT, depth-capped). These templates strictly define state validations, bound within Decidable First-Order Logic (QF_LIA / guarded linear arithmetic per validators in §5).

Universal Routing Keys (Added to every template):



applies_to: string (Either "GLOBAL" or a specific rule_id this rule depends on).

overrides: string | null (The rule_id this rule preempts).

**Note (v1):** Formal JSON shapes for **`EXCLUSIVE_CHOICE`**, **`LOGICAL_IFF`**, and nested **`ConditionExpr`** inside **`LOGICAL_IMPLICATION`** are specified in the Pydantic IR (`§5` M1); extend numbered subsections below when schemas are frozen in-repo.

1. Constant Relational (The Boundary)

Evaluates a dynamic variable against a static constant.



JSON



{

  "template_class": "CONSTANT_RELATIONAL",

  "rule_id": "string",

  "variable": "string",

  "relational_operator": "enum ['EQ', 'NEQ', 'GT', 'LT', 'GTE', 'LTE']",

  "constant_value": "number | string | boolean",

  "yields": "enum ['SATISFIED', 'UNSATISFIED']" 

}

2. Set Inclusion (The Categorical)

Evaluates if a variable belongs to a specific predefined array.



JSON



{

  "template_class": "SET_INCLUSION",

  "rule_id": "string",

  "variable": "string",

  "inclusion_operator": "enum ['IN', 'NOT_IN']",

  "constant_array": ["string", "number"],

  "yields": "enum ['SATISFIED', 'UNSATISFIED']"

}

3. Variable Relational (The Cross-Check)

Compares two dynamic state variables directly against each other.



JSON



{

  "template_class": "VARIABLE_RELATIONAL",

  "rule_id": "string",

  "left_variable": "string",

  "relational_operator": "enum ['EQ', 'NEQ', 'GT', 'LT', 'GTE', 'LTE']",

  "right_variable": "string",

  "yields": "enum ['SATISFIED', 'UNSATISFIED']"

}

4. Arithmetic Evaluation (Linear Limits)

Performs linear math (protecting against non-linear Z3 undecidability) before evaluating a limit. Requires Python-side division-by-zero protection.



JSON



{

  "template_class": "ARITHMETIC_EVALUATION",

  "rule_id": "string",

  "operand_1": "string (variable)",

  "math_operator": "enum ['ADD', 'SUBTRACT', 'MULTIPLY', 'DIVIDE']",

  "operand_2": "number | string (variable)",

  "relational_operator": "enum ['GT', 'LT', 'GTE', 'LTE', 'EQ', 'NEQ']",

  "target_limit": "number | string (variable)",

  "yields": "enum ['SATISFIED', 'UNSATISFIED']"

}

5. Logical Implication (The Dependency)

If the trigger is true, the requirement must be true, otherwise the rule fails.



JSON



{

  "template_class": "LOGICAL_IMPLICATION",

  "rule_id": "string",

  "trigger_condition": {"variable": "string", "operator": "enum", "value": "any"},

  "required_condition": {"variable": "string", "operator": "enum", "value": "any"}

}

6. Preemption (The Short-Circuit)

Explicit commands to force a state or bypass logic, mapped during graph traversal.



JSON



{

  "template_class": "PREEMPTION",

  "rule_id": "string",

  "preempting_condition": {"variable": "string", "operator": "enum", "value": "any"},

  "action": "enum ['FORCE_SATISFIED', 'FORCE_UNSATISFIED', 'BYPASS_RULE']",

  "target_rule_id": "string (Optional)"

}

2. The Meta-Scheme (The DNF Combinator)

The Meta-Scheme is a rigid Disjunctive Normal Form (DNF) wrapper. It groups the atomic rules into evaluation pathways (OR of ANDs). It enforces a strict Closed-World Assumption.



JSON



{

  "policy_id": "string",

  "baseline_evaluation": "DEFAULT_UNSATISFIED",

  "evaluation_pathways": [

    {

      "pathway_id": "string",

      "description": "string",

      "must_satisfy_all": ["R1", "R2"], 

      "must_not_trigger": ["R3"]        

    }

  ],

  "rules": [

    // Array of the populated atomic templates

  ]

}

3. The End-to-End Pipeline

Scope Constraint: The pipeline processes stateless, flat, linear firewalls. It explicitly rejects imperative mutations, temporal loops, and non-linear arithmetic.



Phase 0: Preprocessing (External)

Action: Natural Language is processed through an existing well-formedness module.

Result: Sentences are strictly anaphora-resolved, disambiguated, and terminology-unified.

Phase 1: Atomic Extraction (LLM - Parallelized)

Action: The LLM receives sentences strictly one-by-one.

Task: Classify the sentence into one of the 6 templates, extract variables, and assign the applies_to and overrides routing keys.

Result: An unlinked array of JSON rule templates.

Phase 2: Headless DNF Compilation (Python DAG - Zero LLM)

Action: A deterministic Python script traverses the extracted rules using the routing keys.

Task:

Base pathways are formed from rules tagged applies_to: GLOBAL.

Dependent rules (applies_to: R_X) are appended to relevant pathways.

Override rules (overrides: R_Y) clone existing pathways, dropping the overridden rule and substituting the new one.

Result: The fully populated JSON Meta-Scheme.

Phase 3: Z3 Compilation (Python)

Action: Python translates the JSON Meta-Scheme into the z3-solver API.

Task: Atomic templates become boolean assertions. Pathways become z3.And() blocks. The entire policy is wrapped in a global z3.Or().

Phase 4: Isomorphic Back-Translation (Validation)

Action 1 (Python): Python deterministically translates the JSON Meta-Scheme back into rigid, synthetic English (Rule-by-Rule, then Pathway-by-Pathway).

Action 2 (LLM Critic): An LLM compares the Original NL against the Synthetic English to flag semantic drift, missing conditions, or hallucinated boundaries.

4. Policy Model Interactivity Types (Z3 Capabilities)

Once compiled into Z3, the mathematical model supports four core interaction types (state data injection omitted per instructions):



Execution (State Validation): Provide a set of variables. Z3 evaluates the DNF pathways and returns a boolean SATISFIED or UNSATISFIED.

Model Generation (Valid State Discovery): Provide constraints (or no constraints). Z3 reverse-engineers the math to output a valid combination of variables that guarantees a SATISFIED outcome.

Invariant Checking (Vulnerability Proving): Provide a hypothetical "illegal" outcome. Z3 mathematically proves if there is any possible combination of states/overrides that allows the illegal outcome to occur (UNSAT = mathematically safe).

Shadowing/Subsumption Detection (Dead Code): Z3 analyzes the ruleset against itself to detect if a rule is mathematically unreachable or redundant due to the constraints of other rules.

5. Development plan (v1 — E2E runnability)

**Goal:** One **NL ruleset file** → one **policy model** artifact (validated meta-scheme JSON + runnable Z3 module or in-process check), with **forked Phase 0 WFM** (SMT WFM **unchanged**). Any **blocking** Phase 0 failure or **out-of-scope / validation** failure **stops the pipeline** with a **clear pointer** (e.g. rule line); user **edits that line** and re-runs — no auto-skip.

**Principle:** **1 input ruleset = 1 policy model per run.** No partial promotion of a broken ruleset.

---

### 5.1 Repository layout (suggested)

- `NagV/pivot_pipeline/` (or top-level `pivot_policy/`) — Python package: IR, compiler, CLI, tests.
- `NagV/pivot_wfm/` — **Duplicate** of the **shape** of `wfm_orchestration` needed for registry e2e (or thin wrapper), **separate** prompts under `NagV/pivot_wfm/prompts/` / `templates/`. **Do not edit** `wfm_orchestration/` assets used by SMT except where a shared **library** is intentionally reused read-only.
- `NagV/prompts/pivot_*.md` — Phase 1 extraction, Phase 4 critic (or colocate under `pivot_pipeline/prompts/`).

---

### 5.2 Milestones (implement in order)

**M0 — Scaffolding & contracts**

- Add package, `pyproject` / deps: `pydantic>=2`, `z3-solver`, existing repo Gemini/WFM helpers as needed.
- Pin **`policy_semantics_version: "1.0"`** default in code; document §7 in README for pivot package only.

**M1 — Core IR (Pydantic)**

- Discriminated union for **atomic templates**: existing six **plus** `EXCLUSIVE_CHOICE`, `LOGICAL_IFF`.
- Replace flat `LOGICAL_IMPLICATION` fields with **`ConditionExpr`** (AND/OR/NOT, depth cap, leaves = relational atoms or registered refs).
- Meta-scheme models: `evaluation_pathways`, `rules[]`, `policy_id`, baseline, **semantics version**.
- Validators: divide-by-zero; **linear slash guard** for `ARITHMETIC_EVALUATION` (per prior agreement); **finite** `constant_array`; **pathway cap** constant (256); override graph **acyclicity** check.

**M2 — Phase 0: forked WFM (“pivot well-formedness”)**

- **Copy** the NagV/SMT WFM flow into **`pivot_wfm`**: orchestrator entry, handoff JSON shape, progress file — **scoped** to “self-contained sentences, pivot vocabulary, no SMT formalizer prompts.”
- New **system/user prompts** and templates: instructions that output PASS/REWRITE/BLOCK per line (or per chunk) with **line/sentence index** and **actionable rewrite** text.
- **Freeze rule:** on any **BLOCK** or irrecoverable WFM failure, write `pivot_progress.json` (or parallel structure) with **blocking line id / text**, **exit non-zero**, **do not** run Phase 1+.

**M3 — Phase 1: extraction + identifier registry**

- **1a** Structured LLM extract per line (parallel OK): templates + `applies_to` / `overrides` + entity mentions.
- **1b** Single **registry** pass: canonical variable names (LLM or deterministic clustering + one confirmation call).
- **1c** Deterministic rewrite of all rule fields to use registry.
- Validate full list → **ABORT** with readable errors (no silent drop).

**M4 — Phase 2: `PathwayCompiler`**

- Implement **exactly** §7 (override DAG, tie-break, preemption actions, pathway cloning, cap).
- Unit tests: golden small graphs → expected pathway count and membership.

**M5 — Phase 3: Z3 encoder**

- Map each template + pathway DNF to Z3 (`Bool`/`Int` sorts per variable registry sort metadata).
- Export: `run_check()` or equivalent returning status dict (align with NagV driver pattern if useful).
- Property tests: hand-made policies → expected `sat`/`unsat`.

**M6 — Phase 4: back-translation + checks + critic**

- Deterministic synthetic prose from IR.
- **Python pre-checks:** rule_id coverage, threshold set vs NL regex scan (best-effort).
- LLM critic prompt (checklist + final `[VERDICT: PASS|FAIL]` line). **FAIL** → non-zero exit + log; **no** auto-loop in v1 unless you add a bounded repair budget later.

**M7 — CLI & artifacts**

- Example: `python -m pivot_pipeline --input policy.nl --work-dir exports/pivot_runs/<id>/` (or `pivot-pipeline` console script). Optional: `--skip-phase0` + `--rules-json` for compiler/Z3 without WFM.
- Artifacts: `phase0_handoffs/`, `rules_extracted.json`, `identifier_registry.json`, `meta_scheme.json`, `policy_z3.py` (or embedded), `synthetic_en.md`, `critic_result.txt`, `run_summary.json`.
- Single **source NL path** recorded in summary.

**M8 — E2E test**

- Fixture: 5–10 line policy (linear, in-scope) → full run in CI (mock LLM optional for parser/compiler-only tests; one **smoke** with real API optional/off by default).

---

### 5.3 Definition of done (v1)

- Fresh clone + API keys: **one command** processes **one** NL ruleset through Phase 0→4 and produces a **validated** meta-scheme and **executable** Z3 check.
- Phase 0 **BLOCK** / validation error: **hard stop**, message names **which input line** to fix.
- SMT pipeline WFM: **zero** required changes for pivot to ship; pivot WFM is **separate code path**.

---

## 6. Failure-modes table (v1 — this project)

**Status:** All six rows below are **accepted** — decisions locked for v1; implementation follows §5.

| # | Failure mode | Mitigation (v1) | Status |
|---|----------------|-------------------|--------|
| 1 | Expressivity gap | Templates `EXCLUSIVE_CHOICE`, `LOGICAL_IFF`; Phase 0 + ABORT for out-of-schema NL | Accepted |
| 2 | `LOGICAL_IMPLICATION` too flat | Nested `ConditionExpr` (`AND` / `OR` / `NOT`), depth-capped, operator whitelist | Accepted |
| 3 | Wrong `applies_to` / `overrides` | Static validation (IDs exist, acyclic override graph per §7); optional coverage checks; critic can focus on routing | Accepted |
| 4 | Parallel extract / identifier drift | Phase 0 = **forked WFM** (do not modify SMT WFM). **1a** per-line extract (parallel OK) → **1b** global `identifier_registry` → **1c** deterministic rewrite of variable fields | Accepted |
| 5 | Preemption semantics ambiguity | **Single normative contract for this repo — v1 only** (§7). One reference `PathwayCompiler` + tests; **no per-project fork** of meaning. **Caveat:** a different business reading of preemption requires **`policy_semantics_version` 2+** (breaking), not ad-hoc behavior | Accepted |
| 6 | Back-translation + critic limits | See §8 — structured checklist + coverage; critic is a **gate**, not a proof | **Accepted** |

---

## 7. Preemption, overrides & pathways — **semantics v1** (AutoV pivot, normative)

**Purpose:** One implementation and one meaning for every deployment of this pipeline **at version 1.0**. Validators and `PathwayCompiler` encode **only** this. If stakeholders need different preemption law, ship **semantics 2.0** and migrate data.

**Version field:** Root meta-scheme MUST include `policy_semantics_version: "1.0"` (or omit only before launch — default `1.0` in code).

**Baseline:** `baseline_evaluation: DEFAULT_UNSATISFIED` means the policy is satisfied only if **at least one** `evaluation_pathway` evaluates to satisfied under the closed-world reading documented with pathways (unchanged from your meta-scheme intent).

**`overrides` (on atomic templates):**

- `overrides: null` — no replacement behavior.
- `overrides: "<rule_id>"` — this rule **supersedes** the named rule’s **atomic contribution** wherever both would otherwise apply in the same pathway assembly. The compiler builds a **directed graph** on rule ids from “supersedes” edges (**child** = overridden rule). **v1 requires this graph to be acyclic.** If a cycle is detected → **reject** meta-scheme at validation time.
- **Ties:** If multiple rules override the same target, **v1 tie-break:** the **superseding** rule with **lexicographically greatest `rule_id`** wins (document this; change only in v2). Implementations MUST NOT invent other tie-breaks per customer.

**`PREEMPTION` template actions (v1 Z3 intent):**

- `FORCE_SATISFIED` / `FORCE_UNSATISFIED` on `target_rule_id`: when `preempting_condition` holds, the boolean literal associated with that target rule’s satisfaction is forced **True** / **False** in the pathway context (encoder maps `rule_id` → `Bool`).
- `BYPASS_RULE`: when `preempting_condition` holds, the target rule’s constraints are **omitted** from the conjunction for that pathway branch (not forced true/false — **absent**).

**Pathway cloning:** Overrides/preemption may duplicate pathway variants. **v1 hard cap:** if compiled pathway count exceeds **256**, validation **fails** with a clear error (tunable constant in one place). Prevents combinatorial blowups silently.

**Caveat (accepted):** This is **not** “whatever legal meant in hallway conversation” — it is **exactly** what the compiler does. NL mis-encode (`overrides` wrong) is an **extraction** problem; ambiguous preemption **relative to v1** is fixed by **changing the IR** or **bumping semantics version**, not by branching code per project.

---

## 8. Item 6 — Back-translation & critic: issue, fix, cost, benefit

**What’s the issue?**

- Deterministic synthetic English is **rigid and lossy**: it can **omit** nuance, reorder ideas, or **sound** like it matches when the JSON encodes something stricter/weaker.
- An LLM critic can **false PASS** (drift missed) or **false FAIL** (pedantic disagreement), and is **non-deterministic** across runs unless temperature = 0 and prompts frozen.

**What’s the fix (v1)?**

- Treat Phase 4 as a **risk-reduction gate**, not equivalence proof.
- **Deterministic pre-checks** where possible: every `rule_id` in extraction appears in synthetic text; every Phase 0 sentence has **at least one** cited `rule_id` in the synthetic doc; constants and enumerated thresholds in NL are **regex- or set-compared** to JSON (machine check).
- **Critic prompt:** structured checklist — “list any NL clause with **no** matching rule,” “list any rule introducing a **new** threshold or entity not in NL,” verdict last line only (align with existing NagV critic pattern).
- **On FAIL:** return structured deltas for Phase 1 repair or human ABORT; **on PASS** still allow optional spot audit.

**Cost:** Extra latency and tokens; prompt + golden critic fixtures maintenance; occasional rework from false FAIL.

**Benefit:** Catches **gross** omission, hallucinated bounds, and **coverage gaps** cheaply before Z3 work is trusted for the wrong policy; complements **sound** JSON→Z3 core.

---

## 9. Operational contract — freeze on failure; one ruleset per policy model

- **Input:** A single NL ruleset file (or equivalent single document) = **one** policy model for that run.
- **Phase 0 (pivot WFM):** Any **BLOCK** or irrecoverable well-formedness failure → pipeline **stops**, **`run_summary.json`** / **`pivot_progress.json`** record **blocking line index / excerpt**, **exit code ≠ 0**. Phases 1–4 **do not run**. User **corrects that line** in the source ruleset and re-runs from scratch (or from Phase 0 resume if implemented later — v1 may be full restart).
- **Validation / out-of-scope** after Phase 0 (schema, linearity, pathway cap, override cycle, etc.) → **stop**, report **`rule_id`** or artifact path; user fixes source NL or extraction outcome by fixing input / re-run.
- **Critic FAIL (Phase 4):** For v1 this is **blocking** — the policy model is **not** marked accepted until critic **PASS** (optional spot human audit still allowed). No mandatory auto-repair loop in v1.

---
