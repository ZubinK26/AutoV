# Dev plan: CPMpy NL → policy pipeline (v1)

## Purpose

Implement **v1 of the generalist pipeline** described in:

- `CPMpy/Project_Spec/01_project_specification.md` — architecture, formalizer contract, AST validator, verification tiers, consistency check, runtime (Pattern A/B), orchestrator, outputs, success criteria.
- `CPMpy/Project_Spec/02_signature_template.md` — eight-section `signature.py` schema, AST enforcement rules, `TOOL_DEPENDENCIES`, test-time shape bounds.
- `CPMpy/Project_Spec/03_example_domain.md` — reference domain layout (`domains/refund_example/` → implement as `CPMpy/policy_pipeline/domains/refund_example/`), fixtures shape, and the requirement for a **second** domain (vectors + globals) to satisfy success criterion #9.

**Scope target:** **Full v1 as specified** in §1–§16 of the project specification, including all **CONFLICT** behaviors (comprehensions, expanded AST validator, assumption-SAT cheap checks, router, vector extraction, Hypothesis/mutation/roundtrip tiers, pre-deployment consistency + coverage). **Do not** shrink scope to “scalar-only demo”; scalar-only is **slice 1–2**, not the shipping bar.

**Product goal:** After this plan is implemented, an operator can run the pipeline **end-to-end** on **domain inputs** derived from repo workflows—including **WFM handoff outputs** (current or future format) via a thin adapter—without changing pipeline core code when switching handoff schema (only the adapter or config).

**Containment:** All pipeline implementation (package code, CLI, tests, example domains, WFM adapter, prompts) lives under **`CPMpy/`**—see layout below. The rest of the repo (e.g. `wfm_orchestration/`, `smt_pipeline/`) remains the **shared** WFM producer and SMT formalization path; this plan adds a **sibling** consumer of the same handoff workflow.

---

## Non-goals (explicitly out of scope per spec §14)

Multi-policy composition, live hot updates, distributed runtime, non-CPMpy targets, web UI, optimization in the gating path (objectives offline only), epistemic/claim grounding, multi-LLM ensembles.

---

## Architecture (deliverables map)

| Phase | Components | Primary artifacts |
|-------|------------|-------------------|
| **Formalization** | Formalizer LLM, AST validator, verification suite (cheap / medium / full), repair + diagnoser | `policy.py`, `manifest.json`, `verification_log.jsonl` |
| **Consistency** | Pre-deployment verifier | `consistency_report.json` |
| **Runtime** | Router, Pattern A, Pattern B, state extractor, audit log, `Decision` | Importable package used by host app |

**Orchestrator:** Deterministic Python state machine (no agent framework), with `REPAIR` substates as in spec §8.

---

## Repository layout (normative)

Implement the file tree from spec **§12** under a single Python package root, e.g. `cpmpy_pipeline/` at repo root (name finalized during slice 1; keep setuptools entry points documented in plan README).

```
cpmpy_pipeline/
  pipeline/
    orchestrator.py
    formalizer.py
    ast_validator.py
    verification/
      cheap_checks.py
      medium_checks.py
      full_checks.py
      hypothesis_generators.py
      mutation.py
      roundtrip.py
    consistency.py
    repair.py
    diagnoser.py
  runtime/
    pattern_a.py
    pattern_b.py
    router.py
    state_extractor.py
    audit_log.py
    decision.py
  llm/
    interface.py
    <provider>_client.py
    prompts/
  wfm_import/                    # see §6 — not in spec §12; add for AutoV integration
    adapter.py
    README.md
  domains/
    refund_example/              # per 03_example_domain.md
    <second_domain>/            # vectors + ≥1 global — required for v1 exit
  tests/                         # adversarial AST tests required §5 success
  cli.py
  README.md
```

**Package wiring:** `pyproject.toml` optional-deps for CPMpy, OR-Tools, z3, hypothesis, pydantic; `pytest` in dev deps; console script e.g. `cpmpy-policy-pipeline`.

