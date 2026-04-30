# Validation Workflow Specification

## Purpose

Define the end-to-end flow by which a proposed tool call becomes an ALLOW or BLOCK decision, and by which the policy model itself is checked for internal consistency before deployment. This is the spec your existing NL→SMT-LIB pipeline plugs into.

## Two distinct uses of SMT

The same formalized policy serves two purposes:

1. **Pre-deployment consistency check.** Run once when the policy is loaded or modified. Asks: is the rule set as a whole satisfiable? Are there contradictions? Are the rules reachable (i.e., is there at least one state in which any given rule actually triggers)?
2. **Per-action validation.** Run per tool call at runtime. Asks: given the current state and the proposed tool call, is the call permitted by the active policy?

Both checks consume the same compiled SMT-LIB output of the policy. They differ only in what they conjoin to that compiled model.

## Overall pipeline

```
[Policy NL document]
        |
        v
[NL → SMT-LIB pipeline]   (your existing system)
        |
        v
[policy.smt2]   (a reusable SMT-LIB declarations + assertions file)
        |
        +------> [Pre-deployment consistency check]
        |
        +------> [Per-action validator]
                       ^
                       |
                [State snapshot]   (from DB, per call)
                       |
                [Proposed tool call]   (from agent)
                       |
                [Compiled query]   (state facts + call facts + check_legal predicate)
                       |
                       v
                [Z3 / cvc5 solver]
                       |
                       v
                [Decision: ALLOW or BLOCK + unsat core]
```

The boxes labelled with brackets in the second column are what this spec covers. Your pipeline produces `policy.smt2`.

## What `policy.smt2` contains

Your NL→SMT-LIB pipeline produces an SMT-LIB 2.6 file with:

- Sort declarations for entity types (Customer, Transaction, Refund, etc.) — likely uninterpreted sorts with id projector functions, or finite-domain enumerations where sensible.
- Function declarations for state predicates: `(declare-fun customer-vulnerable (Customer) Bool)`, `(declare-fun transaction-amount-pence (Transaction) Int)`, etc.
- Function declarations for tool-call constructors and parameter accessors.
- A top-level `(declare-fun legal (State Call) Bool)` predicate.
- Assertions encoding each rule from the NL document, expressed in terms of the predicates above.
- A version tag in a comment line at the top.

The validator does not read the NL; it reads `policy.smt2`. The NL is only the source artifact for the formalization step.

## Pre-deployment consistency check

Run when `policy.smt2` is loaded. Sequence:

1. **Satisfiability check.** Push all policy assertions into a fresh solver context. Add a single witness assertion `(assert true)`. Call `(check-sat)`. Expected: `sat`. If `unsat`, the policy contradicts itself in the abstract — abort deployment, surface the unsat core as the contradicting rule IDs.

2. **Per-rule reachability check.** For each rule, check whether there exists a state and a call that triggers the rule's antecedent. If no such state exists, the rule is unreachable (dead code) — this is a warning, not an error, but it should be surfaced because dead rules usually indicate either a typo or an intent the policy author thought they encoded but didn't.

3. **Pairwise interaction check** (optional, expensive). For each pair of rules that share a tool or entity type, check whether there's a state where both fire and produce contradictory verdicts. This catches subtle interactions the author didn't anticipate. Run this in CI, not on every load.

4. **Coverage check.** For each write tool, verify there exists at least one state in which the tool is legal and at least one state in which it is illegal. A tool that is always legal under all states means no rule applies to it (warning). A tool that is always illegal means it was effectively disabled (probably an error).

The output of this phase is a `consistency_report.json` with:
- `policy_version`
- `satisfiable: bool`
- `contradictions: list[{rule_ids, explanation}]`
- `unreachable_rules: list[rule_id]`
- `tools_always_legal: list[tool_name]`
- `tools_always_illegal: list[tool_name]`
- `pairwise_conflicts: list[{rule_a, rule_b, explanation}]`

If `satisfiable=False` or any `contradictions` are present, deployment fails.

## Per-action validation

Triggered for every write tool call.

**Inputs:**
- `tool_call: ToolCall` with typed parameters
- `state_snapshot: StateSnapshot` containing the materialized DB facts for entities the call touches

**Procedure:**

1. Construct a fresh solver context derived from the loaded `policy.smt2`. (Cache the parsed policy across calls for performance; only push state facts and the call assertion per check.)

2. Translate the state snapshot into ground SMT-LIB assertions. Each entity becomes a constant of the appropriate sort, each scalar field becomes an assertion `(assert (= (customer-vulnerable c-123) true))`, etc. The runtime knows the schema of StateSnapshot and how to encode each field.

3. Translate the proposed tool call into a ground term: `(define-const proposed-call Call (mk-apply-refund c-123 t-789 4500 REASON-GOODWILL))` or similar.

