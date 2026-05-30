# Dev plan: External world tester — provenance fill, blind review, executable Z3 test (v1)

**Status:** Implemented (v1); default executable semantics superseded by **`dev_plan_external_world_tester_v2_global_scenario_v1.md`** (scenario + closed-world defaults)  
**Priority:** P1  
**Prerequisites (recommended):** Compiled policy in `work_dir` (`rules_extracted.json`, `meta_scheme.json`, Z3 sat/unsat baseline). Optional gate: prior Tester + Pivot Critic + CrossCritic clean (operator flag, not hard-coded to any domain).  
**Related:** `dev_plans/dev_plan_executable_test_templates_v1.md`, `dev_plans/dev_plan_pivot_query_templates_and_z3_diagnostics_v1.md`, `dev_plans/dev_plan_cross_repairer_hardening_v1.md`, `dev_plans/dev_plan_pivot_test_repairer_hardening_v1.md`  
**Out of scope (v1):** Domain-specific prompts (CV, recruitment fixtures), prompt-injection benchmark suites, CI fail-on-external-tester, auto-repair of policy IR from external test failures.

---

## 1. Goal (simple terms)

Run **one structured test** against an already-compiled policy where:

1. An **external fill agent** reads an **unstructured text chunk** (plus policy variable catalog) and produces a **complete world assignment** (every policy variable accounted for), **provenance** (line numbers + short quotes), a **query**, and a **golden** (same shapes as today’s template tester).
2. A **provenance reviewer agent** checks each field **only against the cited lines** (blind to the rest of the source) and approves or rejects with reasons.
3. Only after reviewer **PASS** does the pipeline **validate JSON → lower to existing `decision_query` (or `scenario`) → run Z3 → diff → record verdict**.

This is **not** the LLM template *generator* (multi-kind suite from policy context). It is a **single-instance, evidence-first** path from **external text → grounded world → deterministic check**.

---

## 2. Which template to use

| Need | Existing kind | v1 choice |
|------|----------------|-----------|
| Full `world` map + ask “what does rule/variable evaluate to?” | `decision_query` | **Primary** — `world` + `query` + `golden.decision` |
| Full `world` + only “is policy ∧ world satisfiable?” | `scenario` | **Optional** second kind in v1 if query is only SAT |
| Partial world / boundary / counterfactual | others | **Defer** — wrong fit for “fill everything from one doc” |

**Gap today:** `decision_query.world` is a **sparse** map; validation only checks keys **present**, not **completeness**. v1 adds a **separate authoring schema** (`ExternalWorldFillV1`) that requires one record per variable in `meta.variable_sorts`, then **lowers** to a sparse `world` dict for Z3 (see §5).

**Not used for fill:** `rule_attribution`, `obligation_inventory`, `boundary`, `counterfactual_flip`, `pairwise` — pathway/attribution semantics differ from “document → full state.”

---

## 3. End-to-end flow

```mermaid
flowchart TD
  A[Numbered source text chunk] --> B[External fill agent Pro]
  B --> C{Deterministic completeness + schema}
  C -->|fail| B2[Fill repair loop]
  B2 --> B
  C -->|ok| D[Build blind review pack per field]
  D --> E[Provenance reviewer Pro]
  E -->|reject field(s)| B
  E -->|PASS| F[Lower to TemplateInstance]
  F --> G{Pydantic + validate_instance}
  G -->|fail| H[Syntax repairer Flash]
  H --> F
  G -->|ok| I[execute_instance Z3 + diff]
  I --> J[external_tester_run_report.json]
```

**Hard gate:** Z3 runs **only** when `provenance_review.verdict == PASS` and lowered instance validates.

---

## 4. Agents and models

| Role | Prompt file | Default model | Env override |
|------|-------------|---------------|--------------|
| **External fill** | `prompts/external_world_fill.md` | `gemini-3.1-pro-preview` | `PIVOT_EXTERNAL_FILL_GEMINI_MODEL` |
| **Provenance reviewer** | `prompts/external_world_provenance_review.md` | `gemini-3.1-pro-preview` | `PIVOT_EXTERNAL_REVIEW_GEMINI_MODEL` |
| **Syntax / JSON repair** | `prompts/external_world_syntax_repair.md` | `gemini-3-flash-preview` (same as `get_pivot_gemini_model()`) | `PIVOT_EXTERNAL_SYNTAX_REPAIR_GEMINI_MODEL` |

Reuse `pivot_llm_complete` / `gemini_complete` with per-stage model env vars (mirror `llm.py` pattern).

**Thinking level:** default **low** for fill/review (structured JSON); configurable via existing `PIVOT_GEMINI_THINKING_LEVEL` or per-stage env if needed later.

