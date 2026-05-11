# Project Specification

A generalist pipeline for converting natural-language policy rules into a verified CPMpy constraint model, with a runtime that gates structured tool calls against the model and current state.

The pipeline is the product. Domains (refund policies, agent guardrails, scheduling, rostering, allocation, anything else expressible in CPMpy) are downstream consumers. The scope target is **the full CPMpy expressivity surface**: scalar and vector variables, global constraints, nested helpers, optimization objectives.

This spec describes the pipeline, its verification suite, and its runtime. Cursor produces a dev plan from this and implements it incrementally.

Throughout the document, **CONFLICT** callouts mark places where the full-CPMpy scope creates a tradeoff against an earlier project principle. These are tradeoffs we're explicitly accepting; Cursor must implement the marked alternative behavior, not the simpler version.

---

## 1. High-level architecture

Six components, organized into three phases:

**Phase 1 — Formalization** (offline, run once per policy version)
- Formalizer: LLM-based, generates CPMpy Python from NL rules one at a time, against a shared signature.
- AST validator: programmatic, ensures generated code uses only whitelisted CPMpy constructs.
- Verification suite: programmatic + LLM-assisted, confirms semantic equivalence to the NL.

**Phase 2 — Consistency check** (offline, run once after formalization)
- Pre-deployment verifier: programmatic, confirms the assembled model is satisfiable, non-trivial, and reachable.

**Phase 3 — Runtime gating** (online, per tool call)
- Validator: programmatic, given a proposed structured tool call and a state snapshot, returns ALLOW / BLOCK with audit trail.

The orchestrator that drives all phases is a deterministic Python state machine, not an agent framework.

---

## 2. Inputs to the pipeline

For each new policy domain, the user provides:

1. **Signature file** (`signature.py`) — typed vocabulary the policy operates over. See the separate signature template artifact.
2. **Glossary file** (`glossary.md`) — NL descriptions of each declared symbol, including derived helpers and global-constraint usage conventions.
3. **NL rules file** (`rules.txt`) — one rule per line, decidable scope (no temporal logic, no unbounded quantification, no implicit world knowledge).
4. **Tool schema** (`tools.json`) — the gated tool calls with parameter names and types.
5. **Test fixtures** (`fixtures/`) — per-rule expected (state, call, decision) triples, authored by the user.

If any input is missing or malformed, the pipeline halts at the relevant stage and reports what's needed.

---

## 3. The Formalizer

**Role:** translate one NL rule at a time into a CPMpy Python expression.

**Input per call:** a single NL rule, the full signature, the full glossary, and a small set of few-shot examples drawn from previously-verified rules in the same domain (or a default seed set).

**Output per call:**
- A Python source string containing exactly one named CPMpy boolean expression assigned to `rule_<n>`.
- A `used_symbols` list explicitly enumerating which signature symbols the rule references.
- A `uses_global_constraints` boolean flag indicating whether the rule uses any CPMpy global constraint (`AllDifferent`, `Cumulative`, `Element`, `Circuit`, `Table`, `Regular`, etc.). Used by the verification suite to route to appropriate checks.
- A `uses_vector_variables` boolean flag indicating whether the rule references any signature symbol declared with `shape=`. Same routing purpose.

**Disallowed:** new symbols not in the signature; imports beyond `cpmpy as cp` and the signature's declared imports; control flow constructs (`if`, `while`, `for` in the *rule body*); function definitions; mutation; classes; lambdas. Quantification over signature-declared collections via comprehensions is **allowed** (see below).

**Comprehension policy.** List/generator comprehensions over collections that are explicitly declared in the signature (e.g., a vector of nurse IDs declared with `shape=(num_nurses,)`) are permitted. The AST validator must check that any comprehension's iterable is a signature-declared collection or a Python literal range with bounds drawn from the signature, never an unbounded or external iterable.

