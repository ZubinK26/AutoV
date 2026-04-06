# Development plan — Registry stage v1 (pre–formalizer)

**Purpose:** Execute the **thin vertical slice** agreed in **`registry_persistence_v1.md`** §§8–9: implement **`pipeline_spec.md` step 3** end-to-end in a **runnable** way, from a **structured handoff** through **search → resolve → user outcome → session populate**, **without** requiring the formalizer, Z3, or production rule commit.

**Canonical references:**

| Doc | Role |
|-----|------|
| **`pipeline_spec.md`** | Step 3 behavior; handoff tables; failure/commit (for later phases). |
| **`registry_persistence_v1.md`** | JSON shapes, enums, Phase 1 boundary, implementation-gap table (§10). |
| **`WFM/Agent_WFM.md`**, **`WFM/prompts/`** | Upstream of handoff (fixtures can mimic Agent 3 output). |
| **`Registry_Way_Forward.ipynb`** | Resolved design table #1–#7. |

**Do not confuse numbers:**

| Meaning | What it refers to |
|--------|-------------------|
| **`pipeline_spec.md` steps 1–8** | Whole NL→Z3 **pipeline** (WFM → registry → formalizer → Z3 → critic → repair → rule accepted). |
| **This document’s M0–M6** | **Milestones** that implement **only pipeline step 3** (Registry agent), i.e. **Phase 1**. |
| **The six bullets** in *What becomes possible after this plan is done* | **Six capabilities** you gain (numbered 1–6 there), **not** pipeline step numbers. |

**Pipeline coverage of this plan**

| `pipeline_spec` step | In Phase 1 (M0–M6)? |
|----------------------|----------------------|
| 1–2 — User input + WFM | **No** (use **`bundles/{bundle_id}.json`** as if WFM had already finished). |
| **3 — Registry agent** | **Yes** — full scope of this plan. |
| **4 — Formalizer** | **No** |
| **5 — Z3 syntax/type check** | **No** |
| **6 — Identifier critic** | **No** |
| **7 — Repair loop** | **No** |
| **8 — Rule accepted** (persist `rules.json`, `committed_edges`, production commit) | **No** |

Steps **4–8** belong to **Phase 2**, which this file only **outlines**; they are **not** broken into milestones here. A future **`development_plan_pipeline_phase2.md`** (or similar) would flesh out formalizer → Z3 → critic → repair → commit the way M0–M6 flesh out step 3.

**Principles**

1. **Neither persistence nor workflow in isolation** — each milestone ships a runnable increment.
2. **Session-first** — production `registry.json` / `rules.json` / `committed_edges` stay **out of scope** until **Phase 2** (post-formalizer) unless you add an explicit **dev-only export** (see M5).
3. **Handoff as boundary** — inputs are **`bundles/{bundle_id}.json`** (+ optional `.pipeline.json` updates for status experiments).

---

## Milestones

### M0 — Scaffold and conventions

**Goal:** A place for code and tests; no product behavior required beyond “it imports.”

| Task | Notes |
|------|--------|
| Choose **package / directory** (e.g. `registry_stage/`, `src/autov_registry/` — see **`registry_persistence_v1.md`** §10 *To do when needed*; **decide in M0**). | Record choice in this file or `README` snippet. |
| Add **Python env** deps as needed: `json` (stdlib), later `numpy`, `faiss-cpu` or `faiss`, `sentence-transformers` (for `BAAI/bge-base-en-v1.5` per spec), optional LLM SDK matching WFM harness. | Pin versions when CI exists. |
| **Fixture** `bundles/*.json`: minimal valid handoff (bundle fields + 1–3 per-line objects, mix PASS and optional OUT_OF_SCOPE). | Generated from **`pipeline_spec.md`** *WFM → registry handoff*. |

**Exit:** `pytest` or smoke script runs zero tests but imports succeed; one fixture file committed.

---

### M1 — Persistence helpers (read-only + dev write)

**Goal:** Code can **load** and **validate** shapes from **`registry_persistence_v1.md`**; optional **write** for dev snapshots only.

