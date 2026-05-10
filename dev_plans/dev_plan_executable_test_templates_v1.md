# Dev plan: Executable test templates (v1) — workflow through per-test verdict

## Reference

- Concept catalog and workflow intent: `Test-Gen-Coverage.md` at repo root.
- Policy execution anchor today: `NagV/pivot_pipeline` — `load_rules_and_compile`, `build_meta_scheme`, `z3_compile.build_solver` / `run_z3_check` on a `MetaScheme`.

## Pipeline order (canonical — pivot integration)

The **template generator + executable suite** (`--with-template-generator`, `--template-suite`) must run **after every existing post-model stage**, not between Tester and the first Critic pass.

**Required sequence:**

1. Phase 0 (WFM) → extract / registry → compile → `meta_scheme.json` / Z3 → `synthetic_en.md`
2. Precheck (+ optional `fail` gates)
3. **Tester** (optional, `--with-tester`)
4. **Semantic critic** (pivot critic loop, unless skipped)
5. **CrossCritic** / CrossRepairer loop (optional)
6. **Post–CrossCritic final semantic critic** (when CrossCritic ran and passed — second NL ↔ synthetic alignment pass)
7. **Template suite** — LLM generate (if enabled) → validate → Z3 executable tests → `template_run_report.json`
8. Final **`outcome`** / warnings / `run_summary.json`

**Not allowed:** Running the template phase **before** step 4–6 when those steps are enabled for the run — i.e. do not place template work “after Tester only” as if that were the end of policy review.

**Future (post-v1, separate plan):** **Template repairer** on verdict failures, then **loop back** to the **final critic** path (semantic pivot critic) for operator / model sign-off. That loop is **out of v1** scope here.

**Implementation note:** As of the last revision of this document, **`run_pivot_pipeline` still hooks the template phase too early** (after Tester, before Critic). Relocating the hook to **step 7** above is **required** to match this plan; treat that move as part of closing **Phase 7b — hook order**.

## v1 definition (closed scope)

**v1 is complete** when the following **end-to-end path** exists and is documented:

1. **LLM** — Given the same policy context the operator already has after a successful compile (effective NL excerpt, `rules_extracted` / variable and rule-id visibility, optional `synthetic_en.md` / pathway summary), the model **fills executable template instances** (JSON matching our Pydantic schemas), including **goldens**, for the eight `template_kind` values where applicable.
2. **Validate** — Every LLM-produced instance is **parsed and validated** (schema + `validate_instance` against live `MetaScheme`); bounded retry or structured repair loop on failure is allowed.
3. **Execute** — The suite is **run against the real Z3 encoding** of that policy (existing `execute_instance` path).
4. **Verdicts** — **`template_run_report.json`** (or equivalent) records **per-test verdicts** through diff.

**Explicitly out of scope for v1 (defer):** any **remediation** driven by verdicts (repairer, auto-edit rules, CI **fail-on-template** gating, refreshing goldens from actuals, human handoff workflows). Optional tooling flags that only **record** results without blocking merges may be added if trivial; policy is “ship verdicts first.”

## Goal

Deliver the **full v1 pipeline** above: **LLM uses templates → suite materialized → validate → execute on real model → diff → verdict report**, domain-agnostic and aligned with `Test-Gen-Coverage.md`. Manual-only suite authorship remains supported for tests and debugging; v1 **also** requires the **integrated LLM authoring** path.

## Scope boundaries

| In scope (v1) | Out of scope (defer) |
|----------------|----------------------|
| LLM **prompt(s)**, response parsing, validation/retry, writing generated suite JSON | **Remediation** from template results (repairs, critic/tester hooks on failures) |
| **Pipeline integration** — **after** full post-model review (Tester → Critic → Cross → final Critic), then template phase; see § Pipeline order | **`--fail-on-template-*`** and other CI gates (unless zero-cost additive) |
| Schemas, Z3 execution, diff, verdict report (existing **machine** stack) | Refreshing goldens from actuals automatically |
| Pytest with **mocked** LLM (or golden transcript) for the integrated path | ASP / non-Z3 executors |
| Unit + integration tests; documentation of inputs/outputs for the LLM step | Tester/Critic behavioral changes |

## Design principles