> **CONFLICT — control flow allowance.** The earlier "no control flow" rule was absolute. Full CPMpy scope requires comprehensions for anything operating over a vector. We narrow the rule: control flow that *constructs constraints* is allowed (comprehensions, vectorized operations); control flow that *executes during evaluation* (loops with side effects, early returns, exceptions) remains banned. AST validator must distinguish these.

**Single LLM call per rule.** Failures handled by the orchestrator's repair loop.

---

## 4. The AST validator

**Role:** programmatically check that formalizer output is valid Python and lies within the allowlisted CPMpy subset.

**Steps per validation:**

1. `ast.parse` the source. Reject on syntax error.
2. Walk the AST. Build inventories of: referenced names, imports, node types, comprehension iterables, function calls.
3. Check imports against the signature's allowlist (Section 1 of `signature.py`).
4. Check node types against the allowlist:
   - Always allowed: `Module`, `Assign`, `Name`, `Attribute`, `BinOp`, `BoolOp`, `Compare`, `UnaryOp`, `Constant`, `Tuple`, `List`, `Subscript`, `Call`, `keyword`, `Index`, `Slice`, `ExtSlice`.
   - Allowed in restricted form: `ListComp`, `GeneratorExp`, `SetComp`, `DictComp` — but only when the iterable is a signature-declared collection or a literal `range(...)` with constant bounds. Reject if the iterable is anything else.
   - Always rejected: `For`, `While`, `If`, `IfExp`, `FunctionDef`, `AsyncFunctionDef`, `Lambda`, `ClassDef`, `Try`, `With`, `Yield`, `Return`, `Global`, `Nonlocal`, `Import` (other than top-level imports already validated in step 3), `AugAssign`, `AnnAssign`, `Delete`, `Raise`, `Assert`.
5. Check that every referenced name is one of:
   - A CPMpy primitive in the allowed set (see step 6).
   - A signature-declared symbol from Sections 2–5 of `signature.py`.
   - A Python literal.
   - A comprehension-bound variable (validated in step 4).
6. Maintain a CPMpy-API allowlist enumerating the permitted constructors and functions:
   - Variable constructors: `cp.intvar`, `cp.boolvar`, `cp.cpm_array`.
   - Operators (already covered as AST nodes): `+`, `-`, `*`, `//`, `%`, `==`, `!=`, `<`, `<=`, `>`, `>=`, `&`, `|`, `~`, `^`.
   - Logical helpers: `cp.any`, `cp.all`, `cp.sum`, `cp.min`, `cp.max`, `cp.abs`.
   - Reification: `.implies(...)` method.
   - Global constraints: `cp.AllDifferent`, `cp.AllDifferentExcept0`, `cp.AllEqual`, `cp.Circuit`, `cp.Cumulative`, `cp.Element`, `cp.GlobalCardinalityCount`, `cp.IfThenElse`, `cp.InDomain`, `cp.Inverse`, `cp.Regular`, `cp.Table`, `cp.NegativeTable`, `cp.ShortTable`, `cp.Xor`, `cp.Increasing`, `cp.Decreasing`, `cp.LexLess`, `cp.LexLessEq`.
   - The list is exhaustive for v1; new constructs require an update to the allowlist.
7. Cross-check the formalizer's `used_symbols` list against the AST's actual symbol references. Reject on mismatch.
8. Verify the `uses_global_constraints` and `uses_vector_variables` flags match the AST. Reject on mismatch.

> **CONFLICT — AST validator complexity.** The earlier spec sized the validator at ~150 lines. Full CPMpy scope (with global constraints, comprehensions, `cpm_array` indexing, vectorized ops) brings it to roughly 400-600 lines. Most of the additional code is the CPMpy-API allowlist enforcement and the comprehension iterable check. Cursor should treat the AST validator as the project's security boundary and write substantial adversarial test coverage for it.

---

## 5. The Verification Suite

Three tiers of checks. Each rule is routed to the appropriate tier based on its formalizer-emitted flags.

