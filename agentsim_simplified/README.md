# agentsim_simplified

Smaller sibling of `agentsim/`: one write tool (`apply_refund`), one read tool (`lookup_bundle`), ~10 NL guardrail lines, in-memory dict DB, scripted scenario.

## Spec files (`_simpl` suffix)

| File | Role |
|------|------|
| `01_simulation_environment_simpl.md` | Entities, seed data, tool surface |
| `02_agent_interactions_simpl.md` | Scripted `scenario_demo` |
| `03_validation_workflow_simpl.md` | Validator, SMT check, file layout |
| `04_agentic_guardrails_simpl.md` | Canonical NL for formalization |

## Dev plan

See **`dev_plans/dev_plan_agentsim_simplified_v1.md`** (pipeline command, translation layer, test milestones).

## Policy artifact

- **Refined (runtime default):** `exports/nl_chunk_smt_runs/agentsim_simplified/policy_model_refined_simpl.smt2`  
  Changelog: `exports/nl_chunk_smt_runs/agentsim_simplified/policy_model_refined_simpl_CHANGELOG.md`  
- **Chunk snapshot (unmodified):** `exports/nl_chunk_smt_runs/agentsim_simplified/policy_snapshots/policy_latest.smt2`

## Run the scripted demo

From repo root: `pip install -e .` then `agentsim-simpl-demo` or `python -m agentsim_simplified.runner`.

## Tests

`python -m pytest agentsim_simplified/tests/test_simpl_policy.py -v`

## Custom state / tool calls

Use `load_db` + `lookup_bundle`, then `validate_apply_refund(bundle, call)` or `RefundCallScenario` + `SimplPolicyChecker` for raw Z3 checks (`agentsim_simplified.validator`, `simpl_scenario`, `simpl_checker`).
