# Validation Workflow Specification (simplified)

Spec tree: `01_simulation_environment_simpl.md`, `02_agent_interactions_simpl.md`, `03_validation_workflow_simpl.md`, `04_agentic_guardrails_simpl.md`.

## Purpose

Define how a proposed `apply_refund` tool call becomes an ALLOW or BLOCK decision via SMT validation against the policy model. This is the spec your existing NL→SMT-LIB pipeline plugs into. It is deliberately a single-purpose validator tonight: per-call validation only. The pre-deployment consistency check is reduced to a startup-time SAT check on the loaded policy (if unsat, the runner refuses to start). No separate consistency CLI tonight.

## What you have already

- An NL→SMT-LIB pipeline that takes plain-text NL rules and produces SMT-LIB 2.6 output.
- The file `agentsim_simplified/04_agentic_guardrails_simpl.md` (entity lines + guardrail lines) ready for that pipeline.
- After the pipeline runs, you have `policy_model.smt2` (path configurable; chunk runs default to `exports/nl_chunk_smt_runs/<stem>/policy_model.smt2`).

## What this spec adds

A Python module that:
1. Loads `policy_model.smt2` once at startup.
2. SAT-checks the policy as a whole. If unsat, raises `PolicyInconsistencyError` and the runner exits.
3. Exposes `validate_call(call: ToolCall, bundle: StateBundle) -> Decision`.

## Decision shape

```python
@dataclass(frozen=True)
class Decision:
    allow: bool
    unsat_core: list[str]   # rule IDs, empty if allow=True
    explanation: str        # human-readable, empty if allow=True
```

Rule IDs are the labels embedded by your NL→SMT-LIB pipeline. They should be stable strings (exact format is whatever the pipeline emits). Cursor should not invent these; the pipeline output is canonical.

## Per-call validation procedure

For every `apply_refund` call:

1. **Build state assertions.** Translate `bundle.customer`, `bundle.account`, `bundle.transaction` into a set of ground SMT-LIB assertions. Each scalar field becomes an `(assert (= (field-name entity-const) value))`. Booleans, ints, and string-like enums all map to standard SMT-LIB primitives. The translator is straightforward and lives in `validator.py`.

2. **Build the call assertion.** Translate the proposed call into a ground term: an `apply_refund` call with the four parameters as constants. Bind it to `proposed-call`.

3. **Push policy + state + call into a fresh solver context.** Use `z3.Solver` with the parsed policy assertions cached from startup. Push the state and call assertions on top.

4. **Query.** Add the negated legality assertion `(assert (not (legal current-state proposed-call)))`. Call `solver.check()`. If `unsat`, the call is legal — return `Decision(allow=True, unsat_core=[], explanation="")`. If `sat`, the call has at least one violating model — extract the unsat core via `solver.unsat_core()`.

5. **Build explanation from core.** Map each rule ID in the core to its NL text via a mapping file produced by your pipeline. Concatenate into a short paragraph.

6. **Return.** `Decision(allow=False, unsat_core=rule_ids, explanation=text)`.

## State translation rules

For tonight, the translator handles exactly these field types:
- `str` (used for enum-like values: `kyc_status`, `account_status`, `refund_type`, etc.) → SMT-LIB constant of an uninterpreted sort (or, if your pipeline prefers, a finite-domain enum). Equality on these constants only.
- `int` (amounts in pence, the goodwill total) → SMT-LIB `Int`.
- `bool` (vulnerable_flag, has_sanctions_block) → SMT-LIB `Bool`.

That's all. No dates, no lists, no nested objects.

## Solver setup

- Solver: Z3, accessed via `z3-solver` Python package.
- Policy is parsed once at startup with `z3.parse_smt2_file(...)` or equivalent.
- Per-call: use solver `push()` / `pop()` to add and remove the state and call assertions without re-parsing the policy.
- Unsat-core extraction requires that the policy assertions are tracked. The pipeline should emit `(assert (! ... :named R-N))` form. If it doesn't, the labels need to be added at parse time using `assert_and_track`.

## Caching

Tonight: cache the parsed policy. Don't cache decisions. The scenario is small enough that running everything fresh is fine.

## Pre-deployment consistency check (minimal version tonight)

At startup, after parsing the policy:
1. Push only the policy assertions.
2. Call `check()`.
3. If `unsat`, raise `PolicyInconsistencyError` with the unsat core.
4. If `sat`, proceed.

That's the entirety of the consistency check tonight. No reachability check, no pairwise interaction check, no coverage check. Those are v2.

## Latency

Not a concern tonight. The whole scenario runs ten steps; even a slow validator is fine.

## Audit log

Tonight, the trace list is the audit log. Every Decision is captured in the TraceEntry that the runner builds. No file persistence.

## What this spec does NOT specify

- The NL→SMT-LIB pipeline (you have it in-repo under `smt/smt_pipeline` and `wfm_orchestration`).
- The exact SMT-LIB encoding choice for entity types (uninterpreted sort vs. enum) — leave to the pipeline.
- Anything LLM-related.

## Deliverables for Cursor

- `policy_loader.py` — `load_policy(path) -> ParsedPolicy`, runs the startup SAT check, raises `PolicyInconsistencyError` on failure.
- `validator.py` — `validate_call(call, bundle) -> Decision`. Contains the state and call translators. Imports from `policy_loader`.
- `rule_mapping.json` — produced by your pipeline or maintained by hand, maps rule IDs to the original NL strings. Cursor reads this for explanation text.
- One small unit-test stub (`test_validator.py`) with three tests: a clean ALLOW, the FAILED-KYC BLOCK, the sanctions-block BLOCK. Just to confirm the validator works in isolation before hooking up the runner.

## File layout for the whole evening

```
agentsim_simplified/
  (or a python package) 
  entities.py
  seed_data.py
  tools.py
  trace.py
  agent.py
  runner.py
  04_agentic_guardrails_simpl.md    # NL source (input to pipeline)
  exports/.../policy_model.smt2     # produced by nl_chunk_smt_policy_pipeline
  rule_mapping.json                 # optional; maps pipeline rule tags to NL
  policy_loader.py
  validator.py
  test_validator.py
  README.md
```

Run `python runner.py` and the demo plays.