### 5.1 Per-rule cheap checks (run after every formalization)

**5.1.1 Direct ground-state evaluation.** For each test fixture (state, expected_truth_value), substitute concrete state values into the CPMpy expression and obtain a Python boolean. Compare to expected.

> **CONFLICT — direct evaluation does not work for global constraints.** When `uses_global_constraints=True`, the rule cannot be evaluated by direct substitution because globals are decomposed at solve time, not evaluated as Python booleans. For these rules, replace direct evaluation with **assumption-based satisfiability check**: build a one-rule `Model` with the rule, add the state as ground assertions, add the expected outcome as an assumption, call `solve()`. Match (SAT/UNSAT) confirms or refutes. Slower than direct eval (tens of ms vs sub-ms), still much cheaper than the medium-tier checks.

The verification suite must implement both paths and route based on `uses_global_constraints`. Same for `uses_vector_variables`: vector-valued rules whose evaluation produces an array of booleans must be aggregated (e.g., via `cp.all(...)`) before comparison; the suite handles this transparently when fixtures provide expected aggregate truth values.

**5.1.2 Symbol-use sanity.** Confirm the rule's AST references the signature symbols its NL claimed to reference (via the formalizer's `claimed_dependencies` output). Catches "rule that compiles but checks the wrong field."

**5.1.3 Non-triviality check.** Build a Model with only this rule. If `Model([rule]).solve()` returns SAT *and* `Model([~rule]).solve()` returns SAT, the rule is non-trivial. If either is UNSAT, the rule is trivially true or trivially false; reject.

> **CONFLICT — non-triviality check for vector rules.** When the rule produces a vector of booleans rather than a single boolean (e.g., a constraint over an entire `shifts` matrix), the negation is over the conjunction. The check still works mathematically but the implementation must handle the aggregation. Use `Model([cp.all(rule)])` and `Model([cp.any(~rule)])` for the two satisfiability checks.

These checks should complete in tens to hundreds of ms per rule (was sub-second; full scope makes some checks slower).

### 5.2 Per-batch medium checks (run every 5–10 rules)

**5.2.1 Property-based testing via Hypothesis.** Generate random states drawn from the signature's declared variable domains. For vector variables, Hypothesis generates arrays of the declared shape. Assert each rule evaluates as expected against user-defined property predicates.

