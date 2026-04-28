# Dev plan — Pivot to WFM → ClinCon / ASP (`asp_pipeline`)

**Branch / product line:** `ClinCon-version` (and descendants).  
**Normative product spec:** [`asp/pipeline_wfm_to_asp.md`](../asp/pipeline_wfm_to_asp.md) — step contracts, prompts, repair budgets, verification, CLI. This document is the **engineering plan** to reach that spec starting from the existing **WFM → `smt_pipeline`** codebase.

**Principle:** Reuse everything that is already correct (handoff schema, orchestration entrypoints, Gemini wiring, batch pacing, bundle records, atomic commit patterns). Replace the **formalization vertical** (SMT-LIB + Z3 in-loop) with **ClinCon / Clingo `.lp`** + **parse/ground** checks + **answer-set** verification.

---

## 1. Goals

1. **Single handoff path:** `HandoffBundle` JSON → `asp_pipeline` → committed `policy_model.lp` (or per-bundle `.lp`), with the same **failure categories**, **bundle JSON sidecars**, and **log.jsonl** shape as today’s SMT path (where the spec says “carried over unchanged”).
2. **ClinCon-safe fragment** as the only target language for in-scope lines; Agent 3 enforces fragment boundaries and **rich `scope_report`** strings for violations.
3. **Clingo** as the oracle for syntax (`--parse-only`) and grounding (`--ground`), with **shared** `parse_ground_repair_cap` and **separate** `semantic_repair_cap` (per product spec).
4. **Policy verification** via answer-set existence + minimal unsat-style cores using `#external` / `--assume` (per product spec).
5. **Batch runners** mirroring `smt_pipeline.run_wfm_handoff_batch` and `run_policy_batch_check`, targeting `bundles/asp_from_wfm/`.

## 2. Non-goals (v1 implementation)

- Full **registry_stage** integration on the ASP path (optional later; WFM `skip_registry` remains valid).
- **Theorem proving** or entailment of the last line from premises (only consistency / cores).
- **Automatic ontology merge** across bundles beyond “existing policy text in formalizer context” (see `dev_plan_bundle_merge_joint_theory_v1.md` for future).
- Deleting **`smt_pipeline`** in the first milestone (keep for regression/compare until ASP path is green).

## 3. Current codebase map (what we mirror)

| Existing (`smt_pipeline`) | New (`asp_pipeline`) |
|---------------------------|------------------------|
| `pipeline.py` | `asp_pipeline/pipeline.py` — steps 1–6 per [`asp/pipeline_wfm_to_asp.md`](../asp/pipeline_wfm_to_asp.md) §6 |
| `config.py` | `asp_pipeline/config.py` — `ASP_PIPELINE_*` env vars per spec §9 |
| `llm_steps.py` | `asp_pipeline/llm_steps.py` — load `prompts/formalizer.md` + `critic.md`; no hardcoded prose |
| `smt_parse.py` (Z3 parse) | **`asp_pipeline/clingo_check.py`** — `clingo --parse-only`, `clingo --ground` |
| `commit.py` | Reuse **`smt_pipeline/commit.py`** (or move to `shared/` later) — same atomic write semantics |
| `policy_check.py` + `unsat_core.py` | **`asp_pipeline/policy_check.py`** — solve + core via assumptions (spec §8) |
| `cli.py` / `__main__.py` | `asp_pipeline/cli.py` — `python -m asp_pipeline` |
| `run_wfm_handoff_batch.py` | `asp_pipeline/run_wfm_handoff_batch.py` — default dirs `bundles/asp_from_wfm/` |
| `run_policy_batch_check.py` | `asp_pipeline/run_policy_batch_check.py` — Clingo-based |
| `tests/test_pipeline.py` | `asp_pipeline/tests/…` — mock formalizer/critic; mock clingo or use tiny programs |
| `models.py` | Reuse or duplicate minimal `PipelineRunResult`-shaped dataclasses; align field names with existing bundle JSON |

**Unchanged packages:** `wfm_orchestration/`, `registry_stage/wfm_acceptance_handoff.py`, `HandoffBundle` parsing in `registry_stage/loaders.py` (unless schema evolves — not required for v1).

---

## 4. Workstream A — WFM (Agent 3 + docs)

