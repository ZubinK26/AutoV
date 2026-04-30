# Dev plan — Agent simulation (`agentsim`) + SMT runtime validation

**Branch / product line:** `agentic-simulation` — commit and branch rules: [`dev_plan_agentic_simulation_branch.md`](dev_plan_agentic_simulation_branch.md).

**Normative product specs (read in this order):**

| Spec | Path |
|------|------|
| Simulation environment | [`agentsim/01_simulation_environment.md`](../agentsim/01_simulation_environment.md) |
| Agent interactions | [`agentsim/02_agent_interactions.md`](../agentsim/02_agent_interactions.md) |
| Validation workflow | [`agentsim/03_validation_workflow.md`](../agentsim/03_validation_workflow.md) |
| Policy sentences (NL source for formalization) | [`agentsim/04_agentic_guardrails.txt`](../agentsim/04_agentic_guardrails.txt) |

**Existing formalization path (not re-specified here):** NL → SMT-LIB as described in [`smt/pipeline_wfm_to_smt.md`](../smt/pipeline_wfm_to_smt.md). The simulation consumes a compiled **`policy.smt2`** (versioned; referenced in audit entries as `policy_version`).

**Principle:** Implement in **vertical slices** (each slice demoable) with **frozen interfaces** between DB/tools, snapshot extraction, and the validator. Grow **`policy.smt2`** incrementally from [`agentsim/04_agentic_guardrails.txt`](../agentsim/04_agentic_guardrails.txt) via the existing pipeline; do not block the sim on a “complete” policy.

---

## 1. Goals (v1)

1. **Deterministic fake bank world:** SQLite + entities and tools per **01**; mockable `now()`; fresh seed per scenario.
2. **Runtime enforcement:** Every **write** tool is intercepted; **validate_call(call, StateSnapshot) → Decision** per **02**/**03**; read tools execute directly.
3. **Shared policy artifact:** One **`policy.smt2`** for pre-deploy checks **and** per-action Z3 checks per **03**.
4. **Harness + comparison:** Scripted scenarios with postconditions; **vanilla** (minimal prompt + full policy text) vs **runtime-gated** (minimal prompt only) per **01**/**02**/**03**, with metrics from audit + post-hoc “as-if” validation for vanilla.
5. **Observability:** Append-only **audit log** (tool path) and **validation log** (solver path) per **02**/**03** — sufficient for demos and debugging.

---

## 2. Non-goals (v1)

- Items listed **“Out of scope for v1”** in **01** (real schemes, multi-currency, etc.).
- **Epistemic legality** / full **fabrication detector** — **stub only** per **02**; real check is v2.
- **Cross-turn coherence** enforcement — v2 (**03**).
- Redesigning the **NL→SMT** formalizer prompts or pipeline structure — reuse as-is.

---

## 3. Traceability — spec deliverables → this plan

| Spec | § Deliverables | Planned home (conceptual) |
|------|----------------|---------------------------|
| **01** | SQLite schema + Pydantic models; seed fixture; 22 tools; SDK shim; validator **interface** stub; audit writer; harness; ~10 scenarios | Package e.g. `agentsim/` or `simulation/` (exact name decided at scaffold) |
| **02** | Conversation loop; interception; StateSnapshot extractor; audit log; two prompt variants; fabrication stub; force-escalation | Same package + thin `harness/` driver |
| **03** | Z3 wrapper + parse cache; manifests; snapshot→SMT; call→term; unsat core + rule mapping; `consistency_report.json` CLI; `validate_call` module; decision logger; vanilla batch | Package e.g. `agentsim/validator/` or top-level `agentic_validator/` — keep import graph acyclic (validator may import snapshot types, not LLM SDK) |
| **04** | *(NL source)* | Chunks fed through existing `smt_pipeline` (or equivalent) → **`policy.smt2` artifacts** checked in or under `agentsim/policies/` (path TBD at implementation) |

---

## 4. Frozen interfaces (lock early)

These contracts should stay stable so work can proceed in parallel:

1. **`ToolCall`:** `tool_name`, `parameters`, `proposed_at`, `interaction_id` (**02**).
2. **`StateSnapshot`:** frozen, JSON-serializable dict (or TypedDict) — material of DB slice + derived rollups (e.g. goodwill totals) per manifests (**02**/**03**).
3. **`Decision`:** `allow: bool`, `unsat_core: list[str] | None`, `explanation: str` (**02**); extend only additively for timing fields if needed.
4. **`validate_call(call, state) -> Decision`** — single entry point for write path (**02**/**03**).
5. **Policy artifact:** path + version string (comment header in **03**); loader reads `policy.smt2` only, never NL at runtime.

---

## 5. Vertical slices (implementation order)

Each slice has **exit criteria** before starting the next.

### Slice A — World + reads + harness skeleton

- SQLite schema + Pydantic models (**01** entities).
- Seed fixture (smaller than full **01** target is acceptable first — grow to ~50 customers / spread later).
- All **nine read** tools working against DB.
- Harness: fresh DB, create `Interaction`, inject messages (stub LLM acceptable: scripted tool calls only) — proves loader and assertions DSL.
- **Exit:** One scenario runs read-only path; audit records reads with `decision: NA`.

### Slice B — Writes + stub validator + audit

- All **thirteen write** tools implemented (DB effects + typing).
- Interception: write path always calls `validate_call`; **stub** returns `allow=True`.
- Audit log covers read + write per **02**.
- **Exit:** One scenario performs a write successfully; log shows ALLOW from stub.

