# Changelog: policy_model_refined_simpl.smt2

**Artifact:** `exports/nl_chunk_smt_runs/agentsim_simplified/policy_model_refined_simpl.smt2`  
**NL source:** `agentsim_simplified/04_agentic_guardrails_simpl.md`  
**Unmodified baseline:** `policy_snapshots/policy_latest.smt2` (chunk pipeline output)

## Summary

Human-maintained refinement so the policy matches **intended validation use** (ground DB facts, link entities, entail **ALLOW** on clean paths) without editing the auto-generated snapshot.

| ID | Change |
|----|--------|
| R-A | Removed `ToolCall` sort and its two universal axioms; refund-only slice reasons on `RefundCall` only. |
| R-B | Introduced `customer-exists-in-db`, `account-exists-in-db`, `transaction-exists-in-db`. Replaced tautological `exists` equalities with `not exists-in-db ⇒ not is-permitted`. |
| R-C | Replaced `forall r . transaction-status = posted` with: if transaction is in DB and not POSTED, then `not is-permitted`. |
| R-D | Added wiring: when customer+account exist in DB, `account-customer = refund-customer`; when account+txn exist, `transaction-account = refund-account`. |
| R-E | Totality axioms for the three `exists-in-db` predicates. |
| R-F | Positive completion: conjunction of NL-clean preconditions implies `is-permitted` (with type-specific merchant/goodwill/vulnerable caps). |

## Bridge note

The **translation layer** (`agentsim_simplified/simpl_scenario.py`) must ground the three `exists-in-db` flags and entity fields for each check. Missing entities should set the corresponding `exists-in-db` to `false` on the **affected** constants linked via `refund-customer` / `refund-account` / `refund-transaction`.