---

## 5. Schemas

### 5.1 Source text envelope (input)

Orchestration **always** supplies numbered lines before any LLM sees the chunk:

```json
{
  "source_id": "opaque-id",
  "line_count": 42,
  "lines": ["line 1 text", "line 2 text", "..."]
}
```

Persist as `external_tester_source.json` (or `.jsonl` one doc). **Provenance line numbers are 1-based** indices into `lines[]`. Multi-line support: `provenance.line_numbers: [3, 4]`.

**CLI:** `--external-source path` (raw text auto-split on `\n`, or pre-numbered JSON).

### 5.2 `ExternalWorldFillV1` (fill agent output)

```json
{
  "schema_version": "1",
  "instance_id": "ext_001",
  "template_kind": "decision_query",
  "query": { "decision_metric": "rule", "rule_id": "R0001" },
  "golden": { "decision": "satisfied" },
  "assignments": [
    {
      "variable": "resume_count",
      "sort": "int",
      "value": 1,
      "status": "present",
      "provenance": {
        "line_numbers": [12],
        "quotes": ["...exact substring..."]
      },
      "rationale": "one sentence"
    },
    {
      "variable": "meets_two_year_customer_operations_experience_requirement",
      "sort": "bool",
      "value": true,
      "status": "inferred",
      "provenance": { "line_numbers": [8, 9], "quotes": ["...", "..."] },
      "rationale": "CV states 3 years in customer support"
    },
    {
      "variable": "salary_expectation",
      "sort": "int",
      "status": "not_found",
      "provenance": { "line_numbers": [], "quotes": [] },
      "rationale": "no compensation mention"
    }
  ]
}
```

**Field rules:**

| Field | Rule |
|-------|------|
| `assignments` | **Exactly one row per** name in `meta.variable_sorts` (sorted); no extras. |
| `status` | `present` \| `inferred` \| `not_found` |
| `value` | Required for `present` and `inferred` (`int` or `bool` per sort); **omitted** for `not_found` |
| `provenance.line_numbers` | Required for `present`/`inferred` (≥1); empty only for `not_found` |
| `provenance.quotes` | Verbatim excerpts; server may truncate in reviewer pack (cap chars) |
| `golden` | Same enums as `template_suite` (`satisfied` / `unsatisfied` for `decision_query`; boolean `sat` for `scenario`) |

**Prompt tone (fill agent):**

- Must cite line numbers for every non–`not_found` value.
- **Allowed:** reasonable `inferred` from explicit evidence (e.g. dates → tenure bool).
- **Forbidden:** refusing inference when ordinary reading of cited lines supports it; inventing values with no cited basis.
- **Explicit `not_found`** preferred over silent omission.

### 5.3 `ExternalProvenanceReviewV1` (reviewer output)

```json
{
  "schema_version": "1",
  "verdict": "PASS",
  "field_reviews": [
    {
      "variable": "resume_count",
      "verdict": "supported",
      "notes": "line 12 states one-page resume"
    }
  ],
  "blocking_variables": []
}
```

Per-field `verdict`: `supported` \| `unsupported` \| `derivable` \| `not_applicable` (only for `not_found`).

**Overall `verdict`:** `PASS` only if every `present`/`inferred` field is `supported` or `derivable`, and no `unsupported`. Any `unsupported` → `FAIL` + `blocking_variables`.

**Blind review pack (server-built, not LLM):** For each assignment, reviewer user message contains **only**:

- variable name, claimed value, status, rationale
- **Quoted line blocks** for cited line numbers (extracted from `lines[]` by index)
- **No** full document, no uncited lines, no policy IR, no golden (reviewer should not tune golden to match Z3)

Optional second pass: reviewer may see **sort** + **variable description** one-liner from `variable_sorts` / rules excerpt (no NL policy wall).

### 5.4 Lowering to executable instance

```python
world = {
  a.variable: a.value
  for a in assignments
  if a.status in ("present", "inferred") and a.value is not None
}
# → DecisionQueryInstance(instance_id=..., world=world, query=..., golden=...)
```

**Semantics of `not_found`:** Variable **not asserted** in Z3 world (solver free). Document in report: `world_coverage: { "asserted": N, "omitted": M, "total": T }`. Golden still author’s prediction under their intended reading (may be wrong — that’s the test).

**Future (out of v1):** Policy-level defaults for `not_found`; or require explicit sentinel int/bool.

---

## 6. Preconditions on `MetaScheme`