### Slice C — Real per-action Z3 (minimal policy)

- Z3 wrapper: load/cache **`policy.smt2`**, push/pop, negated legality query per **03**.
- Snapshot extractor from **YAML manifests** for **one** write tool (e.g. `apply_refund` or `apply_goodwill_credit`) end-to-end.
- Translators: `StateSnapshot` → ground facts; `ToolCall` → call term; `legal(state, call)` check.
- **`policy.smt2` v0:** handful of rules from **04** only (produced via existing pipeline).
- **Exit:** At least one BLOCK and one ALLOW case in tests with stable assertions; validation log captures `solver_time_ms`.

### Slice D — Pre-deploy consistency CLI

- Implement `validate-policy policy.smt2 → consistency_report.json` per **03** (SAT, reachability, tool coverage; pairwise optional / CI).
- **Exit:** CI or local script fails on unsatisfiable policy; report checked in as golden for a tiny policy fixture.

### Slice E — Full integration + comparison runs

- All write tools manifest-driven (iterate **03** manifests).
- Conversation loop + optional LLM adapter (**02**).
- Two system prompts; **vanilla comparison** batch (**03**): post-hoc validation counts + runtime-gated live blocks.
- Force-escalation on repeated blocks (**02**); fabrication detector **stub** returns no-op.
- Grow seed scenarios toward **~10** spanning five domains (**01**).
- **Exit:** Demo script produces side-by-side metrics; escalation scenario passes.

Slices **F+** (after v1 approval): expand **04** coverage, decision cache, pairwise CI, fabrication v2, performance tuning (200 ms budget **03**).

---

## 6. Workstreams and milestones (checklist)

### Workstream 1 — Simulation core (**01**)

- [ ] **1.1** Schema + migrations/init for SQLite mirroring entity model.
- [ ] **1.2** Pydantic (or equivalent) models aligned with schema.
- [ ] **1.3** Seed loader (JSON/YAML) → fresh in-memory DB per scenario.
- [ ] **1.4** Mockable clock injected into queries and tools.
- [ ] **1.5** Implement 9 read + 13 write tools; register schemas for SDK.
- [ ] **1.6** Tool registration / adapter for chosen LLM tool-calling API.

### Workstream 2 — Agent loop + governance (**02**)

- [ ] **2.1** Conversation loop driver (tool → final message, escalation terminates).
- [ ] **2.2** Interception layer (reads direct; writes → validator).
- [ ] **2.3** StateSnapshot extractor (manifest registry per write tool).
- [ ] **2.4** Audit log writer (fields per **02**).
- [ ] **2.5** System prompt variants: minimal-runtime vs vanilla full-policy.
- [ ] **2.6** Force-escalation after N identical/repeated blocked calls.
- [ ] **2.7** Fabrication detector **stub** (interface only / always pass).

### Workstream 3 — Validator + policy checks (**03**)

- [ ] **3.1** Z3 parse cache + scoped assertions per request.
- [ ] **3.2** Manifest YAML (or Python equivalents) for each write tool.
- [ ] **3.3** Snapshot → ground SMT; ToolCall → ground call term.
- [ ] **3.4** Legality query + ALLOW/BLOCK; unsat core → rule IDs + explanation.
- [ ] **3.5** Validation / decision logger (fields per **03**).
- [ ] **3.6** CLI: consistency report → `consistency_report.json`.
- [ ] **3.7** `validate_call` module as stable import.
- [ ] **3.8** Vanilla-comparison batch runner.

### Workstream 4 — Policy content (**04** + existing SMT pipeline)

- [ ] **4.1** Prioritize **04** sentences into tranches (refunds/disputes first, etc.).
- [ ] **4.2** Run formalizer to produce **`policy.smt2`** per tranche; version tag.
- [ ] **4.3** Keep NL chunks + compiled SMT pairs reproducible (paths + pinning in repo docs or bundle records as you already do for WFM).

### Workstream 5 — Quality

- [ ] **5.1** Unit tests: grounding translators, one tool manifest, stub harness.
- [ ] **5.2** Integration tests: seeded DB + Z3 (skip if Z3 unavailable, with pytest marker).
- [ ] **5.3** Golden files: small **`policy.smt2`**, expected `consistency_report.json`, one ALLOW/UNSAT core fixture.

---

## 7. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| **SMT encode mismatch** — DB fields vs predicates in `policy.smt2` | Single schema doc; snapshot translator tests; rule IDs in SMT comments per **03** |
| **Large snapshots / slow queries** | Strict manifests; cap entities; profile early against **03** latency budget |
| **Policy contradicts itself** | **Slice D** gate; no deploy without `satisfiable: true` |
| **Vanilla vs gated conflated** | Separate runs, explicit `policy_version` + prompt variant in logs |

---

## 8. What this document defers to “next chunk” (after your approval)

Implementation should **not** start in this commit unless you explicitly request it. The **first implementation chunk** recommended after approval is **Slice A** (§5) + scaffold **Workstream 1** tasks **1.1–1.4** and minimal **2.4** if audit is needed for reads — adjust if you prefer validator stub first on empty DB.

Optional follow-up edits to *this* dev plan (separate from code): dependency diagram, exact Python package names, CI job names, and pin which existing `smt_pipeline` entrypoint produces `policy.smt2` for **04**.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-26 | Initial `dev_plan_agentsim_v1.md` — umbrella plan, vertical slices, workstreams, traceability to **agentsim** 01–04. |