---

## Inputs (domain bundle)

Per spec **§2** and signature template, each run consumes:

1. `signature.py` (eight sections).
2. `glossary.md`.
3. `rules.txt` (one decidable rule per line).
4. `tools.json` (gated tools + parameters).
5. `fixtures/` (`per_rule.py`, `properties.py` as in example).

**Validation:** Pydantic (or equivalent) validates `tools.json` and fails fast with actionable errors if required keys are missing.

---

## WFM integration (v1 requirement) — parity with SMT pipeline

The specification does not define WFM; **this repo’s existing WFM + SMT path does.** The CPMpy pipeline is a **second formalization target** fed by the **same** WFM handoff workflow:

- **Unchanged:** WFM runner, orchestration, and the **general pattern** of “handoff JSON in → formalize per rule/bundle → verify → repair.” Prompting philosophy (clear contracts, repair loops, structured outputs) should **align** with `smt_pipeline` / `wfm_orchestration` where analogous—even though the **target language is CPMpy Python**, not SMT-LIB.
- **May change:** Handoff **JSON schema** and field names, as long as the adapter is updated; the **adapter** is the only place that should know concrete handoff keys. Core pipeline code consumes the normalized domain bundle only.

**v1 must include** `CPMpy/policy_pipeline/wfm_import/` with:

1. **Accepts** a path or stdin payload to a **handoff JSON** (discriminate variants by a **schema version** field and/or CLI `--handoff-format=…`, not by hardcoded example IDs).
2. **Emits** (writes into a run workdir) the **minimal domain bundle** the orchestrator expects:
   - `rules.txt` — one NL statement per in-scope line (**same extraction rules** as existing NL pipelines: strip comments, stable ordering, align with how SMT chunk runs interpret WFM lines).
   - `tools.json` — gated tools; if handoff lacks tool schema, CLI documents **required** companion file or defaults with a loud warning.
   - **Optional:** draft `glossary.md` stubs from field names (operator-reviewed), or require operator-provided glossary next to handoff.
3. **Does not** embed domain logic (product-specific branches) in the adapter—only **structural** mapping from handoff fields to files.

Reuse **shared helpers** from the repo where they already exist for parsing handoff paths or NL lines (import from neutral modules under `wfm_orchestration` or `registry_stage` if available); avoid duplicating WFM clients in `CPMpy/`.

**CLI sketch:** `cpmpy-policy-pipeline prepare-from-wfm --handoff path.json --out-dir work/domain_bundle/` then `cpmpy-policy-pipeline run --domain work/domain_bundle/ …`. Alternatively a single `run` with `--wfm-handoff` that materializes bundle into `--work-dir` then proceeds.

**Success:** Running on a real `bundles/wfm_artifacts/*.json` (or `exports/.../wfm_handoffs/*.json`) produces a bundle that the orchestrator can **attempt** to formalize; failures are attributed to **missing glossary/signature**, not adapter crashes.

---

## Implementation slices (vertical, end-to-end each slice)

Order follows spec **§13**, expanded into acceptance criteria. Each slice ends with a **runnable demo** committed under `CPMpy/policy_pipeline/domains/` or `CPMpy/policy_pipeline/tests/examples/`.

### Slice 1 — AST validator (core subset) + Pattern A + hand-written policy

**Status (2026-05):** Initial code lives under `CPMpy/policy_pipeline/` (`cpmpy_wfm_policy` package): scalar AST allowlist (no comprehensions), `pattern_a` evaluation via `get_variables` + `Model.solve()`, `domains/refund_example/` + `tests/`. Install: `pip install -e ".[cpmpy-pipeline]"`.

- Implement `ast_validator.py` with:
  - Parse + node allow/deny lists per **§4** (start with scalar subset; leave hooks for comprehensions / globals).
  - Import allowlist from signature section 1.
  - Name resolution against signature sections 2–6; **no** helper cycle check yet if helpers empty.