1. **`variable_sorts` must be non-empty** before external tester runs. If compile left sorts empty, run a small **sort harvest** pass (scan rules IR for variable names + bool/int inference) and write `meta_scheme.json` / sidecar `variable_catalog.json`.
2. **Variable catalog in fill prompt:** sorted list `{ name, sort, optional_hint }` from sorts + optional first mention in `synthetic_en.md` (truncated).
3. **Query `rule_id`:** must exist in active rules; validate in `validate_instance`.

---

## 7. Repair loops (mirror existing pivot style)

### 7.1 API 503 / transient errors

| Stage | Behavior |
|-------|----------|
| Fill / Review | **Unlimited auto-retry** when `PIVOT_EXTERNAL_TESTER_API_AUTO_RETRIES=0` (default), no prompt; sleep/backoff optional P2 |
| Interactive | Same pattern as `cross_critic_interactive_loop`: optional `retry` prompt if auto cap set |

Env: `PIVOT_EXTERNAL_TESTER_API_AUTO_RETRIES` (default `0` = unlimited).

### 7.2 Fill agent loop (reviewer or deterministic rejection)

| Trigger | Action |
|---------|--------|
| Pydantic / completeness (“missing variable X”) | Re-prompt fill with **structured error list**; cap `PIVOT_EXTERNAL_FILL_MAX_ROUNDS` (default 5) |
| Reviewer `FAIL` | Re-prompt fill with **only** `blocking_variables` + per-field reviewer notes (no full doc re-send unless round 1) |
| Stall | Same fingerprint 2× → stop with `blocked_external_fill_stall` (reuse stall helper pattern from semantic repair) |

### 7.3 Syntax repair loop (post-review, pre-Z3)

| Trigger | Action |
|---------|--------|
| `TemplateSuiteFile` / instance validation fails after lower | **Flash** syntax repairer: invalid JSON or Pydantic errors + truncated invalid blob |
| Cap | `PIVOT_EXTERNAL_SYNTAX_REPAIR_MAX` (default 3) |

Reviewer **does not** re-run on syntax-only fixes unless lower changes values (it shouldn’t).

### 7.4 Reviewer loop

| Trigger | Action |
|---------|--------|
| Reviewer JSON parse fail | Flash JSON repair **or** re-call reviewer (cap `PIVOT_EXTERNAL_REVIEW_MAX_ROUNDS`, default 3) |
| Reviewer 503 | Same API auto-retry as fill |

**No IR/policy repair** in v1 — only fill ↔ review ↔ syntax.

---

## 8. Artifacts (`work_dir`)

| File | Content |
|------|---------|
| `external_tester_source.json` | Numbered source envelope |
| `external_world_fill.json` | Last accepted fill payload |
| `external_world_fill_raw.txt` | Raw LLM fill |
| `external_provenance_review.json` | Reviewer verdict |
| `external_provenance_review_raw.txt` | Raw reviewer |
| `external_tester_instance.json` | Lowered `DecisionQueryInstance` (or scenario) |
| `external_tester_run_report.json` | Z3 actual, golden, diff, verdict, coverage stats |
| `external_tester_trace.jsonl` | Round-by-round: fill, review, syntax, execute |

---

## 9. Package layout

Under `NagV/pivot_pipeline/`:

| Module | Responsibility |
|--------|----------------|
| `external_tester/schemas.py` | Pydantic: source, fill, review |
| `external_tester/source_numbering.py` | Raw text → numbered envelope |
| `external_tester/variable_catalog.py` | Build catalog from `MetaScheme` + optional hints |
| `external_tester/fill_agent.py` | Fill LLM + rounds + 503 retry |
| `external_tester/review_pack.py` | Build blind line slices per assignment |
| `external_tester/review_agent.py` | Reviewer LLM + rounds |
| `external_tester/completeness.py` | Deterministic: all variables, sorts, quotes non-empty |
| `external_tester/lower.py` | Fill → `DecisionQueryInstance` |
| `external_tester/syntax_repair_agent.py` | Flash repair lowered instance JSON |
| `external_tester/run.py` | Orchestrate gates → `execute_instance` + `diff` |
| `external_tester/interactive_loop.py` | Optional operator gate after review FAIL (PROCEED / RETRY) |

**Prompts:** `prompts/external_world_fill.md`, `prompts/external_world_provenance_review.md`, `prompts/external_world_syntax_repair.md`

**CLI** (`cli.py` flags):

- `--with-external-tester`
- `--external-source PATH`
- `--external-instance-id ext_001` (optional)
- `--require-prior-critics` (optional: fail fast if `cross_critic_report` / critic not PASS)
- `--external-query-rule R0001` (optional override; else fill agent picks from prompt)

**Pipeline hook:** New step **after** template suite (step 8) or **standalone** subcommand `python -m pivot_pipeline.external_tester.run --work-dir ...` so large policies can run without re-running extract.