| Task | Notes |
|------|--------|
| Parse **`bundles/{bundle_id}.json`** into typed structures (dataclasses / Pydantic optional). | Reject unknown required fields in strict mode later. |
| Load **`registry.json`** into session model (may start **empty**). | Supports “warm start” from prior dev export. |
| Implement **`validate_alignment` stub** — `pass` or TODO hooks; full checks land in Phase 2. | Spec reminder in **`registry_persistence_v1.md`** §7. |
| **Dev export:** `export_session(path, session_snapshot)` writing JSON that **maps** to registry entry / line trace shapes (not necessarily a full production `registry.json` commit). | Label as `dev_export: true` in metadata if useful. |

**Exit:** Unit test: load fixture handoff + empty registry → no crash.

---

### M2 — In-memory registry + semantic index

**Goal:** **Search** (spec: embeddings + FAISS) against **session entries**.

| Task | Notes |
|------|--------|
| **`RegistrySession`:** CRUD for `entries[]` with ids `sort_` / `ent_` / `fn_`; enforce kind-specific fields. | Tombstone optional in v1 session. |
| **Embedding:** for each entry, embed `nl_description + name` (spec); cache vectors in session. | Model: **`bge-base-en-v1.5`** per **`pipeline_spec.md`**. |
| **FAISS:** build/update index when entries change; **search(query_embedding, k)** → entry ids + scores. | Empty registry: return []. |
| **Stub mode:** keyword / hash fallback if GPU/CPU limits — **clearly flagged**, not default for “spec-accurate” demo. |

**Exit:** Test: insert 3 fake entries, search returns sensible neighbor for a short NL query.

---

### M3 — Line driver: search → extract gaps (skeleton)

**Goal:** For one **`statement_nl`** (in-scope line), run **search** then identify **gaps** per spec (entities/symbols **not** covered by authoritative hits).

| Task | Notes |
|------|--------|
| **Search terms:** start with **`statement_nl`** as query string (embed query); optional LLM to expand terms (prompt **To do** — start heuristic). | Align with **`pipeline_spec.md`** step 3 “generate search terms.” |
| **Authoritative hits:** treat top-k + threshold as “covered”; never let gap extraction **override** existing entries. | |
| **Gap extraction:** stub returns **placeholder** gaps (e.g. nouns / capitalized tokens) OR LLM structured output (prompt **To do**). | Log gaps per `line_index`. |

**Exit:** For a line and a small registry fixture, logs show `hits` + `gaps`.

---

### M4 — Resolve + user path

**Goal:** **Side-by-side** pre-resolved vs registry-resolved NL; **auto-confirm** default; **interrupt** when ambiguous.

| Task | Notes |
|------|--------|
| **Resolve:** substitute canonical **names + ids** into text (or parallel “resolved line” field) per **`pipeline_spec.md`** step 3. | Store **pre_resolved** / **resolved** strings per line. |
| **Auto-confirm:** if single unambiguous mapping per gap, accept without prompt. | |
| **Ambiguity:** if multiple competing registry matches, **present options** (CLI: numbered menu; future: UI). | Record **user_choice** in trace. |
| **Disagree / correct:** user can pick alternate id or type correction — session updates before populate. | Minimal: one correction round in v1. |

**Exit:** Integration-style test with scripted “user” input completes resolve for 2 lines, one auto, one disambiguation.

---

### M5 — Populate (session) + traceability bundle

**Goal:** After resolve, **add** new session entries for remaining gaps **and** link context for formalizer **later** (in-memory only).

| Task | Notes |
|------|--------|
| **Populate:** create tentative `sort_` / `ent_` / `fn_` rows; update FAISS. | No `rule_id` yet if formalizer not run — optional **`provisional_line_ref`** `{bundle_id, line_index}`. |
| **Per-line trace object:** `{ bundle_id, line_index, statement_nl, agent3_verdict, hits, gaps, pre_resolved_nl, resolved_nl, user_decisions, new_entry_ids }`. | Serializable for dev export. |
| **OUT_OF_SCOPE lines:** skip formal pipeline steps; include in trace as **`skipped_reason`**. | Match **`pipeline_spec.md`**. |
| **Optional:** write **`.pipeline.json`** with `pipeline_status: pending` for harness realism. | Does not imply production commit. |

