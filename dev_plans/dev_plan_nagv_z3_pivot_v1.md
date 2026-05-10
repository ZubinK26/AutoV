# Dev plan: NagV pivot — Z3 Python formalization (replace Nagini)

## 1. Purpose

Pivot **NagV** so the formalizer emits **Z3 Python** (Microsoft `z3` / `z3-solver` API) instead of **Nagini**-annotated Python. Preserve the **same conceptual pipeline** as today:

1. WFM → aggregated NL (unchanged).
2. **Feasibility / execution gate** before semantic critic — *was* Nagini translation; becomes **“Z3 program runs and builds a check we define.”**
3. **Semantic critic** — still NL ↔ formalization alignment (updated prompts for Z3 encodings).
4. **Final verification pass** — *was* Nagini `Verification successful`; becomes **primary satisfiability signal** from Z3 (`sat` / `unsat` / `unknown`) per §5, plus optional analysis (e.g. **minimal unsat core** when `unsat`).

**Explicit non-goal:** Match Nagini’s **proof / VC** strength. Z3 gives **SMT outcomes** on the **encoding** the LLM wrote, not verified Python contracts. Success means “our harness says the generated script completed the scripted check with the expected outcome,” not “Nagini proved all contracts.”

## 2. Why this pivot

- LLMs generate **generic Python + library calls** far more reliably than **Nagini translator quirks**.
- **SAT / UNSAT / UNKNOWN** remains a crisp automation signal comparable in *role* to “verification finished,” even though the *meaning* is encoding-relative.
- **Unsat cores** (with tracked assertions) yield **actionable repair hints** when the policy conjunction is inconsistent or a query is false.

## 3. Conceptual pipeline (unchanged philosophy)

```text
WFM + NL aggregate (unchanged)
    ↓
[Phase A] Formalizer → Python syntax OK (ast) — optional syntax-only repair
    ↓
[Phase B] Z3 FEASIBILITY GATE — generated module loads, builds problem, reaches “check ready”
         (no critic; repair on ImportError, Z3 exceptions, harness protocol violations)
    ↓
[Phase C] SEMANTIC GATE — critic PASS (NL vs Z3 encoding)
    ↓
[Phase D] Z3 VERIFY — run harnessed check() → expect SAT (or scripted expect_unsat for refutation queries)
    ↓ repair with shared solver-repair budget + core excerpts when unsat
success / structured reject outcomes
```

**Ordering:** No critic until Phase B passes (same rule as Nagini-first plan).

**Budgets:** Reuse the existing pattern: **`Z3_REPAIR_CAP`**, **`Z3_REPAIR_FINAL_FLOOR`**, **`SEMANTIC_*`**, **`SYNTAX_INNER_CAP`**, **`Z3_INNER_CAP`** per inner repair loops (names TBD; can alias current `NAGINI_*` constants to `SOLVER_*` in code).

## 4. Formalization contract (what the formalizer must emit)

### 4.1 File shape

- Single **importable Python module** (or single script) defining a **stable entry contract** the harness calls.

**Recommended minimal protocol (implementation choice — pick one and document in `NagV/README`):**

| Option | Pros | Cons |
|--------|------|------|
| **A. `build(ctx) -> None`** mutates a `Solver` + assertion list on `ctx` | Explicit, testable | Needs ctx type |
| **B. `check() -> CheckResult`** dataclass with `status`, `model` optional, `diagnostics` | Clean functional style | LLM must follow schema |
| **C. Module-level `def main():` printing JSON** | Subprocess isolation | Harder to extract cores in-process |

**Recommendation:** **Option B** with a **small typed stub** shipped in-repo (`nagv/z3_harness_types.py` or similar) that the formalizer prompt imports — improves LLM conformance.

### 4.2 Allowed / forbidden (prompt + optional linter)

- **Allow:** `z3` imports, `Solver`, `Bool`, `Int`, `BitVec`, `And`, `Or`, `Not`, `Implies`, `If`, `sat`, `unsat`, `unknown`, quantifiers only if team accepts (prefer **ground / QF** fragments for predictability).
- **Forbid (initially):** network, filesystem outside temp, `subprocess`, `eval` on untrusted strings, unbounded Python loops generating unbounded Z3 variables (soft prompt + timeout).
- **Remove:** all `nagini_contracts`, `@Requires`, `@Ensures`, Nagini-specific rules from formalizer.

### 4.3 “Policy model” semantics

The formalizer encodes **WFM PASS/REWRITE NL** as Z3 variables/constraints. **Truth = sat of conjunction** (or family of checks) **only relative to that encoding**. Document that **soundness of the NL → Z3 step remains LLM + critic**, not a proof assistant.

## 5. Z3 harness and verification signal

### 5.1 Harness responsibilities (`nagv/z3_runner.py` or replace `nagini_runner.py`)

1. **Load** candidate in a **subprocess** or restricted **in-process** import (subprocess preferred for crash isolation — mirror Nagini).
2. **Timeout** wall-clock (reuse `NAGV_Z3_TIMEOUT` / `nagini_timeout` CLI flag or rename to `--solver-timeout`).
3. Call **`check()`** (or equivalent) and map:
   - **Expected `sat`** for “policy constraints satisfiable” baseline, **or**
   - **Scripted battery:** e.g. multiple calls: `check_consistency()` → expect `sat`; `check_query_violation()` → expect `unsat` if NL says “never happens.”

