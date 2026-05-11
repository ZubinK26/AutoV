# CPMpy policy pipeline (`cpmpy_wfm_policy`)

NL → verified **CPMpy** policies per `CPMpy/Project_Spec/`. This package is a **sibling consumer** of the same WFM handoff workflow as `smt_pipeline` (different target language: Python constraints, not SMT-LIB).

## Install

From repo root (workspace package):

```bash
pip install -e ".[cpmpy-pipeline]"
```

Requires **Python 3.11+**. Optional extras pull in `cpmpy`, `hypothesis`, `z3-solver`, `pydantic`, and **`pyyaml`** (Phase 0 glossary checks).

## Phase 0 — signature and glossary drafting

Workflow: `CPMpy/Project_Spec/Project_Spec_Agents/04_signature_glossary_workflow.md`, dev plan: `dev_plans/dev_plan_cpmpy_phase0_signature_glossary_v1.md`.

Structural checks are programmatic (no LLM). `phase0-run` uses the same Gemini wiring as `run`. Human review is gated via `workflow_state.json` (`phase_0a_approved`, `phase_0b_approved`); use **`--skip-human`** only for CI or local automation.

Prompts: `cpmpy_wfm_policy/llm/prompts/signature_{drafter,critic,refiner}.md`, `glossary_drafter.md`.

Cold-start stub domain: `domains/scheduling_sketch/` (`rules.txt` + optional `domain_notes.md`).

## Layout

| Path | Role |
|------|------|
| `cpmpy_wfm_policy/pipeline/drafting/` | **Phase 0** structural checks, drafter/critic/refiner/glossary agents, `run_phase0` |
| `cpmpy_wfm_policy/pipeline/` | Orchestrator, formalizer, AST validator, cheap checks, **consistency**, repair, diagnoser |
| `cpmpy_wfm_policy/verification/` | Medium checks, roundtrip, Hypothesis helpers, mutation |
| `cpmpy_wfm_policy/runtime/` | Pattern A/B, router, state extractor, **audit log**, `Decision` |
| `cpmpy_wfm_policy/llm/` | Formalizer backend (Gemini via `registry_stage.llm.gemini_call`) |
| `cpmpy_wfm_policy/wfm_import/` | **WFM handoff → `rules.txt` + stub `tools.json`** |
| `domains/` | Example bundles: `refund_example` (scalar), **`inventory_alldiff`** (vector + `AllDifferent`), **`scheduling_sketch`** (Phase 0 cold-start stub), `slots_alldiff`, `vector_line` |

## Latency (runtime)

- **Pattern A** (scalar, no globals/vectors): direct evaluation — target **&lt;10 ms** for the scalar subset.
- **Pattern B** (globals and/or vector rules): SAT with Z3 — **tens of ms**. The audit log records `pattern_used` per decision so you can split metrics.

## Domain bundle (inputs)

Each run needs:

1. `signature.py` — vocabulary, `TOOL_DEPENDENCIES`, optional `GLOBAL_CONSTRAINTS`, `TEST_SHAPE_BOUNDS`.
2. `glossary.md`
3. `rules.txt` — one NL rule per line
4. `tools.json` — gated tools (validated with Pydantic)
5. `fixtures/per_rule.py` — optional cheap-check fixtures

## CLI (`cpmpy-policy-pipeline`)

```bash
cpmpy-policy-pipeline validate-domain --domain path/to/bundle
cpmpy-policy-pipeline prepare-from-wfm --handoff exports/.../wfm_handoffs/foo.json --out-dir work/cpmpy_bundle
cpmpy-policy-pipeline reset-domain --domain path/to/bundle [--out-dir exports/cpmpy_rerun]
cpmpy-policy-pipeline phase0-check-signature --domain path/to/bundle
cpmpy-policy-pipeline phase0-check-glossary --domain path/to/bundle
cpmpy-policy-pipeline phase0-run --domain path/to/bundle [--skip-human] [--rerun-phase-0a]
cpmpy-policy-pipeline run --domain path/to/bundle --out-dir work/out   # Phase 1: requires Gemini env from registry
cpmpy-policy-pipeline runtime-check --bundle-dir work/out               # smoke: `gate_tool` + `runtime_audit.jsonl`
```

After `prepare-from-wfm`, copy or author `signature.py` and `glossary.md` before `run`.

## Orchestrator outputs

- `policy.py`, `manifest.json`, `verification_log.jsonl`
- **`consistency_report.json`** — joint SAT, per-rule reachability warnings, tool coverage (§5.3.3), optional `pairwise` placeholder when `CPMPY_PAIRWISE_CONSISTENCY` is set

## Medium-tier verification (scope)

- **Cumulative SAT** — all rules so far must be jointly satisfiable (batched).
- **Hypothesis** — the orchestrator calls **`medium_hypothesis_smoke_ok`**: it draws **`CPMPY_MEDIUM_HYPOTHESIS_EXAMPLES`** states (default **100**) from `flat_state_strategy` and evaluates each **Pattern A** rule on each draw. This is **not** full `@given` property testing (no shrinking, no falsification loop); it is intentional **smoke-scale** coverage in-process. For deep properties, add dedicated **`@given`** tests under `tests/` against a fixed `policy.py`.
- **Mutation** — `run_mutation_flip_dependency_smoke` in `verification/medium_checks.py` is implemented and **unit-tested**, but **not** invoked from **`run_orchestrator`** today. Dependency-sensitive “flip one field and expect falsification” needs a reliable per-rule `(state_when_true, critical_field, alt)` source (e.g. extended fixtures or SAT model extraction); treat as a **spec gap** until wired.
- **Roundtrip** — `verification_log.jsonl` **`roundtrip`** events include **`nl_source`**, **`nl_back_translation`**, **`orig_rule_module`**, **`reform_rule_module`** (and **`reform_used_symbols`** when present) for audit.

## Phase 0 vs `run`

**`cpmpy-policy-pipeline run`** does **not** call Phase 0 agents. It assumes **`signature.py`** and **`glossary.md`** exist in the domain. Evidence from a **`run` only** (e.g. `verification_log.jsonl`) **does not** prove drafter/critic/refiner/glossary-drafter behavior. If you ran **`phase0-run`** earlier, that run’s **`signature_draft_log.jsonl`** / **`glossary_draft_log.jsonl`** (and LLM outputs there) are the Phase 0 audit trail.

## Tests (mocked LLMs)

```bash
pytest CPMpy/policy_pipeline/tests
```

## Dev plan

- `dev_plans/dev_plan_cpmpy_policy_pipeline_v1.md`
- `dev_plans/dev_plan_cpmpy_phase0_signature_glossary_v1.md`