> **CONFLICT — Hypothesis state generation for vectors.** State generation for vector variables can produce very large state spaces. Domain operators must declare reasonable test-time shape bounds in the signature (separate from the model's nominal shape) when the nominal shape is too large to test exhaustively. The pipeline reads test-time shape bounds from a `TEST_SHAPE_BOUNDS` dict in the signature, defaulting to nominal shape if absent.

**5.2.2 Mutation testing.** Take a state where the rule evaluates True. Mutate one signature field at a time. Compare against expected dependencies.

> **CONFLICT — mutation for vector fields.** Mutating one element of a vector field is a smaller perturbation than mutating the whole field. The mutation tester must support both element-level and field-level mutations, configurable per fixture.

**5.2.3 Cumulative consistency.** Build a Model from all rules verified so far. Confirm satisfiability. UNSAT means the latest batch contradicts prior rules.

### 5.3 End-of-policy full checks (run after all rules formalized)

**5.3.1 Roundtrip equivalence.** Back-translate each formalized rule to NL via LLM, re-formalize, check equivalence. Equivalence check is `Model([orig != reform]).solve()`; UNSAT means equivalent.

> **CONFLICT — roundtrip drift is harder for vector and global rules.** Back-translating a rule like `cp.AllDifferent(shifts[:, day])` into NL introduces ambiguity ("all nurses must work different shifts on a given day" — but which day? Each day, or some specific day?). The roundtrip check is still valid (the equivalence test is symbolic, not NL-based), but the *failure rate* is expected to be higher for these rules. The diagnoser LLM must be able to recognize "ambiguous back-translation" as a failure mode distinct from "drift," and the repair operator should attempt re-back-translation with stricter NL templates before regenerating from scratch.

**5.3.2 Full pre-deployment consistency check.** See Section 6.

**5.3.3 Coverage check.** For each tool, confirm at least one state exists where the tool is legal and at least one where it's illegal under the model.

---

## 6. Pre-deployment consistency check

Run once after the full policy is formalized and verified.

1. **Satisfiability.** `Model(all_rules).solve()` must return SAT. UNSAT means policy-level contradiction; surface unsat core.
2. **Per-rule reachability.** For each rule, check there exists a state where the rule's antecedent is satisfied. Unreachable rules are dead code (warning).
3. **Pairwise interaction (optional, expensive).** For each pair of rules sharing symbols, check whether a state exists where both fire and produce contradictory verdicts. CI-only, not on every load.

Output: `consistency_report.json`.

---

## 7. The Runtime (Patterns A + B)

### 7.1 Pattern A — fast evaluation path (default for scalar, non-global rules)

For every gated tool call:
1. Take the proposed call and the state snapshot.
2. For each rule that doesn't set `uses_global_constraints` or `uses_vector_variables`, substitute concrete values and evaluate as a Python boolean.
3. Collect violated rules (False evaluations). Any → BLOCK with violation list. None → continue.
4. Latency target: under 10ms for the scalar/non-global subset.

> **CONFLICT — Pattern A cannot handle global constraints or vector-aggregated rules.** Rules with `uses_global_constraints=True` or `uses_vector_variables=True` must be routed to Pattern B for evaluation. This is enforced by the runtime: the rule's metadata tells the runtime which path to take.

### 7.2 Pattern B — SAT path

Used for:
- Rules with `uses_global_constraints=True` (always).
- Rules with `uses_vector_variables=True` (always).
- Pre-deployment consistency check.
- Debug mode requesting true minimal unsat core.
- Pattern A inconclusive cases (should not happen, but logged if it does).

Procedure:
1. Build CPMpy Model from policy with assumption literals per rule.
2. Add ground assertions for state and proposed call.
3. Add `~legal(state, call)` as the negated query.
4. `solve()` under assumptions. UNSAT → ALLOW. SAT → BLOCK with assumption literals in unsat core mapped to rule IDs.

Latency: tens to hundreds of ms.

> **CONFLICT — runtime now has two latency profiles.** Documentation, monitoring, and any SLA framing must distinguish "scalar/non-global rules: <10ms" from "vector or global rules: tens of ms." The audit log records `pattern_used` per call so latency can be analyzed by path.

### 7.3 State snapshot extraction

Each gated tool has a state-dependency manifest declaring which signature fields it depends on. The runtime materializes those fields from the live state source at validation time.

> **CONFLICT — extraction for vector fields.** When a tool depends on a vector field, the manifest entry must specify whether the full vector is needed or a slice. The state extractor supports both. Schema for manifest entries:
> ```python
> "<tool_name>": [
>     "<scalar_symbol>",
>     {"name": "<vector_symbol>", "slice": "full"},
>     {"name": "<another_vector>", "slice": "by_index", "index_param": "<call_param_name>"},
> ]
> ```
> Slice modes: `full` (whole array), `by_index` (single element indexed by a call parameter), `by_range` (range slice with bounds from call parameters). New slice modes added by extending the manifest schema.

### 7.4 Decision shape

```python
@dataclass(frozen=True)
class Decision:
    allow: bool
    violated_rules: list[str]
    pattern_used: Literal["A", "B"]
    explanation: str
    solver_time_ms: float
```

### 7.5 Audit log

Every decision logged with: `policy_version`, `tool_call`, `state_snapshot`, `decision`, `rules_consulted`, `pattern_used`, `solver_time_ms`, `flags_for_routing` (uses_globals, uses_vectors).

---

## 8. The Orchestrator

Deterministic Python state machine.

States:

1. `LOAD_INPUTS`
2. `FORMALIZE` — per rule: invoke formalizer, run AST validator, run per-rule cheap checks (routed by flags).
3. `BATCH_VERIFY` — every N rules.
4. `FULL_VERIFY` — after all rules.
5. `CONSISTENCY_CHECK`.
6. `EMIT_POLICY` — write `policy.py`, `manifest.json`, `consistency_report.json`.
7. `RUNTIME_READY`.

`REPAIR` sub-state: gather diagnostics, invoke diagnoser LLM, choose repair strategy, retry up to N times, escalate to human on final failure.

> **CONFLICT — manifest.json must include rule flags.** Each rule entry now includes `uses_global_constraints` and `uses_vector_variables` so the runtime can route to A vs B without re-parsing the rule.

---

## 9. LLM roles

1. **Formalizer LLM** — generates CPMpy Python (now including global constraints and comprehensions when appropriate). Required.
2. **Back-translator LLM** — formalized expression → NL paraphrase. Required.
3. **Diagnoser LLM** — given two NL versions and the formal expression, classifies which stage drifted. Required.
4. **Test-case generator LLM** — proposes ground-state fixtures (now including vector states for vector-using rules). Optional, output reviewed by human.

> **CONFLICT — formalizer prompt must demonstrate global-constraint and vector usage.** The few-shot examples shown to the formalizer must include examples of `AllDifferent`, vector indexing, and comprehensions over signature collections. Without these examples the formalizer will under-use full CPMpy expressivity even when it would be appropriate. Cursor should produce the prompts artifact with this in mind.

Prompts are out of scope for this spec; produced separately.

---

## 10. Outputs of the pipeline

- `policy.py` — verified CPMpy module, importable.
- `manifest.json` — rule IDs, NL→formal mapping, dependencies per rule, **routing flags per rule**, formalizer/verifier metadata, policy version hash.
- `consistency_report.json`.
- `verification_log.jsonl`.

---

## 11. Tech stack

- Python 3.11+
- CPMpy (latest stable)
- Solvers: OR-Tools (default), Z3 (for assumption-based unsat core extraction)
- Hypothesis for property-based testing
- Pydantic for input validation
- One LLM SDK behind an interface
- pytest

No agent frameworks.

---

## 12. File layout

```
project/
  pipeline/
    orchestrator.py
    formalizer.py
    ast_validator.py
    verification/
      cheap_checks.py        # implements both direct-eval and assumption-SAT paths
      medium_checks.py
      full_checks.py
      hypothesis_generators.py  # supports vector state generation
      mutation.py            # supports element-level and field-level mutation
      roundtrip.py
    consistency.py
    repair.py
    diagnoser.py
  runtime/
    pattern_a.py             # scalar/non-global path
    pattern_b.py             # SAT path with global/vector support
    router.py                # routes rules to A vs B based on flags
    state_extractor.py       # supports scalar, vector-full, vector-slice
    audit_log.py
    decision.py
  llm/
    interface.py
    anthropic_client.py
    prompts/
  domains/
    refund_example/
      signature.py
      glossary.md
      rules.txt
      tools.json
      fixtures/
  tests/
    test_ast_validator.py    # extensive adversarial coverage
    test_pattern_a.py
    test_pattern_b.py
    test_router.py           # routing-decision tests
    test_orchestrator_states.py
  cli.py
  README.md
```

---

## 13. Build order recommendation for Cursor

Vertical-slice order, smallest end-to-end first. Adjusted for full scope:

1. **Slice 1: AST validator (basic) + Pattern A runtime + one hand-written scalar policy**, no globals, no vectors, no LLM. ~1 day.
2. **Slice 2: Add formalizer LLM + per-rule cheap checks for the scalar subset**. ~1 day.
3. **Slice 3: Add the orchestrator state machine + repair loop**. ~1 day.
4. **Slice 4: Add Pattern B + router + assumption-SAT cheap checks for global constraints**. Now formalize a policy with at least one `AllDifferent` rule. ~1.5 days.
5. **Slice 5: Add vector variable support — signature, AST validator extensions, state extractor with slice modes, Hypothesis vector generation, mutation extensions**. ~1.5 days.
6. **Slice 6: Add medium and full verification checks (Hypothesis, mutation, roundtrip with diagnoser)**. ~1 day.
7. **Slice 7: Add full consistency check + coverage check + audit log + CLI + README + polish**. ~1 day.

Seven to eight days for full-scope v1. Each slice ends with a runnable demo.

---

## 14. Out of scope for v1

- Multi-policy composition (one policy per pipeline run).
- Live policy updates without restart.
- Distributed runtime / horizontal scaling.
- Non-CPMpy formalization targets.
- Web UI for rule authoring.
- Optimization objectives in the runtime path (the pipeline accepts policies with objectives but the runtime treats them as satisfaction problems for gating; objectives are for offline solve-for-best-action use cases, deferred to v2).
- Anything epistemic (claim grounding, fabrication detection).
- Multi-LLM ensemble formalization.

---

## 15. Success criteria for v1

1. All NL rules formalize without manual intervention, including rules using global constraints and vector variables.
2. AST validator catches all out-of-allowlist constructs in held-out adversarial test set, including malformed comprehensions, banned imports, and lying-about-globals flag mismatches.
3. Per-rule cheap checks (both direct-eval and assumption-SAT paths) catch all hand-injected drift cases.
4. Roundtrip equivalence agrees on at least 85% of scalar rules and 70% of vector/global rules without repair (lower bar for vector/global because of NL ambiguity, as flagged above).
5. Pre-deployment consistency check correctly identifies inserted contradictions and unreachable rules.
6. Pattern A runtime gates 100% of scalar/non-global test scenarios correctly with sub-10ms latency.
7. Pattern B runtime produces correct minimal unsat cores on global-constraint and vector scenarios.
8. The router correctly directs every rule to its appropriate runtime path; misrouting any rule is a critical failure.
9. The pipeline runs end-to-end on a fresh second domain (covering scalar fields, vector fields, and at least one global constraint) without code changes — only inputs change.

That last criterion is the actual value proposition. Anything less is a domain-specific tool, not a generalist pipeline.

---

## 16. Summary of CONFLICT callouts

For Cursor's reference, here is the full list of places where full-CPMpy scope creates tradeoffs that affect implementation:

1. **§3 — control flow allowance.** Comprehensions allowed when iterating over signature-declared collections; loops with side effects banned.
2. **§4 — AST validator complexity.** Validator grows from ~150 lines to ~400-600 lines.
3. **§5.1.1 — direct evaluation does not work for global constraints.** Cheap-check path forks: direct-eval for scalar/non-global, assumption-SAT for global/vector.
4. **§5.1.3 — non-triviality check for vector rules.** Aggregation needed before satisfiability check.
5. **§5.2.1 — Hypothesis state generation for vectors.** Test-time shape bounds required in signature.
6. **§5.2.2 — mutation for vector fields.** Element-level and field-level both supported.
7. **§5.3.1 — roundtrip drift higher for vector/global rules.** Diagnoser must distinguish ambiguity from drift.
8. **§7.1 — Pattern A cannot handle global constraints or vector-aggregated rules.** Router enforces.
9. **§7.2 — runtime has two latency profiles.** Audit log records `pattern_used`.
10. **§7.3 — extraction for vector fields.** Manifest schema extended with slice modes.
11. **§8 — manifest.json must include rule flags.**
12. **§9 — formalizer prompt must demonstrate global-constraint and vector usage.**

These are not bugs to fix; they are deliberate consequences of the scope decision and Cursor must implement the marked alternative behavior throughout.
