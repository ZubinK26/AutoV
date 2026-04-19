# Implementation dev plan — NL→Z3 control flow v1

**Normative spec:** `dev_plans/control_flow_v1.md`  
**Plain-language companion:** `dev_plans/control_flow_v1_explained.md`  

**Purpose:** Executable roadmap to implement the pipeline **as specified** there. **Non–functionality-compromising** choices (defaults, file layout, exact schema keys) are fixed below so work can start without reopening architecture.

**Commits:** None required by this document; user controls git.

---

## 1. Scope of this implementation

**In scope**

- Pipeline from **accepted `HandoffBundle`** through **formalizer → sandbox → registry agent → validation gate → commit** per `control_flow_v1.md`.
- **OUT_OF_SCOPE** line handling; **partial bundle** commit with `failed_lines`.
- **Deterministic Z3 string extractor** with documented **allowlist** of AST patterns.
- **Programmatic gate** checks 1–5; **validator-owned** ambiguity (re-run `semantic_search`).
- **Persistence** aligned with spec (`registry.json`, `rules.json`, `bundles/{bundle_id}.json` or equivalent under project conventions).
- **Integration** with existing **`registry_stage`** (`SemanticIndex`, `RegistrySession`, embeddings) and **`wfm_orchestration`** (handoff after accept).

**Explicitly out of scope (defer)**

- Merged **multi-line** Z3 theory; **`expect_sat`**; user review UI; labeled **graph edges** on entries; contradiction engine.

---

## 2. Default parameters (implementation may tune; behavior unchanged)

| Parameter | Default | Notes |
|-----------|---------|--------|
| Formalizer repair cap | **3** | Per line, execution-failure path only. |
| Registry agent repair cap | **3** | Per line, after validation failure. |
| Global per-line iteration cap | **10** | Sum of formalizer + registry + validation repair entries that **consume** budget. |
| Sandbox timeout | **30_000** ms | Configurable env / config file. |
| `semantic_search` top_k (agent) | **12** | |
| `semantic_search` top_k (validator) | **12** | Same backend as agent. |
| `similarity_floor` | **0.72** | Cosine; align with embedding scale in tests. |
| Ambiguity `delta` | **0.05** | Top-two scores within this **and** both ≥ floor → require disambiguation fields. |
| Z3 extractor v1 patterns | `DeclareSort`, `Function`, `Const` string first arg | Extend list in one module with comments; add patterns only when formalizer template requires. |

---

## 3. Artifacts and schemas to implement

1. **`FormalizerLineAttempt`** (internal): `line_index`, `z3_code`, `attempt_ix`, `execution_error?`, `z3_check_result?`, `formalizer_attempts` counter.
2. **`RegistryAgentLineAttempt`**: `symbol_bindings` raw JSON, `attempt_ix`, `registry_attempts` counter.
3. **`RegistryAgentOutput` (JSON Schema v1):**  
   - Top-level: `symbol_bindings: array` of objects with fields per spec (`z3_string_literal`, `decision`, `target_entry_id?`, proposed fields for `declare_new`).  
   - Optional: `chosen_from_candidates`, `justify_new_despite_near_duplicate` when ambiguity check applies.  
   - Validate with **jsonschema** (or equivalent) in CI.
4. **`BudgetLog`** per failed or successful line: `formalizer_attempts`, `registry_attempts`, `validation_attempts` (increment validation when gate rejects and triggers registry repair).
5. **`RuleRecord`** / **`BundleRecord`** fields per `control_flow_v1.md` including **`z3_check_result`**, **`symbol_bindings`** snapshot post-validation.

**Single writer:** Process-level **mutex** or **queue** for commit path; document in README for operators. Default single-threaded CLI satisfies spec.

---

## 4. Phases and deliverables

### Phase A — Contracts and pure logic

| Task | Done when |
|------|-----------|
| A1. JSON Schema files for registry agent output | Checked into repo; tests reject invalid fixtures. |
| A2. Rules A–G as pure functions | Unit tests: valid/invalid `canonical_name`, G-then-B ordering. |
| A3. Z3 string extractor | Unit tests on hand-written snippets; extractor ⊆ bindings test. |
| A4. Ambiguity predicate | Given top-k hits + scores, returns whether disambiguation required. |

### Phase B — Sandbox

| Task | Done when |
|------|-----------|
| B1. Subprocess runner | `import z3` only; timeout; capture stdout/stderr; parse `sat`/`unsat`/`unknown` from process **or** structured convention (e.g. last line). |
| B2. Execution vs outcome | **No** repair on clean exit with unsat; repair only on exception/timeout/policy. |

### Phase C — Formalizer service

| Task | Done when |
|------|-----------|
| C1. Prompt template | IN_SCOPE lines; Rules A–G **as prose**; `import z3` style; no registry context. |
| C2. Repair loop | Feed structured errors from B; respect cap; log attempts. |

