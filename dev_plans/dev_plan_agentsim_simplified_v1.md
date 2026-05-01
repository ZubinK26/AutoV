# Dev plan: agentsim_simplified

**Goal:** Reach a state where you can **run `apply_refund` against realistic DB snapshots** and get ALLOW/BLOCK from Z3, with a **small** policy and a **thin** translation layer.

**Docs:** `agentsim_simplified/*_simpl.md` (spec), this plan (implementation order).

**Status (2026-05):** Refined policy `exports/nl_chunk_smt_runs/agentsim_simplified/policy_model_refined_simpl.smt2` (see `policy_model_refined_simpl_CHANGELOG.md`), Python package `agentsim_simplified/` with `SimplPolicyChecker`, `RefundCallScenario`, `validate_apply_refund`, `runner`, and `agentsim_simplified/tests/test_simpl_policy.py`.

---

## Phase 0 — Prerequisites (you run; needs Gemini / `.env` as for full agentsim)

Two artifacts gate “runtime testing with state data”:

1. **Formalized model** — a single satisfiable `policy_model.smt2` whose symbols match what the translator will emit.
2. **Translation layer** — Python that turns `StateBundle` + `ToolCall` into SMT assertions (and optionally maps unsat cores back to NL).

Until both exist, work can proceed on **simulation-only** code (`entities`, `seed_data`, `runner`) using a **stub** validator that always ALLOWs or uses hardcoded rules.

### Command to produce the policy (same family as `04_agentic_guardrails` / nl-chunk SMT)

From the **repository root** (`AutoV`), with API keys loaded for WFM + formalizer:

```bash
python -m wfm_orchestration.nl_chunk_smt_policy_pipeline --nl-file agentsim_simplified/04_agentic_guardrails_simpl.md --work-dir exports/nl_chunk_smt_runs/agentsim_simplified --rules-per-chunk 10
```

- **Output (default layout):**  
  `exports/nl_chunk_smt_runs/agentsim_simplified/policy_model.smt2`  
  plus `wfm_handoffs/`, `smt_bundles/`, `policy_snapshots/`, `nl_chunk_progress.json`.

- **Resume / reset:** If you re-run after partial progress, the chunk runner uses `nl_chunk_progress.json`. Use `--reset-progress` to start from rule 0.

- **Sanity check:**  
  `python -m smt_pipeline.policy_check exports/nl_chunk_smt_runs/agentsim_simplified/policy_model_refined_simpl.smt2`

**Handoff-only alternative (then SMT in a second step):**  
`python -m wfm_orchestration.cli --wfm-profile smt --skip-registry --file agentsim_simplified/04_agentic_guardrails_simpl.md --handoff bundles/wfm_artifacts/agentsim_simplified_handoff.json`  
then  
`python -m smt_pipeline --handoff bundles/wfm_artifacts/agentsim_simplified_handoff.json --policy-model exports/nl_chunk_smt_runs/agentsim_simplified/policy_model.smt2 --out-bundle-dir bundles`

---

## Phase 1 — After `policy_model.smt2` exists

**Blocker:** Inspect the **actual** sorts, functors, and `ToolCall` / `is-permitted` (or equivalent) encoding the pipeline produced. The simplified NL file deliberately **does not** lock in symbol names.

**Tasks:**

1. Document **symbol map** (short internal markdown or comments in `validator.py`): customer/account/transaction fields, refund call shape, legality predicate name.
2. Implement **`policy_loader.py`**: parse policy, startup `check-sat`, raise on UNSAT.
3. Implement **`validator.translate_state(bundle)`** and **`validator.translate_call(call)`** producing assertions consistent with the policy.
4. Implement **legality query** per `03_validation_workflow_simpl.md` (or align with `GuardrailsPolicyChecker` entailment style if you prefer parity with `agentsim`).
5. **`rule_mapping.json`** — extract from pipeline comments / `; Rule:` tags, or maintain by hand for ~10 lines.

**Milestone:** `test_validator.py`: ALLOW on clean T-001 path; BLOCK on FAILED KYC (T-004); BLOCK on sanctions (T-005).

---

## Phase 2 — Simulation + integration

Per `01` / `02` specs:

- `entities.py`, `seed_data.py`, `trace.py`, `agent.py`, `runner.py`, `tools.py`
- Wire `apply_refund` → `lookup_bundle` → `validate_call` → execute or `RefundError`
- Run `scenario_demo` end-to-end; trace shows five gated outcomes aligned with spec

---

## Phase 3 — Optional hardening

- Vulnerable + >20k goodwill path (seed row C-002 / T-002) if you extend the scripted scenario
- Entailment vs UNSAT core UX (mirror lessons from `agentsim` NL query tests)
- Package under `agentsim_simplified/` as a Python package with `pyproject` entry if desired

---

## What you need before asking Cursor to “finish the validator”

| Deliverable | Owner |
|-------------|--------|
| `policy_model.smt2` for this slice | You (pipeline command above) |
| Optional: paste or path to committed `.smt2` after first successful run | You |
| Symbol + legality convention from that file | Cursor / you in Phase 1 |

Once the `.smt2` is in `exports/nl_chunk_smt_runs/agentsim_simplified/` (or path you choose), say where it landed and implementation can continue without guessing functor names.