4. Push the legality query: `(assert (not (legal current-state proposed-call)))`. This is the negation: we're asking the solver "find a model in which this call is NOT legal under the current state." If `unsat`, the call is legal under every interpretation consistent with the state — return ALLOW. If `sat`, the call has at least one violating interpretation — return BLOCK.

   (Equivalently: `(assert (legal current-state proposed-call))` and check if SAT, but framing as "prove legality by failing to find a counterexample" gives a usable unsat core for the explanation.)

5. On UNSAT (legal): return `Decision(allow=True)`.

6. On SAT (illegal): extract the unsat core via `(get-unsat-core)`. Map rule IDs in the core back to NL rule statements via the rule-id metadata embedded in `policy.smt2`. Construct a human-readable explanation by templating the violated rules.

7. Return `Decision(allow=allow, unsat_core=rule_ids, explanation=text)`.

**Latency budget:** target sub-200ms per call. The state snapshot is small (typically < 10 entities, < 100 facts). The policy is parsed and cached. Z3 should handle this comfortably for the rule complexity expected. If a particular call exceeds budget, it indicates a rule expressed with too much arithmetic or too many alternations — surface as a performance warning.

## State snapshot extraction

For each write tool, define a "state dependency manifest" — a declarative spec of what to load. Example for `apply_refund`:

```yaml
tool: apply_refund
load:
  - Customer where customer_id = call.parameters.transaction_id.account.customer_id
  - Account where account_id = transaction.account_id
  - Transaction where transaction_id = call.parameters.transaction_id
  - Disputes where customer_id = customer.customer_id and dispute_status in (OPEN, UNDER_REVIEW)
  - Restrictions where account_id = account.account_id
  - GoodwillCreditTotal: sum(refund.amount_pence) where customer_id = customer.customer_id and refund_type = GOODWILL_CREDIT and created_date > now - 365 days
  - ConsumerDutyAssessment where interaction_id = current_interaction.interaction_id (latest)
```

The runtime resolves the manifest into actual DB queries and produces a frozen StateSnapshot. This indirection keeps the validator pure: same inputs always produce same outputs, suitable for caching and for property-based testing.

## Caching

Two layers:

- **Policy parse cache.** `policy.smt2` is parsed once on load; the parsed assertions are reused across every validation. Invalidated only on policy reload.
- **Decision cache.** Hash of `(policy_version, state_snapshot, tool_call)` → `Decision`. Optional. Useful in test runs where the same scenario replays. Disabled in production-like runs to keep behavior live.

## What gets logged

Every validation produces an entry:
- `interaction_id`
- `timestamp`
- `tool_call` (full structured form)
- `state_snapshot` (full materialized form)
- `decision` (ALLOW / BLOCK)
- `unsat_core` (if BLOCK)
- `explanation` (if BLOCK)
- `solver_time_ms`
- `policy_version`

This log is what the demo screencast shows side-by-side with the vanilla run.

## Handling deferred categories

Two categories of validation are explicitly out of scope for v1:

1. **Epistemic legality** (claim grounding). Whether the agent's natural-language messages contain claims unsupported by state. The fabrication detector in the agent-interactions spec is the v2 hook for this.
2. **Cross-turn coherence.** Whether the agent's behavior across turns within an interaction is consistent (e.g., promised X in turn 3, then did Y in turn 5). The audit log captures the data needed for v2 here.

Both are recorded in the audit log even though they aren't enforced.

## Vanilla comparison run

To generate the demo metric "vanilla violated N rules, runtime violated 0":

1. Run all scripted scenarios with vanilla LLM (system prompt = role + full policy text).
2. After each scenario, run the validator over every tool call the vanilla agent attempted, **as if** the runtime had been active. Count blocked calls.
3. Run all scripted scenarios with runtime-gated LLM. Count blocked calls (these are the calls the agent attempted but the runtime blocked, before they hit the DB).

Vanilla typically attempts more illegal calls because nothing prevents it. Runtime-gated typically attempts fewer because the agent learns from the blocks within the interaction. Both metrics matter and both are reported.

## Deliverables for Cursor to implement

1. Solver wrapper around Z3 (Python bindings) with the parse-cache + per-call push/pop pattern.
2. State snapshot extractor (driven by the YAML manifests; one manifest per write tool).
3. Translator from StateSnapshot dict → SMT-LIB ground assertions.
4. Translator from ToolCall dict → SMT-LIB call term.
5. Unsat core extractor + rule-ID-to-NL mapper.
6. Pre-deployment consistency checker as a CLI: `validate-policy policy.smt2 → consistency_report.json`.
7. Per-action validator as a Python module: `from validator import validate_call`.
8. Decision logger.
9. Vanilla-comparison batch runner.

## What this spec does NOT specify

- The NL→SMT-LIB pipeline itself (you have it).
- The exact SMT-LIB encoding choice for each entity type (uninterpreted sort vs. enumeration vs. integer ID — leave to the pipeline).
- The LLM provider (any tool-calling-capable model works).
- The hosting / deployment story (this is a portfolio simulation, runs locally).