1. **Single semantics** — Lowering maps template fields **only** into names and sorts the compiler already produced (`variable_sorts`, rule ids from IR, pathway/meta_scheme fields). No parallel ontology.
2. **Deterministic** — Same instance + same policy build → same lowered Z3 fragment + same comparison result (modulo Z3 `unknown`, which must be a first-class verdict).
3. **Golden is data** — Expected outcomes are enums, sorted lists, small structured objects — **no** NL in goldens.
4. **Executor boundary** — Core logic depends on a narrow API, e.g. `execute_lowered(lowered: LoweredTest, ctx: PolicyRunContext) -> ActualResult`, backed today by Z3. Future backends implement the same API.

## Artifacts (files)

| Artifact | Role |
|----------|------|
| `template_suite.schema.json` (or Pydantic models in code) | Versioned envelope: `suite_id`, `schema_version`, optional `policy_binding` (digest, semantics version). |
| `instances.jsonl` | One JSON object per line: `template_kind`, `instance_id`, author fields, `golden` (or reference to golden file). |
| `lowered/` (optional debug) | Serialized lowered form per instance (for debugging lowering only). |
| `template_run_report.json` | Per-instance rows: `instance_id`, `template_kind`, `verdict`, `actual`, `golden`, `diff` summary, `error` if lowering/run failed. |
| `template_suite_generated.json` (v1) | LLM-written suite after successful parse/validate (Phase 6–7). |
| `template_generator_raw.txt` (v1, optional) | Audit trail of raw model output. |

## Canonical verdicts

| Verdict | Meaning |
|---------|---------|
| `pass` | Actual equals golden under comparison rules for that template kind. |
| `fail` | Comparable result present and mismatch. |
| `error` | Validation/lowering threw, or executor error. |
| `inconclusive` | Solver returned `unknown` (or policy encoding cannot answer query without extension). |

## Architecture (suggested package layout)

All new modules under `NagV/pivot_pipeline/` (or subpackage `pivot_pipeline.template_suite/`):

| Module | Responsibility |
|--------|----------------|
| `pivot_pipeline/template_suite/schemas.py` | Pydantic models: suite envelope, per-kind instances. |
| `pivot_pipeline/template_suite/validate.py` | Cross-field checks, sort compatibility vs `MetaScheme`. |
| `pivot_pipeline/template_suite/lower.py` | Boundary expansion, debug dumps. |
| `pivot_pipeline/template_suite/execute_z3.py` | Z3 execution → actual dict. |
| `pivot_pipeline/template_suite/diff.py` | Actual vs golden → verdict. |
| `pivot_pipeline/template_suite/run.py` | Load suite + bind policy → report. |
| `pivot_pipeline/template_generator_agent.py` (v1) | Build user message from NL + rules summary; call `pivot_llm_complete`; parse JSON → `TemplateSuiteFile`; validation errors → bounded retry with truncated error feedback. |
| `prompts/template_generator.md` (v1) | Instructions: eight kinds, JSON-only output, use **only** `rule_id` / variable names present in supplied excerpt; golden shapes; no NL inside goldens. |
| `cli.py` / `run.py` (v1) | Flags to run generator + executor in one pass; **call site** must follow § Pipeline order (step 7). |

**Policy run context** minimally includes: path to `rules_extracted.json` (or in-memory `MetaScheme`), path to `meta_scheme.json` if needed for ids, and compiled encoders. Reuse `build_solver(meta)` where possible; **v1 likely adds** a “scenario push” API that asserts grounded facts and runs additional checks (see § Z3 / executor).

**Precondition:** Template phase only runs when the run has **already** produced `rules_extracted.json`, Z3 artifacts, and (for the generator) the usual `work_dir` context — **not** because the phase is “right after Z3,” but because the operator has finished **steps 1–6** when applicable.

**LLM context pack (v1):** deterministic excerpt builder: `policy_id`, sorted `variable_sorts` or inferred names, `rule_id` list + template classes (from rules JSON), optional compact `synthetic_en.md` head + tail cap, optional `evaluation_pathways[0].must_satisfy_all`. No secrets; length caps to match other pivot agents. *Optional later enhancement:* include short excerpts from critic/cross artifacts only if useful for template authoring — not required for v1 relocation.

## Phase 0 — Schemas and suite loader

1. Define `schema_version` (string) and document backwards-compatibility rules.
2. Implement envelope + discriminated `template_kind` with eight variants (or one model per kind in a tagged union).
3. Load and validate `instances.jsonl`; stable ordering by `instance_id`.
4. Tests: malformed lines rejected; golden type matches kind.

## Phase 1 — Policy binding