- Implement `pattern_a.py`: substitute state into scalar expressions, evaluate to bool; violated rules list.
- Hand-write `policy.py` + tiny `manifest.json` for one domain (can be minimal copy of refund without LLM).
- **Tests:** `test_ast_validator.py` with adversarial: bad imports, `IfExp`, `lambda`, mystery comprehensions (should reject until slice 3/5).
- **Exit:** `pytest tests/test_ast_validator.py tests/test_pattern_a.py` green.

### Slice 2 — Formalizer LLM + per-rule cheap checks (scalar / non-global path)

- `llm/interface.py` + one provider; env-driven model id.
- `formalizer.py`: one LLM call per rule; parse JSON/text → Python assignment `rule_<n> = <expr>` + metadata flags.
- `verification/cheap_checks.py`:
  - **Direct evaluation** path for `uses_global_constraints=False` and `uses_vector_variables=False` (spec **§5.1.1**).
  - `used_symbols` / flags cross-check vs AST.
  - **Non-triviality** check (spec **§5.1.3**) for scalar boolean rules.
- Prompts artifact: seed few-shots must eventually include vector+global examples (**§9 CONFLICT**); for slice 2, include placeholder + TODO gate, or stub second path behind feature flag until slice 4.
- **Exit:** Full `refund_example` rules formalize with LLM + cheap checks (or marked skipped in CI with `GEMINI_API_KEY` unset); deterministic offline test uses mocked LLM returning fixed strings.

### Slice 3 — Orchestrator + repair loop

- `orchestrator.py`: states `LOAD_INPUTS` → `FORMALIZE` → `BATCH_VERIFY` → `FULL_VERIFY` → `CONSISTENCY_CHECK` → `EMIT_POLICY` → `RUNTIME_READY`; `REPAIR` with cap N.
- `repair.py` + `diagnoser.py`: wire diagnoser LLM for failure classification (minimal v1: parse errors vs AST vs cheap-check vs batch UNSAT).
- Emit `policy.py`, `manifest.json` with **routing flags per rule** (spec **§8 CONFLICT**).
- **Tests:** `test_orchestrator_states.py` with injected LLM functions, no network.

### Slice 4 — Pattern B + router + assumption-SAT cheap checks

- Extend AST allowlist for global constructors in spec **§4 step 6**.
- `verification/cheap_checks.py`: branch for `uses_global_constraints=True` → build one-rule `Model`, ground state, assumption-based SAT/UNSAT per **§5.1.1 CONFLICT**.
- `runtime/pattern_b.py`: assumptions + unsat core mapping to rule IDs (Z3 backend per spec **§11**).
- `runtime/router.py`: route every rule to A or B from manifest flags; **misroute = test failure** (spec §15 item 8).
- Add at least **one** rule in a dev domain using `AllDifferent` (or smallest global) to exercise the path.
- **Tests:** `test_pattern_b.py`, `test_router.py`.

### Slice 5 — Vectors + signature §4/§7 + extractor + Hypothesis + mutation

- AST: comprehensions with iterable-derived signature + `range` bounds; `cpm_array` indexing allowlist.
- Helper graph: **cycle detection + topological validation** (signature template **CONFLICT**).
- `TEST_SHAPE_BOUNDS` in signature → `hypothesis_generators.py` builds smaller arrays for tests.
- `mutation.py`: field-level and element-level mutations.
- `state_extractor.py`: scalar, `full`, `by_index`, `by_range` per **§7.3**.
- **Tests:** vector formalization fixtures; extractor unit tests; mutation tests.

### Slice 6 — Medium + full verification

- **Medium:** Hypothesis batch (every N rules), cumulative model SAT, mutation dependencies.
- **Full:** `roundtrip.py` — back-translate LLM, re-formalize, equivalence `Model([orig != reform])` UNSAT; diagnoser distinguishes ambiguity vs drift (**§5.3.1 CONFLICT**).
- Tune N (default 5–10) via config/env.

