# Dev plan — WFM → registry workflow end-to-end demo

**Purpose:** Ship a **single stakeholder-facing story**: choose input (curated or manual) → run **WFM** (user makes in-flow choices: confirmation, disagree, Agent 4, etc.) → on **acceptance** (**yes** / **y**), **automatically** build the handoff and run the **registry agent** workflow (**`pipeline_spec.md`** step 3 through populate / dev export, **before** formalizer) → optionally **readable** reports at each stage. **No** separate “after the demo, fill a JSON file by hand” step for registry.

**Authoritative specs:** **`pipeline_spec.md`**, **`registry_persistence_v1.md`**, **`development_plan_registry_stage_v1.md`** (M0–M6), **`asp/wfm/Agent_WFM.md`**, **`test_sets/README.md`**.

**G1 / G2 implementation detail (orchestration only):** **`development_plan_g1_g2_orchestration.md`** — maps demo intentions to locked asp/wfm/registry behavior, **O1–O3** open points, and default recommendations.

---

## Terminology — “gaps” in chat vs this table

An earlier assistant message used **“gaps / choices”** as a **loose checklist** of *anything* to settle before implementation. That mixed two different things:

| Meaning | Examples |
|---------|----------|
| **A — Implementation gap** | Code that **does not exist yet** and must be **built** (orchestrator, handoff builder, Style-A loop automation). |
| **B — Agreed deliverable / content** | **Curated example lists** are **not** an undecided product question: the spec is **already agreed** (~**10** per source from existing FOLIO / P-FOLIO / stress files, difficulty mix: **hard** first, then **medium**, **1–2 easy** total globally). **Implementation** = **author and check in** the index files — **content work**, not “we don’t know what we want.” |

**Why “curated lists” looked like it was in a “gaps” section:** it was listed as **item 5** in that **pre-flight checklist** (alongside “pick Gemini,” “bundle id policy,” etc.). That was **confusing labeling** — it was **never** “missing requirements,” only **scheduled curation**. The separate note about **not** needing an **exhaustive** pool (every FOLIO row in the dataset) was the same idea as **B**: a **small checked-in** list is enough; **expand later** without architecture change.

**This document’s table below** uses **ID** only for **trackable rows**; **“Gap”** here means **tracked work item**, not always “unknown spec.” **G1** and **G2** are the items that **require substantial new development** (see **New dev?** column).

---

## Work tracking table (resolve during implementation; revisit when closing the plan)

| ID | Item | Kind | New development? | Status | Notes |
|----|------|------|-------------------|--------|-------|
| **G1** | Acceptance → handoff | **Code** | **Yes** — orchestrator + builder | **Done (v1)** | **`registry_stage/wfm_acceptance_handoff.py`** + **`wfm_orchestration/snapshot_from_agents.py`** + **`run_wfm_registry_e2e`** handoff path. |
| **G2** | Style-A loop (merge → Agent 1 re-entry) | **Code** | **Yes** — same-process loop | **Done (v1)** | **`wfm_orchestration/orchestrator.py`** — automatic Agent 1 after merge + user messaging. **Follow-ups:** Agent 4 retry loop, O2 A3 rewrite retry (see **`development_plan_g1_g2_orchestration.md`**). |
| **G3** | `bundle_id` | Metadata | Minimal | **Done (v1)** | **`wfm_orchestration/run_metadata.new_bundle_id`** — `demo_<YYYYMMDD>_<UTCtime>Z_<8hex>`; override via CLI **`--bundle-id`** / **`--bundle-prefix`**. |
| **G4** | `wfm_pipeline_timestamps` | Metadata | Minimal | **Done (v1)** | **`wfm_pipeline_timestamps_at_accept()`** — at minimum **`confirmation_accepted_utc`** (UTC ISO Z). |
| **G5** | `orchestration_run_id` | Metadata | Minimal | **Done (v1)** | **`orchestration_run_id_accept(bundle_id, outer_pass_index)`** — `orr_<bundle>_p<n>_accept`. |
| **G6** | Curated pools (F / PF / stress) | **Content** | **No** — check in lists (not missing spec) | **Done (v1)** | **`demo_curated_pools.json`** — **7** FOLIO / **8** P-FOLIO / **10** stress; **medium+hard** only (no easy rows). Stress uses **E-3–E-6** (not E-1/E-2). |
| **G7** | Manual word cap | Config | **Minimal** (constant after G6) | **Done (v1)** | **`demo_loader.compute_manual_word_limit()`** — `max(words in G6 pools) + 15`; enforced before WFM in **`demo_launcher`**. |
| **G8** | Readable viewers | **Code** | **Yes** | **Done (v1)** | **`python -m registry_stage.view_dev_session -i <export.json> -o <dir>`** — Markdown under `01_search` … `04_populate`; read-only (writes only `--out`). |
| **G9** | Warm-registry two-run | **Code** + runbook | **Yes** | **Done (v1)** | **`python -m registry_stage.warm_registry_two_run`** — defaults: `m4_warm_*` fixtures; **`--registry-out`**, optional **`--export-seed`** / **`--export-reuse`**. See § **8** below. |