1. Accept `work_dir` (pivot layout) or explicit paths to `rules_extracted.json` + built `MetaScheme` in memory.
2. Compute **binding record** (rules hash, `POLICY_SEMANTICS_VERSION` / constants, optional git sha) for audit trail in report; **do not** block run if binding mismatches suite metadata in v1 (optional warning only).
3. Tests: binding recorded in report.

## Phase 2 — Z3 executor foundation

Today `run_z3_check(meta)` checks global satisfiability once. Template tests require **per-instance** queries:

1. **World / scenario facts** — Map template “world” maps to Z3 assertions over **existing** policy variables (and only named constants allowed in v1). Document mapping: string keys in instance → IR variable names (must exist in `variable_sorts`).
2. **Push + query pattern** — For each lowered test: clone or scope solver from `build_solver(meta)`’s assertions; `add` scenario facts; run `check()` with optional `prove`/`implies` pattern depending on template kind.
3. **Decision channel** — Define how a **decision-query** maps to the formal model (e.g. boolean `yields` / decision atom already in encoding, or a dedicated query variable introduced only in test layer — **decide in implementation** and document). Must match **golden** enum (e.g. `allow` / `deny` / `unknown_bucket`).
4. **Unknown handling** — Any Z3 `unknown` → `inconclusive` with reason string in report.

Tests: one minimal `MetaScheme` (single rule, one boolean decision) + one hand-written lowered test; assert `pass`.

## Phase 3 — Per-template implementation

Each row: lowering rules, golden shape, comparison function, minimal example instance.

### 1. Scenario (world) template

- **Intent:** Pin “these facts”; verify model still **admits** a consistent state (or optional model slice golden).
- **Lowering:** Assert equalities/inequalities / bool fixes per world dict.
- **Golden (v1):** `{ "sat": true }` or `{ "sat": false }` for “world ∧ policy” (or “world alone” if testing only scenario encoding — document which).
- **Compare:** Boolean sat bit; if golden includes optional `variable_values` subset, check against model.

### 2. Decision-query template

- **Intent:** Same world + one query → decision equals golden.
- **Lowering:** Scenario + query record → decision variable assignment or entailment check.
- **Golden:** `{ "decision": "<enum>" }` plus optional numeric/enum fields.
- **Compare:** Normalized enum (case, aliases forbidden in file; one canonical set).

### 3. Explanation / rule-attribution template

- **Intent:** Outcome + **which** rule/pathway explains it.
- **Lowering:** Same as (2) plus extraction of active rule ids from **instrumented** encoding *or* from a secondary Z3 query per candidate rule id.
- **Golden:** `{ "decision": "...", "rule_ids": ["R0001", ...] }` — set compared as **sorted** lists; optional “any of” semantics if ties documented.
- **Dependencies:** May require **encoding extension** to expose firing indicators (e.g. per-rule Bool “fired”) — spike early; if too large for v1, ship with `inconclusive` when witness unavailable and document gap.

### 4. Boundary / monotonicity template

- **Intent:** One parameter × three samples (below / at / above).
- **Lowering:** Expand to **three** internal `LoweredTest` rows from one instance **deterministically** (seed = instance fields, no randomness).
- **Golden:** List of three decisions or `{ "monotone": "non_decreasing", "axis": "amount" }` — v1 recommends **explicit triple golden** for simplicity.
- **Compare:** Triple-wise equality; optional monotonicity check derived from triple.

### 5. Counterfactual flip template

- **Intent:** Two worlds differ by one fact; decision changes (or stays) as specified.
- **Lowering:** Two scenario blocks + two queries (or one query applied in both).
- **Golden:** `{ "base_decision": "...", "mutant_decision": "...", "expect_flip": true }` or explicit pair compare; **implemented:** `{ "base_decision": "...", "mutant_unsat": true, "expect_flip": true }` when mutant world makes policy∧world UNSAT.
- **Compare:** Match flip boolean and both decisions; or, in `mutant_unsat` mode, base sat + mutant unsat + `base_decision`.

### 6. Obligation / constraint inventory template

- **Intent:** Set of active obligations / `must_satisfy` must match golden multiset.
- **Lowering:** After scenario, **enumerate** obligations from encoding (predicates or MetaScheme obligation list — align with `precheck` / IR).
- **Golden:** `{ "obligations": [ { "key": "...", "args": [...] }, ... ] }` normalized sort.
- **Compare:** Multiset equality after canonical sort (stable key for each obligation).