---

## 10. Implementation phases

### Phase 0 — Variable catalog + sorts

- [ ] Implement `populate_variable_sorts(meta, rules)` if missing; persist into `meta_scheme.json`.
- [ ] `variable_catalog.json` generator for prompts.
- [ ] Tests: harvest picks up bool/int from sample rules.

### Phase 1 — Schemas + deterministic gates

- [ ] Pydantic models §5.1–5.3.
- [ ] `completeness.check(fill, meta)` — every sort key present, value/sort consistency.
- [ ] `review_pack.build(source, fill)` — blind slices only.
- [ ] Tests: completeness failures; pack excludes uncited lines.

### Phase 2 — Fill agent

- [ ] `fill_agent.run` + prompt + context builder (catalog + query template stub).
- [ ] 503 auto-retry; max rounds; trace jsonl.
- [ ] Tests: mocked LLM golden fill parses; retry on missing variable.

### Phase 3 — Provenance reviewer

- [ ] `review_agent.run` — blind pack only in user message.
- [ ] Aggregate PASS/FAIL; blocking_variables back to fill.
- [ ] Tests: mocked reviewer FAIL triggers fill re-prompt; PASS does not include full source in prompt (assert on fixture).

### Phase 4 — Lower + syntax repair + Z3

- [ ] `lower.to_decision_query(fill)`.
- [ ] Syntax repairer (flash) on validation errors.
- [ ] Reuse `template_suite.execute_instance` + `diff.compare`.
- [ ] `external_tester_run_report.json` with `world_coverage`, `provenance_review_verdict`.
- [ ] Tests: lowered world executes against toy `MetaScheme`; diff pass/fail.

### Phase 5 — CLI + `run.py` hook + docs

- [ ] Wire flags; optional `--require-prior-critics`.
- [ ] `NagV/pivot_pipeline/README.md` section: External world tester.
- [ ] `PIVOT_TEMPLATE_SYSTEM.md` cross-link: when to use generator vs external tester.

### Phase 6 — Interactive operator gate (optional v1.1)

- [ ] After review FAIL: `RETRY_FILL` / `PROCEED_ANYWAY` (default deny Z3) — mirror cross gate tokens.

---

## 11. Success criteria (v1 done)

- [ ] Given numbered source text + compiled `work_dir`, pipeline produces fill → review PASS → Z3 run → report **without manual JSON editing**.
- [ ] Fill output includes **all** `variable_sorts` keys with `status` + provenance rules enforced.
- [ ] Reviewer prompt contains **only** cited line blocks (verified in test).
- [ ] Reviewer FAIL re-invokes fill with structured feedback; 503 does not consume fill/review round counters.
- [ ] Syntax errors repaired by **flash** model or fail with clear stage in trace.
- [ ] Domain-agnostic: no CV/recruitment strings in code or prompts (examples in dev plan only).

---

## 12. Open decisions (defaults chosen for v1)

| Question | v1 default |
|----------|------------|
| Who picks `query.rule_id`? | Fill agent from prompt + catalog; CLI override optional |
| `not_found` in Z3 | Omit from `world` (unconstrained) |
| Reviewer sees golden? | **No** |
| Multiple external instances per run? | **One** per invocation; batch = later |
| Fail pipeline on external test `fail`? | **No** — record in `run_summary.json`; optional `--fail-on-external-tester` P2 |
| inconclusive Z3 | Keep first-class; **do not** map to unsat |

---

## 13. Testing strategy

| Layer | Tests |
|-------|--------|
| Unit | completeness, review_pack blinding, lower, sort harvest |
| Integration | mocked Pro fill + Pro review → execute on fixture policy |
| Regression | Hand-authored `external_world_fill.json` + source fixture → deterministic Z3 verdict (no LLM) |

---

## 14. Non-goals / follow-ups (P2+)

- Multi-instance suites from one document.
- `scenario` + multi-query bundles.
- Golden auto-refresh from Z3 actuals.
- Prompt-injection corpora and domain eval metrics.
- Pathway-scoped worlds (partial pathway activation instead of global AND).
- Reviewer model distillation or dual-review consensus.

---

## 15. Relation to existing “three critics”

External tester is a **fourth check** orthogonal to Tester/Critic/CrossCritic:

| Layer | What it validates |
|-------|-------------------|
| Tester / Critic / Cross | Policy IR ↔ NL / synthetic / cross wiring |
| Template generator | Policy self-consistency on LLM-authored worlds |
| **External tester** | External evidence → grounded world → policy query under Z3 |

Recommended operator order: critics clean → optional template suite → **external tester** with live document.

---

*End of plan.*