**WFM backend:** **Gemini** — resolved (canonical demo uses Gemini harnesses / contract).

**Discussion queue:** *(empty — G1–G9 demo-track items landed.)* **G1–G9** implementation paths are in **`wfm_orchestration`** + **`registry_stage`** (v1). **Demo launcher:** `python -m wfm_orchestration.demo_launcher` (same e2e as `python -m wfm_orchestration.cli`).

---

## Relation to M0–M6 (scope check)

**Yes — for registry behavior from a valid WFM-style handoff through the end of step 3 (pre-formalizer), the M0–M6 implementation is sufficient.** `run_bundle_through_registry` + `python -m registry_stage.run` already exercise **search → gap extraction → automated resolve → populate** with traces and export.

What this demo plan adds is **not** another registry milestone — it is **orchestration and presentation**:

| Area | M0–M6 status | Demo plan |
|------|----------------|-----------|
| Registry pipeline on `HandoffBundle` | **Done** | Call existing APIs / CLI |
| WFM Agents 1–3 (+ Agent 4) harness | **Done** (`test_sets/scripts/`) | Extend / unify under **one** orchestrator |
| **One** flow: menu → WFM → **accept → auto handoff** → registry | **Done (v1)** | **`python -m wfm_orchestration.demo_launcher`** (G6/G7) or **`python -m wfm_orchestration.cli`** — same **`run_wfm_registry_e2e`** path |
| Style-A → Agent 1 re-entry **without** new manual run | **Done (v1)** | **`wfm_orchestration/orchestrator.py`** (see **G2**) |
| Readable per-step viewers | **Done (v1)** | **G8** — **`registry_stage.view_dev_session`** (§ **4**) |
| Two-bundle warm-registry (process guard) | **Done (v1)** | **G9** — **`registry_stage.warm_registry_two_run`** (§ **8**) |

The registry dev plan’s **two-bundle warm-registry** exercise is **scripted** here; **`registry_stage.run`** remains the primitive (**`--save-registry`** / **`--registry`**).

---

## 1. Demo launcher (input choice)

**Intent:** Start from a small **menu**:

1. **P-FOLIO** — random choice from a **pre-curated** list (PF-*), lifted from existing examples.
2. **FOLIO** — random from curated **F-*** (**## FOLIO** in **`test_sets/wfm_folio_pffolio_examples_en.md`**).
3. **Stress** — random from curated **R-\*** / **E-\*** (**`test_sets/wfm_stress_examples_en.md`** or equivalent).
4. **Manual** — operator types/pastes NL subject to the **word cap** (see G7).

**Curated lists (G6):**

- **~10** example ids per category (**FOLIO**, **P-FOLIO**, **stress**), or the **maximum count available** if fewer than 10 exist in the source files.
- **Difficulty policy:** when choosing which examples to include, prefer **hard** cases first, then **medium**; include only **1–2 easy** examples **in total** across the **combined** curated set (not 1–2 per source — **one global** easy budget so the demo stresses real corners).

**Implementation:** Checked-in index (JSON or Markdown) listing **id → source file anchor** so selection does not scrape at runtime. **Random:** `random.choice`; optional **`--demo-seed`** for reproducible runs.

**Manual input word cap (G7):** `MANUAL_INPUT_WORD_LIMIT = max(word count over **all** curated blocks in G6) + 15`. Enforce **before** WFM starts.

**Deliverable:** Orchestrator entry point (e.g. `test_sets/scripts/demo_wfm_registry_launcher.py`, name TBD).

---

## 2. WFM phase (interactive, then automatic handoff)

**Intent:** User walks the **full** WFM control flow (including confirmation, disagree/omit, **Agent 4** where applicable). When the user **accepts** the confirmation package (**yes** / **y**), the orchestrator **does not** end with “now fill JSON”; it **extracts** the data needed for **`HandoffBundle`** and proceeds.

**Gemini:** **`run_wfm_folio_gemini.py`** patterns, **`run_wfm_agent4_*.py`**, **`GEMINI_API_KEY`**, contract **`test_sets/wfm_api_contract_gemini.md`**.

**Style-A loop (G2 — required):** Implement **automation** so that after Agent 4 produces / user confirms **merged** natural language, the system **invokes Agents 1 → 2 → 3** again on that merged text **inside the same program**, per **`asp/wfm/Agent_WFM.md`** (full WFM re-entry), **without** requiring the operator to launch a **second** `run_wfm_folio_gemini.py` and paste text. Budgets and failure handling follow WFM spec.

**Deliverable:** Single orchestrated demo process (or clearly linked subprocesses with **structured IPC**) that ends at “accept” with **structured acceptance state** available to the handoff builder.

---

## 3. Handoff JSON → registry (automatic at accept)

**Intent:** At accept, produce **`HandoffBundle`** JSON compatible with **`registry_stage.loaders.load_handoff_bundle`** (see **`bundles/fixture_bu_001.json`**).

**Implementation note:** The **reliable** path is **structured state** held by the orchestrator (or a **strict** final JSON record), not recovering everything from Markdown alone. Markdown remains useful for **humans**; **handoff** should come from **machine-structured** outputs.

**Deliverable:**

- **`wfm_acceptance_to_handoff_bundle(...)`** (or equivalent): inputs = structured acceptance state; output = written **`bundles/{bundle_id}.json`** or in-memory **`HandoffBundle`**.
- **Validation:** `load_handoff_bundle` succeeds.
- **Then:** invoke **`registry_stage.run`** or **`run_bundle_through_registry`** with **`--export`** / **`--save-registry`** as needed.

**Registry stage:** Unchanged — automatic resolve + populate (M4–M5).

---

## 4. Readable per-step reports (read-only)

**Intent:** Inspect **search / extract (gaps) / resolve / populate** from export traces; WFM stages from existing artifacts. **Read-only** writers; **do not** mutate sources.

**Registry mapping:**

| Narrative step | Primary source in export / trace |
|----------------|----------------------------------|
| **Search** | `hits`, `authoritative_hits`, scores; expansion / backend labels |
| **Extract (structured gaps)** | `gap_spans`, `structured_gaps` / raw structured gaps — *“gaps” here = NL gap extraction, not § work-tracking IDs* |
| **Resolve** | `registry_resolution_candidate_nl`, validation, `raw_resolver_json`, `failure_reasons` |
| **Populate** | `new_entry_ids` (and/or session diff) |

**Complexity:** Low–moderate; worth doing for demos.

---

## 5. Suggested implementation order

| Phase | Work | Exit criterion |
|-------|------|----------------|
| **P0** | Orchestrator shell + **G2** Style-A loop + structured acceptance state | Full WFM cycle including re-entry without manual paste |
| **P1** | **G1** handoff builder + `load_handoff_bundle` + `registry_stage.run` from emitted JSON | Accept → registry completes |
| **P2** | **G6** launcher menu + curated lists + G7 word cap | Random/manual entry works |
| **P3** | **G8** readable viewers | Human-readable folders per stage (**`view_dev_session`**) |
| **P4** | **G9** warm-registry two-run | Documented + scripted variant (**`warm_registry_two_run`**, § **8**) |

---

## 6. Risk / error-proneness (automatic accept → registry)

| Risk | Mitigation |
|------|------------|
| Parsing **only** human Markdown for handoff | **Don’t** rely on that as the only path; use **structured** outputs from the runner. |
| Schema drift vs **`registry_persistence_v1`** | Validate with **`load_handoff_bundle`**; tests on fixture + one live path. |
| Agent 4 / loop edge cases | Follow **`Agent_WFM.md`** budgets; surface failures clearly instead of silent bad handoffs. |

**Conclusion:** Automatic accept → handoff is **not** inherently error-prone if the orchestrator **owns** structured state; it **is** error-prone if the design depends on **regex over prose** as the primary source of truth.

---

## 7. After this demo (v1 baseline → next workflow)

**v1 e2e status:** The **WFM → handoff → registry** demo track (**G1–G9**) is the **current** project baseline for orchestration + registry **Phase 1** (step 3 through populate / export).

**Product decision (2026-04-16):** **Defer** (do not schedule next) **similarity / edit-distance** guardrails, **M4 numeric** calibration sweeps, and **systematic revisiting** of **existing** numeric knobs (e.g. **M3** Protocol B / `authoritative_min_score` / expansion and retrieval-margin prep) until a **later, explicit evaluation** after **v1 e2e** is treated as complete — i.e. guardrail work is **out of scope** for the **immediate** engineering milestone. Normative detail: **`development_plan_registry_stage_v1.md`** — **Guardrail numbers** § and **Numerical guardrails — inventory**.

**Next in the end-to-end pipeline:** **`pipeline_spec.md` Phase 2** — **steps 4–8**: formalizer (**4**) → Z3 check (**5**) → identifier critic (**6**) → repair loop (**7**) → **production commit** (**8**). **Steps 4–5** dev plan: **`development_plan_pipeline_phase2.md`**. Full pointer table: **`development_plan_registry_stage_v1.md`** — **[Phase 2 pointer](development_plan_registry_stage_v1.md#phase-2-pointer-not-scheduled-here)**. It is **out of scope** for **this** e2e demo document to restate Phase 2 milestones.

**Post–v1 polish (landed):** e2e CLI loads **repo-root `.env`** before `GEMINI_API_KEY` checks; each successful accept→registry run writes **timestamped** artifacts under **`exports/e2e_demo_runs/<UTC>_<id>/`** (`dev_session.json` + G8 **`viewer/`**), unless **`--no-artifacts`**. Prior runs are preserved (new subfolder per run).

**Interactive demo warm registry:** before the FOLIO/P-FOLIO/stress menu, **`demo_launcher`** asks whether to **load/save** **`exports/wfm_demo_warm_registry.json`** and whether to **clear** that file; scripted runs use **`--warm-registry`** / **`--clear-warm-registry`** with **`--demo-choice`**.

---

## 8. G9 — Warm-registry two-run (runbook)

**Intent:** One scripted path for the **two-bundle** process guard: run handoff **A** on an empty session, **save** the resulting registry JSON, then run handoff **B** with **`--registry`** so search/resolve see prior entries (same behavior as two manual **`registry_stage.run`** invocations; see **`registry_stage/README.md`**).

**Command (repo root):**

```powershell
pip install -r registry_stage/requirements.txt
python -m registry_stage.warm_registry_two_run --registry-out exports/warm_after_seed_registry.json
```

**Defaults:** **`--seed-bundle`** = **`registry_stage/eval_fixtures/m4_warm_seed_bundle.json`**, **`--reuse-bundle`** = **`m4_warm_reuse_bundle.json`** (same pair as **`m4_warm_eval`**). **`--registry-out`** defaults to **`exports/warm_after_seed_registry.json`** (under repo root).

**Optional:** **`--export-seed`** / **`--export-reuse`** pass through to each run’s **`--export`** (dev session snapshots). **`--index stub`** skips BGE/FAISS (faster smoke; retrieval differs). **`--no-llm`** disables M3 Gemini only; **M4 resolve still calls Gemini** unless you use tests with mocks.

**Exit code:** Non-zero if either run fails (same as **`registry_stage.run`**).