### 7. Sat / unsat / consistency template

- **Intent:** Policy + scenario is SAT or UNSAT as golden says.
- **Lowering:** Scenario only (or scenario + extra constraint object if template allows).
- **Golden:** `{ "expect": "sat" | "unsat" }`.
- **Compare:** Z3 result vs expect; `unknown` → `inconclusive`.

### 8. Pairwise equivalence / non-interference template

- **Intent:** Two queries in same world — same decision unless attribute differs.
- **Lowering:** One scenario + `query_a` + `query_b`.
- **Golden:** `{ "expect_equal": true }` or `{ "decision_a": "...", "decision_b": "..." }`.
- **Compare:** As specified.

## Phase 4 — Runner and CLI

1. `template_run.py`: orchestrate validate → lower → execute → diff for each instance; aggregate summary counts (`passed`, `failed`, `errors`, `inconclusive`).
2. Write `template_run_report.json` to `work_dir` (or `--out`).
3. Optional terminal summary (one line per failure).
4. Wire entry: extend `pivot-pipeline` or add `python -m pivot_pipeline.template_run` — pick one in implementation to avoid overloading `cli.py`.

## Phase 5 — Tests (pytest) — machine stack

| Test | Purpose |
|------|---------|
| Schema validation rejects bad goldens | Safety |
| Lowering snapshots | Regression for deterministic maps |
| End-to-end tiny policy | Each template kind at least one `pass` |
| Z3 unknown simulation | If possible mock solver; else document skip |
| Rule-attribution | If witness not implemented, expect `inconclusive` with stable message |

## Phase 6 — LLM template generator (v1 required)

1. **Prompt** (`prompts/template_generator.md`) — Describe each `template_kind`, required fields, golden shapes, `query.decision_metric` contract, `counterfactual_flip` + `mutant_unsat`, boundary triple, etc.; require **single JSON object** or fenced JSON with root `{ "schema_version": "1", "suite_id": "...", "instances": [ ... ] }`; forbid inventing variable or `rule_id` names not in the excerpt.
2. **Context builder** — One function assembling excerpt from `work_dir`: read `rules_extracted.json`, optional `synthetic_en.md`, optional `meta_scheme.json` if present; enforce char caps.
3. **Agent** — `run_template_generator(...) -> TemplateSuiteFile`: call `pivot_llm_complete`; extract JSON (`parse_json_object` reuse from `json_util`); validate; on `ValidationError` / JSON errors, retry up to **N** (env e.g. `PIVOT_TEMPLATE_GEN_MAX_ROUNDS`, default 2–3) with error snippet in user message.
4. **Artifacts** — Write `template_suite_generated.json` under `work_dir`; optional `template_generator_raw.txt` for audit.
5. **Tests** — Mock `pivot_llm_complete` to return fixed JSON; assert valid suite and that downstream `run_template_suite` runs without error on toy policy.

## Phase 7 — Pivot pipeline integration (v1 required)

### Phase 7a — Mechanics (done)

Flags, generator, `run_template_suite`, `template_run_report.json`, non-fatal policy for `pivot-pipeline` exit code.

### Phase 7b — Hook order (**required**)

1. **Where** — In `run_pivot_pipeline`, move the template block to **immediately before** the final **`warnings` / `outcome` / `run_summary.json`** assembly — i.e. **after**:
   - semantic critic loop (when run),
   - CrossCritic / CrossRepair (when run),
   - post–CrossCritic final `run_semantic_critic_interactive_loop` (when run),
   - and the same **`fail_on_varprod_trigger`** checks that already follow that final critic.

2. **Remove** the template block from its current position (after Tester, before first Critic).

3. **CLI** — unchanged: `--with-template-generator`, `--template-suite`; optional future `--template-suite-out` if needed.

4. **Tests** — Add or adjust an integration test that asserts the template hook runs **only after** the critic/cross section in control-flow terms (e.g. by mocking/spying call order, or by documenting a single end-of-run injection point).

5. **Tests** — Integration test: temp `work_dir` with toy `rules_extracted.json`, mock LLM, assert `template_run_report.json` exists (existing generator tests remain valid).

**v1 default:** template generator + run **does not** change **exit code** of `pivot-pipeline` (verdicts and generator errors are recorded in `run_summary` / stderr only). Use standalone `pivot-template-suite` if you want process exit `1` on failed tests.

## Phase 8 — Tests (pytest) — LLM + integration