**Exit:** End-to-end: handoff fixture → for each in-scope line, session contains new/updated entries + full trace JSON exportable.

---

### M6 — Runnable harness

**Goal:** One command reproduces the demo for humans.

| Task | Notes |
|------|--------|
| CLI e.g. `python -m registry_stage.run --bundle bundles/fixture_bu_001.json [--registry path/to/registry.json] [--interactive]`. | Exact module path follows M0 choice. |
| **Output:** print resolved lines + summary; write `exports/{bundle_id}_session.json` (dev). | |

**Exit:** README section “Registry stage v1 demo” with copy-paste command.

---

### Stretch (same phase, optional)

| Task | Notes |
|------|--------|
| **LLM-backed** search expansion + gap extraction + resolve polishing. | Add `registry_stage/prompts/`; mirror WFM prompt hygiene. |
| **Warm start** from real `registry.json` produced elsewhere. | M1 loader + M2 reindex. |

---

## Explicitly out of scope for this plan

- **`pipeline_spec.md` steps 4–8** (formalizer, Z3, critic, repair loop, **production** rule acceptance).
- **Production commit** to `registry.json` / `rules.json` / **`committed_edges`** / bundle **`committed` status** tied to successful Z3 (see *Failure / commit contract* — **Phase 2**).
- **Contradiction / consistency engine** (deferred in spec).
- **Product WFM↔orchestrator API** (use fixtures until defined).

---

## Risks / mitigations

| Risk | Mitigation |
|------|------------|
| LLM quality for gaps/resolve | Start M3–M4 with **deterministic stubs**; add LLM in Stretch. |
| FAISS / model weight size | Document env; offer stub index for CI. |
| Scope creep into formalizer | Gate PRs with “M5 trace only” acceptance. |

---

## What this plan covers (summary)

| Area | Covered |
|------|---------|
| Structured **handoff ingestion** | M1, M6 |
| **Semantic + structural** registry session | M2 |
| **Step 3** pipeline: search, gaps, resolve, populate | M3–M5 |
| **User** agree / disambiguate / disagree path | M4 |
| **Traceability** per `line_index` / `bundle_id` | M5 |
| Alignment with **`registry_persistence_v1`** keys | M1, M5 exports |
| **Runnable demo** | M6 |

---

## What becomes possible after this plan is done

1. **Experience** the full **registry agent story** from a realistic **post–WFM handoff** without building formalizer or Z3.
2. **Test** extraction, retrieval, and **registry-resolved NL** with real or stubbed embeddings.
3. **Iterate prompts** for search/gaps/resolve with **fast feedback** (fixture in → trace out).
4. **Show stakeholders** side-by-side resolution and disambiguation UX early.
5. **Produce dev artifacts** that **map 1:1** to **`registry_persistence_v1`** so **Phase 2** adds formalizer → production commit without renaming fields.
6. **Optionally warm-start** from a growing `registry.json` once you start persisting dev sessions.

---

## Phase 2 pointer (not scheduled here)

After M0–M6, you can **design and implement** the rest of **`pipeline_spec.md`** **steps 4–8** in a **separate** plan:

| Step | Work (summary) |
|------|----------------|
| **4** | Formalizer LLM + registry context → Z3/Python artifact. |
| **5** | Z3 parse/type check. |
| **6** | Identifier extraction + fuzzy match + critic LLM. |
| **7** | Repair loop (errors back to formalizer, iteration budget). |
| **8** | User-approved **production commit**: `rules.json`, **`committed_edges`**, **`registry.json`**, **`bundles/*.pipeline.json`** per *Failure / commit contract*; full **`validate_alignment`**. |

Until that plan exists, **steps 4–8 are not** in the “what you can do after” list for **Phase 1** — by design, Phase 1 stops at the **output that step 3 hands to step 4** (resolved NL + session registry context).