**Objective:** NL scope matches **ClinCon-safe fragment**; temporal/state narratives **in scope** when expressible as fluents; old “temporal = OUT_OF_SCOPE” defaults **removed** where they conflict with the new spec.

| Task | Detail | Done when |
|------|--------|-----------|
| A1 | Update **`WFM/prompts/agent_3_scope_rewrite.md`** (and any Agent 2 decomposition hints if needed) with fragment rules from spec §2: term functions, NAF stratification, linear arithmetic, finite domains, choice rules, aggregates, optimization, `holds/occurs` pattern | ✅ Done |
| A2 | Update **`WFM/Agent_WFM.md`** (or companion) — scope table aligned with §2.1 / §2.2; `scope_report` must name violation class (e.g. `term-level function: …`) | ✅ Done (`pipeline_spec.md` ClinCon note) |
| A3 | Extend **stress / curated examples** in `test_sets/` where useful: at least one **in-scope** temporal snippet; at least one **OUT_OF_SCOPE** nonlinear / open-domain line with expected `scope_report` prefix | ✅ `wfm_clincon_fragment_examples_en.md` + `--clincon` runners |
| A4 | Optional: `wfm_orchestration` demo pools unchanged structurally; **re-run** small batch to confirm new Agent 3 behavior does not regress PASS/OUT_OF_SCOPE rates catastrophically | Smoke report |

**Risk:** Existing stress cases (e.g. R-*) assumed “snapshot-only” rejection; some may flip to PASS or REWRITE — **re-baseline** expected outcomes in markdown baselines if present.

---

## 5. Workstream B — `asp_pipeline` package (greenfield)

Implement in **dependency order**:

### Milestone B0 — Scaffold
- [ ] Create package `asp_pipeline/` with `__init__.py`, `config.py` (defaults match spec §9), `pyproject` / `requirements` entry for **Clingo** (document install; optional `clingo` on PATH check in CLI).
- [ ] `cli.py`: `--handoff`, `--policy-model`, `--out-bundle-dir` (mirror SMT CLI).

### Milestone B1 — `clingo_check.py`
- [ ] Subprocess wrapper: temp file write, `--parse-only`, capture stderr/stdout, timeout (`ASP_PIPELINE_CLINGO_PARSE_TIMEOUT`).
- [ ] Combined file: `existing + proposed`, `--ground --output=text`, timeout (`ASP_PIPELINE_CLINGO_GROUND_TIMEOUT`).
- [ ] Classify failures: parse vs grounding vs timeout vs `unsafe variable` substring (per spec §4).
- [ ] Unit tests with **minimal** `.lp` strings (valid / invalid / unsafe variable fixture if reproducible).

### Milestone B2 — Prompts + `llm_steps.py`
- [ ] Add **`asp_pipeline/prompts/formalizer.md`** and **`critic.md`** — text **authoritative in files**, interpolated only (spec §6 templates).
- [ ] `formalizer_lp_gemini(ctx)` and `critic_json_gemini(ctx)` — reuse patterns from `smt_pipeline/llm_steps.py` (Gemini client, token caps from config).

### Milestone B3 — `pipeline.py` (steps 1–6)
- [ ] Step 1: load handoff, partition PASS/REWRITE vs OUT_OF_SCOPE (same predicate as SMT: `verdict != OUT_OF_SCOPE`).
- [ ] Step 2: context guard (UTF-8 byte sum handoff JSON + existing policy).
- [ ] Step 3–4 loop: formalizer → strip fences → clingo parse → ground; on failure decrement **shared** parse/ground cap; structured log lines (mirror JSONL shape from SMT for comparability).
- [ ] Step 5: critic loop with **separate** semantic cap; on reject feed `overall_issue` + per-line issues into formalizer repair block (spec §6).
- [ ] Step 6: commit — `% Bundle:` header, `% Rule: line_index | NL: …` comments, atomic write; bundle record JSON + `pipeline_status` (same semantics as SMT).
- [ ] Wire **`rule_cap`**, **`POLICY_MODEL_CORRUPT`**, **`CONTEXT_LIMIT_EXCEEDED`**, **`SIZE_CAP_REACHED`** analogs (reuse `rule_count` logic if applicable to `.lp` Rule comments — or define ASP comment convention matching `policy_check` tagger).

