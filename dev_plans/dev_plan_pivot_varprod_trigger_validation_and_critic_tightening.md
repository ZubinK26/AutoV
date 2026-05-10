# Dev plan: Var-product trigger validation + critic tightening (post-Test_input2 regression)

## Problem

- **Semantic critic (`pivot_critic`)** compares **effective NL** to **`synthetic_en.md`**. It does **not** reliably surface **per-rule trigger shape** (e.g. dropping one conjunct from a **product-limit** implication). Two PASS runs can miss the same gap.
- **CrossCritic** can **wave through** template diversity (`CONSTANT_RELATIONAL` vs `LOGICAL_IMPLICATION`) without checking that **every operand** implied by NL for a **multi-factor / product** limit appears in the **guarding conditions** as intended.
- **CrossRepairer** can weaken triggers when “standardize numerics / remove guards” is interpreted loosely (mitigated by prompt; **structural guard still needed**).

## Goals

1. **Deterministic IR check (primary):** For each rule whose `required_condition` contains **`varprod_cmp`**, require **`left_variable`** and **`right_variable`** each to **appear in `trigger_condition`** (recursive walk of atoms / varcmp / varprod / and / or / not — same variable name string). Emit structured issues (rule_id, missing variable, message). This encodes a **pipeline convention**: product limits must not gate on only one factor in the trigger while the NL treats both factors as part of the product story. **Allowlist / escape hatch** (optional v1): env or per-rule key to skip for exotic encodings (document if added).
2. **`pivot_critic` prompt:** Instruct the model to **spot-check NL lines that assert multi-factor numeric / product relationships** against **rule-level structure**, not only the synthetic prose. **Optional (v1 or v1.1):** pass a **short deterministic excerpt** into the critic payload—e.g. **`linearize_rules_for_cross_critic` filtered to rules whose JSON contains `varprod_cmp`** (R0003/R0004-style), appended after `<<<SYNTHETIC_EN>>>` or a new placeholder `<<<VARPROD_RULES_LINEARIZED>>>`—so the critic sees triggers without reading raw JSON.
3. **`cross_critic.md` prompt:** Add an explicit bullet under discipline: for **product / multi-variable limits**, verify **all named operands** (from NL + linearization) are **reflected in conditions as the NL requires**; **PASS** only if that holds—not merely “templates differ.”
4. **Product / CLI:** **`--strict-precheck` or `--fail-on-precheck-warnings`:** exit non-zero when `precheck_ok` is false (existing heuristic precheck). **Separate flag (recommended):** **`--fail-on-ir-structure`** (name TBD) when the **new varprod trigger validator** reports any issue—so operators can enforce IR structure without conflating with legacy precheck quirks (e.g. constant-in-NL heuristic noise).
5. **Orchestration (`run.py`):** Run the validator **after** rules are finalized for a phase: post initial compile, post structural repair, post semantic repair, post cross repair—**same points `load_rules_and_compile` succeeds**—and merge issues into **`precheck.json`** or a dedicated **`ir_structure_check.json`** (prefer dedicated file + summary fields for clarity).
6. **Tests / regression:**  
   - **General:** Unit tests on synthetic minimal rule dicts (varprod with full trigger → OK; varprod with one variable missing from trigger → issue).  
   - **Optional example-specific:** Small fixture or snapshot asserting **Test_input2 R0003** trigger references **both** operands in `trigger_condition` (regression net for the known incident; **not** a substitute for the general check).

## Non-goals (v1)

- Full **NL parse** to variable binding (regex “product of …”) — brittle; defer unless invariant + critic prove insufficient.
- Proving **semantic equivalence** of conditions (SMT); **structural convention** only.
- Changing **compiler** or **`varprod_cmp`** schema.

## Design

### A. Module `pivot_pipeline/var_product_trigger_validate.py` (name TBD)

- `collect_variables_in_condition(cond: dict) -> set[str]` — recursive.
- `find_varprod_rules(rules: list[dict]) -> list[tuple[rule_id, left, right]]` — scan `required_condition` trees for `kind == "varprod_cmp"` (mirror depth patterns used elsewhere if a shared walker exists).
- `validate_varprod_triggers(rules: list[dict]) -> list[str]` — return human-readable issues or structured dataclass list.
- **Rule:** for each varprod rule, `left` ∈ vars(trigger), `right` ∈ vars(trigger). If not, emit issue.

### B. `run.py` integration

- After successful compile paths where `rules` are authoritative, call validator; append to summary `varprod_trigger_ok: bool`, `varprod_trigger_issues: [...]`.
- Respect **`--fail-on-ir-structure`**: set outcome `blocked_ir_structure` or reuse `blocked_*` pattern; write `run_summary.json`.
- Order relative to **existing precheck** → define: run **after** `meta` available or purely on **rules JSON** (rules-only is enough for trigger walk).

### C. Prompts

- **`prompts/pivot_critic.md`:** New subsection “Multi-factor / product limits”: compare NL lines to **linearized varprod excerpt** when provided; DRIFT if operands or guards clearly mismatch.
- **`prompts/cross_critic.md`:** Bullet under discipline: product / multi-variable limits — operands and triggers vs NL.

### D. CLI (`cli.py`)

- `--fail-on-precheck-warnings` (or reuse naming consistent with tester flag style).
- `--fail-on-varprod-trigger` / `--fail-on-ir-structure` — document in README or pivot_pipeline README only if user asks (per project habit: optional one-line in `cli --help`).

## Tests

- `test_var_product_trigger_validate.py`: happy path, missing variable in trigger, nested and/or in trigger, not-applicable rules skipped.
- Optional: `test_test_input2_r0003_regression.py` loading minimal JSON fragment.

## Risks

- **False positives** if a valid encoding intentionally gates varprod with a trigger referencing only one variable (rare). Mitigation: allowlist or prompt to document exception in IR comment field (not in v1 schema — env allowlist only).
- **Critic token budget** if linearized excerpt grows — keep **varprod-only** filter.

## Implementation order

1. `var_product_trigger_validate.py` + unit tests (no `run.py` yet).  
2. Wire `run.py` + summary + optional `ir_structure_check.json`.  
3. CLI flags + exit codes.  
4. Prompt edits (`pivot_critic`, `cross_critic`).  
5. Optional Test_input2 regression snippet.  
6. Manual run on `exports/pivot_runs_test_input2` to confirm current bad R0003 fails validator until fixed.

## Status

**Implemented** — `varprod_trigger_validate.py`, `ir_structure_check.json`, `run.py` + `cli.py` + `cross_coherence.py` flags, `pivot_critic` / `cross_critic` prompt updates, `semantic_critic_loop` passes `<<<VARPROD_RULES_LINEARIZED>>>`, tests in `test_varprod_trigger_validate.py`.

Optional env: **`PIVOT_VARPROD_TRIGGER_SKIP_RULE_IDS`** (comma-separated rule ids).