### Phase D — Registry agent service

| Task | Done when |
|------|-----------|
| D1. Tool bindings | `exact_lookup`, `signature_lookup`, `semantic_search` implemented via **`RegistrySession`** + existing **`SemanticIndex`**. |
| D2. Prompt + schema | Agent must emit **only** JSON matching schema; repair on validation error. |

### Phase E — Validation gate

| Task | Done when |
|------|-----------|
| E1. Checks 1–5 | Integration tests with mock registry + mock embeddings. |
| E2. Ambiguity check 5 | Validator builds deterministic query string; re-invokes search; compares to agent fields. |

### Phase F — Commit

| Task | Done when |
|------|-----------|
| F1. Transactional write | Staged dir + rename **or** write temp + atomic replace per file. |
| F2. Entry CRUD | New entries get embeddings via same `entry_embed_text` / index rebuild policy as `registry_stage`. |
| F3. `members` | **Derive** on read **or** compute once in commit from `parent_sort` — **no** separate dual-write path. |

### Phase G — Orchestration

| Task | Done when |
|------|-----------|
| G1. `run_nl_z3_pipeline(bundle, session, ...)` | Single entry point after WFM accept. |
| G2. Feature flag | e.g. `AUTOV_PIPELINE_MODE=legacy|nl_z3_v1` for migration. |
| G3. Export / `DevSessionSnapshot` | Includes per-line traces, `z3_check_result`, failure categories, budget logs. |

### Phase H — Migration and cleanup

| Task | Done when |
|------|-----------|
| H1. Document coexistence | `pipeline_spec.md` cross-link or short appendix: **legacy** `run_bundle_through_registry` vs **v1** path. |
| H2. Deprecation path | When v1 stable, mark legacy path **deprecated** in code comments. |

---

## 5. Testing strategy (minimum)

- **Unit:** A–G, extractor, ambiguity predicate.
- **Integration:** End-to-end **one** golden bundle: empty registry → commit; **one** line `Z3_FAIL`; **one** line `REGISTRY_AMBIG` (forced by test doubles).
- **Regression:** Clean exit + `unsat` does **not** increment formalizer repair counter.

---

## 6. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| LLM ignores `import z3` convention | Denylist + repair message citing policy; count toward formalizer attempts. |
| Extractor misses literals | Expand allowlist incrementally; formalizer template lists **only** allowed patterns in prompt. |
| Embedding drift vs thresholds | Calibrate `similarity_floor` / `delta` on a **small** labeled set once Phase E exists. |

---

## 7. Definition of done (this dev plan)

- [ ] All phases A–G have exit criteria met.
- [ ] `control_flow_v1.md` behavior is covered by tests or explicitly marked **manual** (e.g. single-writer ops).
- [ ] Operators can run one documented command (or API) from **handoff JSON** to **committed** or **partially_committed** bundle state.

---

## Implementation status (codebase)

| Phase | Status |
|-------|--------|
| A — Naming + extractor + ambiguity math | **Done** (`nl_z3_pipeline/naming_rules.py`, `z3_string_extractor.py`, tests) |
| B — Sandbox | **Done** (`sandbox_runner.py`, reuses `formalizer_stage.z3_runner`) |
| C — Formalizer LLM | **Done** (`formalizer_step.py`, `prompts/formalizer_nl_z3_v1.md`, Gemini with `max_output_tokens`) |
| D — Registry agent | **Done** — **prefetch + single Gemini call** per line (`tool_prefetch.py`, `registry_agent_step.py`). **Not** an unbounded multi-turn tool loop. |
| E — Validation gate | **Done** (`validation_gate.py`) |
| F — Commit | **Done** (`commit.py`, atomic batch `add_or_replace`) |
| G — Orchestration | **Done** (`pipeline.py`, `cli.py`) |
| JSON Schema file | **Pending** — validation is programmatic in Python (same checks); optional JSON Schema file later. |
| Orchestrator `--nl-z3-v1` flag | **Pending** — CLI exists as `python -m nl_z3_pipeline.cli --handoff …`. |

### Token / cost controls (registry + formalizer)

- **Per-call output caps:** `gemini_complete(..., max_output_tokens=...)` — formalizer and registry agent use `NlZ3PipelineConfig.formalizer_max_output_tokens` and `registry_agent_max_output_tokens` (default **8192** each; env `NL_Z3_*` overrides).
- **No open-ended tool loop:** Semantic / exact “tools” run **deterministically** in `tool_prefetch` (bounded `top_k`); the LLM receives **one** user payload with prefetch JSON — **not** repeated tool rounds.
- **Input size:** Z3 code in registry prompt truncated at `max_z3_code_chars_in_prompt` (default **48k** chars).

---

*End of implementation dev plan.*