### Milestone B4 — `policy_check.py`
- [ ] Run Clingo on full policy (document exact args for “exist at least one model”).
- [ ] Implement UNSAT / core: `#external` per tracked rule + `--assume` binary search per spec §8 (may land after basic SAT/UNSAT).
- [ ] JSON schema as in spec §8; CLI `python -m asp_pipeline.policy_check`.

### Milestone B5 — Batch runners
- [ ] `run_wfm_handoff_batch.py` — clone SMT version: paths default to `bundles/asp_from_wfm/policies/`, resume on `committed` record.
- [ ] `run_policy_batch_check.py` — glob `*.lp`.

### Milestone B6 — Tests + CI
- [ ] End-to-end test with **mocked** Gemini + **mocked** clingo (inject success/failure strings).
- [ ] One **integration** test optional: skip if `clingo` not installed (pytest marker).
- [ ] Document in root or `docs/` how to install Clingo on Windows/Linux.

---

## 6. Workstream C — Documentation & repo hygiene

- [ ] **`asp/pipeline_wfm_to_asp.md`** is the canonical ASP story (committed from product draft).
- [ ] **`smt/pipeline_wfm_to_smt.md`**: add one line at top — “Superseded for ClinCon product line by `asp/pipeline_wfm_to_asp.md`; retained for SMT track / comparison.”
- [ ] Update **`dev_plans/dev_plan_implementation_control_flow_v3.md`** footer: note ASP pivot; SMT milestones remain historical reference.
- [ ] **`pipeline_spec.md`**: add pointer to ClinCon fragment scope or defer to `asp/pipeline_wfm_to_asp.md` §2.

---

## 7. Migration strategy for developers

1. **Develop on `ClinCon-version`.** Keep `smt-pipeline` tag `wfm-smt-baseline` immutable for the old demo.
2. **First runnable milestone:** B1 + B3 with **mock** formalizer returning static `.lp` — proves subprocess + loop + commit.
3. **Second:** Real Gemini formalizer + critic on **one** handoff from `bundles/wfm_artifacts/`.
4. **Third:** Batch + policy_check.
5. **Product decision:** Whether `smt_pipeline` stays in-tree forever, moves to `archive/`, or becomes optional extra.

---

## 8. Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Grounding blowups / infinite domains | Grounding timeout → repair loop; Agent 3 trains on “finite domain” discipline |
| ClinCon vs plain Clingo feature gap | **Addressed** for `&sum` via `clingcon` in `asp_pipeline` (see `dev_plans/dev_plan_clincon_theory_grounding_v1.md`, `asp/pipeline_wfm_to_asp.md` Tooling / oracle) |
| Critic approves bad ASP | Same as SMT: caps + human review + golden tests |
| Rule counting / corruption checks for `.lp` | Define stable `% Rule:` or `%% track:` convention shared by `pipeline` and `policy_check` |

---

## 9. Acceptance criteria (v1 complete)

- [ ] `python -m asp_pipeline --handoff … --policy-model … --out-bundle-dir …` commits a valid `.lp` for at least one curated handoff with PASS lines.
- [ ] Parse/ground failure triggers repair loop; exhaustion sets failed `pipeline_status` with structured `failure_reason`.
- [ ] Critic rejection triggers semantic loop; exhaustion sets critic failure.
- [ ] `python -m asp_pipeline.policy_check` returns JSON with SAT/UNSAT for committed policies.
- [ ] Batch WFM → ASP path documented and runnable (`run_wfm_handoff_batch`, `run_policy_batch_check`).
- [ ] WFM Agent 3 updated and smoke-tested against ClinCon scope.

---

## 10. References

- [`asp/pipeline_wfm_to_asp.md`](../asp/pipeline_wfm_to_asp.md) — authoritative pipeline behavior.
- [`smt/pipeline_wfm_to_smt.md`](../smt/pipeline_wfm_to_smt.md) — prior SMT path (reference implementation).
- [`dev_plans/control_flow_v3.md`](control_flow_v3.md) — control-flow ideas transferable to repair/commit semantics.
- [`dev_plans/dev_plan_bundle_merge_joint_theory_v1.md`](dev_plan_bundle_merge_joint_theory_v1.md) — future multi-bundle joint theory (post–per-line ASP).