| Test | Purpose |
|------|---------|
| Mock LLM returns invalid JSON | Retry or error path; no crash |
| Mock LLM returns suite with wrong variable | Validation failure surfaced in report or generator error |
| Full chain mock | Generator → `run_template_suite` → report file on disk |

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Current Z3 helper only does global `check()` | Introduce scoped solver API in `template_execute_z3.py`; keep `run_z3_check` unchanged for pipeline. |
| Decision variable not uniquely defined in IR | Early spike: document canonical decision atom; temporary bridge constants in lowering only. |
| Rule-attribution expensive | Optional second phase; v1 may use `inconclusive` until firing instrumentation exists. |
| Sort / name mismatches at lowering | Validate instance against live `variable_sorts` in Phase 1. |
| LLM invents unknown ids | Prompt contract + excerpt lists allowed names; validate before Z3. |
| Long context | Hard cap excerpt; summarize rule list if over cap. |

## Implementation status

| Phase | Status |
|-------|--------|
| Phase 0 — Schemas / loader | **Done** — `template_suite/schemas.py` |
| Phase 1 — Policy binding | **Done** — `rules_sha256` + policy_id in `template_run_report.json` |
| Phase 2 — Z3 executor foundation | **Done** — `template_suite/execute_z3.py`; `build_solver` returns `sorts` in aux |
| Phase 3 — Template kinds 1–8 | **Done** — all eight kinds; `counterfactual_flip` supports `mutant_unsat` in golden; boundary `decision_metric=rule` uses full model when policy∧world is SAT, else rule∧world consistency check |
| Phase 4 — Runner / CLI (standalone) | **Done** — `template_suite/run.py`, `python -m pivot_pipeline.template_suite`, `pivot-template-suite` console script |
| Phase 5 — Pytest (machine) | **Done** — `tests/test_template_suite.py`, fixtures `template_suite_toy_*.json` |
| Phase 6 — LLM template generator | **Done** — `template_generator_agent.py`, `template_generator_context.py`, `prompts/template_generator.md` |
| Phase 7a — Pivot flags + generator + run | **Done** |
| Phase 7b — Hook order (after full critic/cross/final critic) | **Pending** — code still runs after Tester, before first Critic; relocate per § Pipeline order |
| Phase 8 — Pytest (LLM + integration) | **Done** — `tests/test_template_generator.py` (mocked LLM); add Phase **7b** call-order test when hook moves |

### Pivot CLI (integrated)

```text
pivot-pipeline ... --with-template-generator
pivot-pipeline ... --template-suite path/to/suite.json
```

```text
python -m pivot_pipeline.template_suite --suite SUITE.json --rules-extracted rules_extracted.json [--out template_run_report.json]
```

Exit code `1` if any instance `failed` or `error` (not on `inconclusive` only).

## Done criteria (v1)

**Machine path (baseline)**

- [x] For a **single pivot `work_dir`** with a successful compile, running the template runner with a hand-crafted suite produces `template_run_report.json` with **per-instance verdicts**.
- [x] All **eight** `template_kind` values are implemented **or** explicitly produce `inconclusive` with a documented reason (no silent skip).
- [x] Pytest covers lowering + at least one pass/fail path per kind on **synthetic** policies.
- [x] `Test-Gen-Coverage.md` cross-linked from this plan; golden vs actual semantics match the “same page” definition (execute on **real** model, diff to golden, stop at verdict).

**LLM + integrated pipeline (v1 remainder)**

- [x] Prompt `prompts/template_generator.md` + agent module (**Phase 6**) produces a valid `TemplateSuiteFile` from a real `work_dir` context excerpt (mocked in CI).
- [x] **`pivot-pipeline`** can run **generator → validate → execute → verdict report** (**Phase 7a**), writing `template_suite_generated.json` (when generating) and `template_run_report.json`.
- [ ] **Phase 7b — Hook order:** `pivot-pipeline` runs the template phase **after** Tester, semantic critic, CrossCritic/repair, and post–Cross final semantic critic — per § Pipeline order (not after Tester alone).
- [x] Pytest covers generator + retries with **mocked** LLM (**Phase 8**).
- [ ] Pytest (or equivalent) asserts **7b** placement once the hook is moved.
- [x] **No** verdict-driven remediation or **template → final critic** loop in v1; template failures are **non-fatal** for pipeline exit code (see Phase 7 note). **Future:** template repairer → final critic pass (post-v1).