**Phase B (feasibility)** — success if:

- No uncaught exception,
- Solver / variables constructed,
- Optionally: **`check()` returns without error** (or first lightweight `push`/`pop` probe).

**Phase D (verify)** — success if:

- Status matches **expected** outcome for that scenario (default: **`sat`** for merged policy),
- `unknown` → treat as **repair or reject** (config flag).

### 5.2 UNSAT and minimal core

- Enable **`set_param('produce-unsat-cores', True)`** and use **named/assertion tracking** (`Assert` with string names or `solver.assert_and_track`) in the **formalizer prompt template** so cores are meaningful.
- On **`unsat`**, extract **`solver.unsat_core()`** (minimal subset of tracked names) and pass **compact string** into repairer (cap length for API).

### 5.3 SAT model (optional signal)

- On **`sat`**, optionally serialize **small model fragment** (bounded) to `verification_log.txt` for human/debug; avoid dumping huge models into LLM context.

## 6. Pipeline code changes (`NagV/nagv/pipeline.py`)

1. Replace **`run_nagini`** / **`nagini_translation_passed`** with **`run_z3_candidate`** and **`z3_feasibility_passed`** (exact predicates in `z3_runner`).
2. Rename outcome enums for clarity:
   - `rejected_nagini_translation_budget` → **`rejected_z3_feasibility_budget`** (keep legacy string optional for one release if needed).
   - `rejected_nagini_verify_budget` → **`rejected_z3_verify_budget`**.
   - `success` message → **“Z3 check succeeded (expected sat/unsat)”** with detail.
3. **Repair diagnostics:** pass stdout/stderr + **exception chains** + **unsat core** snippets.
4. **Progress JSON:** `schema_version: nagv_progress_v3_z3`, fields `z3_repair_used`, etc.
5. **`nagv_progress.json` / `run_summary.json`:** include `z3_status`, `expected`, `unsat_core_tags` (list of tracked names).

## 7. Agents and prompts

| Artifact | Action |
|----------|--------|
| `prompts/formalizer.md` | Rewrite for **Z3 Python** + **harness `CheckResult` protocol** + tracked assertions + **no Nagini**. |
| `prompts/critic.md` | Audit **NL vs Z3 encoding** (variables match NL entities, operators match boundaries, no invented constraints). Precondition: passed feasibility gate. |
| `prompts/repairer.md` | Split **Z3 traceback / unsat core** vs **critic** diagnostics; narrow ABORT to true NL vs solver impossibility. |
| `nagv/formalizer_agent.py` | Unchanged plumbing except prompt path / optional `load_prompt("formalizer_z3.md")` if you keep old file for reference. |
| `nagv/critic_agent.py` / `repair_agent.py` | Prompt + message text only unless model routing changes. |

## 8. Dependencies and environment

- Add **`z3-solver`** to NagV install path (e.g. `NagV/requirements.txt` or root extras).
- **Remove or make optional:** Nagini exe, `NAGV_NAGINI_EXE`, JVM hints — keep behind **`NAGV_LEGACY_NAGINI=1`** only if dual mode desired; **default off** after pivot.

## 9. CLI / packaging

- Optional rename: `nagv.cli` description **“WFM → Z3 Python → critic → Z3 verify.”**
- Flag **`--nagini-timeout`** → **`--z3-timeout`** (alias old flag for backward compatibility).

## 10. Security and robustness

- **Subprocess** for Z3 run with **resource limits** where OS allows; cap **model printing** size.
- **No** `pickle` / arbitrary `exec` of untrusted blobs from model output beyond the candidate file itself (treat candidate as untrusted code — same as today).

## 11. Testing

- **Unit:** mock `z3_runner` — feasibility pass/fail, unsat core string formatting, budget floor (reuse existing budget tests with renamed imports).
- **Golden:** tiny hand-written `candidate_ok_sat.py` / `candidate_bad_unsat.py` in `NagV/tests/fixtures/` run through harness.
- **Regression:** one e2e dry-run with **stub LLM** optional (future).

## 12. Documentation

- **`NagV/README.md`** (add if missing): Z3 pivot, what “success” means, how to read `verification_log.txt` and unsat cores.
- **`dev_plans/dev_plan_nagv_nagini_before_critic_v1.md`**: superseded **for verification backend** only; WFM + critic ordering ideas remain valid.

## 13. Migration checklist

- [ ] Implement `z3_runner` + harness protocol + subprocess wrapper.
- [ ] Swap pipeline Phases B/D from Nagini to Z3.
- [ ] Rewrite formalizer / critic / repairer prompts.
- [ ] Add `z3-solver` dependency; document platform wheels.
- [ ] Update outcomes, progress schema, CLI flags.
- [ ] Remove or gate Nagini-specific code paths.
- [ ] Tests + one manual run on existing `exports/nagv_runs/*/wfm_handoffs` work dirs.

---

**Status:** Ready for review. Implementation should follow this document section order (harness + protocol first, then pipeline swap, then prompts, then cleanup).
