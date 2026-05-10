# Test input 2 — template suite report walkthrough

This note explains `NagV/exports/pivot_runs_test_input2/template_run_report.json` in plain language (suite `test_input2_suite`, policy `Test_input2`).

## Big picture

The report binds the run to a **rules snapshot** (`rules_sha256`, `policy_id`, `policy_semantics_version`).

**Summary counts:**

- **passed:** Z3 ran and the outcome matched the golden expected in the suite.
- **failed:** Z3 ran but the outcome did **not** match the golden.
- **errors:** Validation or execution threw (broken instance).
- **inconclusive:** The harness could not score pass/fail against the golden (e.g. UNSAT so no model / missing decision).

For this run: **6 passed, 1 failed, 0 errors, 1 inconclusive** — eight instances (`gen_001` … `gen_008`), one per template kind.

## Test by test

### `gen_001` — `scenario` — pass

**Checks:** With this world assignment, is policy ∧ world **satisfiable**?

**Result:** Solver **SAT**; golden expected **sat** → match.

### `gen_002` — `decision_query` — pass

**Checks:** Under policy ∧ world, does the chosen rule (or bool) evaluate **satisfied** vs **unsatisfied**?

**Result:** **Satisfied**; golden expected **satisfied** → match.

### `gen_003` — `rule_attribution` — fail

**Checks:** Which rule ids are **satisfied** in the model for the chosen query?

**Actual:** Many rules satisfied in that world (long list `R0001` … `R0020`, etc.).

**Golden:** Only **`R0006`**.

**Meaning:** The **LLM-authored golden** was too narrow relative to what the formal model does in that world (wrong expected attribution), not a Z3 execution failure.

### `gen_004` — `boundary` — pass

**Checks:** Same decision across **three** values along one variable (boundary behavior).

**Result:** **satisfied / unsatisfied / unsatisfied** matched golden.

### `gen_005` — `counterfactual_flip` — inconclusive

**Checks:** Base world vs mutant world; expect a **flip** in decisions per golden.

**What happened:** **Policy ∧ base world was UNSAT**, so there is no base model and **`base_decision`** is null. Mutant side was SAT with **unsatisfied** for the query. Golden assumed base **unsatisfied** and mutant **satisfied** with flip — the harness reports **inconclusive** (“counterfactual decision unknown” on the base side).

### `gen_006` — `obligation_inventory` — pass

**Checks:** Does the **obligation** list (pathway rules that must hold) match?

**Result:** Actual list equals golden (same rule keys with empty `args`).

### `gen_007` — `sat_unsat` — pass

**Checks:** Is policy ∧ world **SAT** or **UNSAT**?

**Result:** **UNSAT**; golden expected **unsat** → match.

### `gen_008` — `pairwise` — pass

**Checks:** Two world fragments `query_a` vs `query_b` under shared `world`, same top-level `query`; compare **decision_a** vs **decision_b** (or `expect_equal`).

**Result:** **Satisfied** vs **unsatisfied** matched golden.

## How to read this for your goals

- **Passes** mean: for **machine-authored** goldens, the **solver** agreed — consistency check between generator and engine, not independent human ground truth.
- **The `rule_attribution` fail** is a clear example: expected rule set did not match the solver (typically **wrong golden**).
- **The inconclusive counterfactual** means the scenario (base UNSAT) did not support the story the golden told; revising worlds or gold would yield a clear pass or fail.