### Slice 7 — Consistency + coverage + audit + CLI + README + second domain

- `consistency.py`: SAT, per-rule reachability, optional pairwise (CI flag).
- Coverage check: per gated tool, ∃ legal and ∃ illegal state (**§5.3.3**).
- `audit_log.py`: log fields per **§7.5**.
- **CLI:** `run`, `validate-domain`, `runtime-check` (optional smoke), `prepare-from-wfm`.
- **Second domain:** New folder under `CPMpy/policy_pipeline/domains/` with **vector** field(s), **≥1 global constraint**, comprehensions; **no** changes to pipeline code—only inputs—per success criterion **#9**.
- **README:** `CPMpy/policy_pipeline/README.md` — dual latency profile, how to add domains, WFM adapter usage, pointer to SMT sibling pipeline for handoff authoring.

---

## LLM roles (all required except test generator)

| Role | Responsibility |
|------|----------------|
| Formalizer | CPMpy rule expressions + metadata flags |
| Back-translator | NL paraphrase for roundtrip |
| Diagnoser | Drift vs ambiguity for repair |
| Test-case generator | Optional; human-reviewed |

Prompts live under `llm/prompts/`; formalizer prompt **must** include few-shots for scalar, vector, and global constraint (**§9**).

---

## Outputs (contract)

- `policy.py` — importable verified module.
- `manifest.json` — rule IDs, NL, dependencies, **`uses_global_constraints`**, **`uses_vector_variables`**, version hash.
- `consistency_report.json` — SAT, reachability, optional pairwise.
- `verification_log.jsonl` — append-only check log.

---

## Success criteria (v1 exit gate)

Match **§15** of the project specification numerically where stated (e.g. roundtrip rates 85% / 70% on curated sets). Additional **internal** gates:

- AST validator: **zero** known bypasses in held-out adversarial set; CI job `test_ast_validator.py` required on PR.
- Router: 100% correct routing on manifest derived from AST flags.
- WFM adapter: documented path from at least one real handoff file to `rules.txt` + runnable orchestrator entry.

---

## CONFLICT register (implementation checklist)

Implementers must verify each item from spec **§16** is reflected in code + tests:

1. Comprehensions allowed; side-effect loops banned.
2. AST validator size/complexity acceptable; exhaustive API allowlist tests.
3. Cheap checks: dual path direct-eval vs assumption-SAT.
4. Non-triviality uses aggregation for vector rules.
5. Hypothesis uses `TEST_SHAPE_BOUNDS`.
6. Mutation supports element- and field-level.
7. Roundtrip diagnoser handles ambiguous back-translation.
8. Pattern A excludes globals/vectors; router enforces.
9. Audit log includes `pattern_used` + latency-relevant fields.
10. Vector manifest slice modes implemented.
11. Manifest includes routing flags per rule.
12. Formalizer few-shots cover globals + vectors.

---

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| CPMpy/solver version drift | Pin versions in `pyproject.toml`; CI matrix pinned. |
| LLM non-determinism | Repair loop + roundtrip equivalence; manifest stores hashes. |
| WFM schema change | Adapter version field + tests with fixture JSON snapshots. |
| Full-scope schedule pressure | Slices still vertical; **do not** ship without slice 7 second domain. |

---

## Definition of done

1. All slices **1–7** complete; second domain passes without pipeline code edits.
2. CLI documented; `CPMpy/policy_pipeline/README.md` matches **§12** layout (under `CPMpy/policy_pipeline/`) and **§7** runtime semantics.
3. `pytest` green with **mocked LLMs** in default CI; optional **live LLM** job documented for maintainers.
4. WFM `prepare-from-wfm` (or equivalent) demonstrated on at least one handoff artifact path in repo docs.

---

## References

- `CPMpy/Project_Spec/01_project_specification.md`
- `CPMpy/Project_Spec/02_signature_template.md`
- `CPMpy/Project_Spec/03_example_domain.md`
