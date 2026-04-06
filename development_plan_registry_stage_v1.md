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
| Choose **package / directory** (e.g. `registry_stage/`, `src/autov_registry/` — see **`registry_persistence_v1.md`** §10 *To do when needed*; **decide in M0**). | **Done:** package **`registry_stage/`** (import `registry_stage`); handoff dir **`bundles/`** at **repo root**; details **`registry_stage/README.md`**. |
| Add **Python env** deps as needed: `json` (stdlib), later `numpy`, `faiss-cpu` or `faiss`, `sentence-transformers` (for `BAAI/bge-base-en-v1.5` per spec), optional LLM SDK matching WFM harness. | **M0:** **`registry_stage/requirements.txt`** — `pytest` only; M2+ deps TBD / pinned when CI exists. |
| **Fixture** `bundles/*.json`: minimal valid handoff (bundle fields + 1–3 per-line objects, mix PASS and optional OUT_OF_SCOPE). | **Done:** **`bundles/fixture_bu_001.json`** (`PASS`, `OUT_OF_SCOPE`, `line_index` 0-based per **`registry_persistence_v1.md`**). |

**Exit:** `pytest` or smoke script runs zero tests but imports succeed; one fixture file committed.

**M0 exit (implemented):** `python -m pytest registry_stage/tests -q` passes; handoff fixture committed under **`bundles/`**.

---

### M1 — Persistence helpers (read-only + dev write)

**Goal:** Code can **load** and **validate** shapes from **`registry_persistence_v1.md`**; optional **write** for dev snapshots only.

| Task | Notes |
|------|--------|
| Parse **`bundles/{bundle_id}.json`** into typed structures (dataclasses / Pydantic optional). | **Done:** `registry_stage.loaders.load_handoff_bundle` / `parse_handoff_bundle`. |
| Load **`registry.json`** into session model (may start **empty**). | **Done:** `load_registry` (missing file → empty shell). |
| Implement **`validate_alignment` stub** — `pass` or TODO hooks; full checks land in Phase 2. | **Done:** `registry_stage.validation.validate_alignment` (returns `[]`; see **`registry_persistence_v1.md`** §7). |
| **Dev export:** `export_session(path, session_snapshot)` writing JSON that **maps** to registry entry / line trace shapes (not necessarily a full production `registry.json` commit). | **Done:** `registry_stage.export_session.export_session` + `DevSessionSnapshot.to_jsonable()` (`dev_export: true`). |

**Exit:** Unit test: load fixture handoff + empty registry → no crash.

**M1 exit (implemented):** `registry_stage/tests/test_m1_persistence.py`; run `python -m pytest registry_stage/tests -q` from repo root (directory containing `bundles/` and `registry_stage/`).

---

### M2 — In-memory registry + semantic index

**Goal:** **Search** (spec: embeddings + FAISS) against **session entries**.

| Task | Notes |
|------|--------|
| **`RegistrySession`:** CRUD for `entries[]` with ids `sort_` / `ent_` / `fn_`; enforce kind-specific fields. | **Done:** `registry_stage.registry_session` (`add_or_replace`, `remove`, `get`, `from_entries`; tombstoned excluded from index by default). |
| **Embedding:** for each entry, embed `nl_description + name` (spec); cache vectors in session. | **Done:** `entry_embed_text`; BGE path caches `embedding` on each indexed entry after rebuild. |
| **FAISS:** build/update index when entries change; **search(query_embedding, k)** → entry ids + scores. | **Done:** `BgeFaissSemanticIndex` + `RegistrySession.search` / `search_nl`; empty index → `[]`. |
| **Stub mode:** keyword / hash fallback if GPU/CPU limits — **clearly flagged**, not default for “spec-accurate” demo. | **Done:** `StubKeywordSemanticIndex` (`backend_label` `stub_keyword_fallback`); `create_semantic_index(prefer="faiss")` falls back if BGE/FAISS init fails. |

**Exit:** Test: insert 3 fake entries, search returns sensible neighbor for a short NL query.

**M2 exit (implemented):** `registry_stage/tests/test_m2_registry_session.py` (stub tests + BGE+FAISS when `faiss` / `sentence-transformers` are installed; `REGISTRY_M2_SKIP_HEAVY=1` skips the heavy test). Deps: `registry_stage/requirements.txt` (`numpy`, `faiss-cpu`, `sentence-transformers`).

---

### M3 — Line driver: search → extract gaps

**Goal:** For one **`statement_nl`** (in-scope line), run **search** (including **LLM-backed query expansion**), then identify **gaps** per spec using **structured** extraction where coverage is incomplete—entities/symbols **not** already explained by **authoritative** hits.

**Placement (why M3, not M4/M5):** **Search expansion** and **gap extraction** decide *what* is retrieved and *what* is still missing **before** resolution. **M4** consumes gaps (map to registry symbols, user disambiguation). **M5** materializes **post-resolve** rows. Putting LLM retrieval/extraction in M4 or M5 would invert dependencies and make traces misleading (you would be “resolving” before you know structured gaps). Therefore both capabilities are **explicit M3 requirements** below.

| Task | Notes |
|------|--------|
| **Baseline search query** | **Done:** `build_search_query` — `statement_nl` + optional `LineDriverConfig.extra_search_context` (truncated); feeds `RegistrySession.search_nl`. |
| **LLM-backed search term expansion** | **Done:** `registry_stage/llm/agents.py` (`expand_search_phrases`); prompts `registry_stage/prompts/registry_search_expand.md`; **Gemini** via `registry_stage/llm/gemini_call.py` (env contract aligned with **`test_sets/wfm_api_contract_gemini.md`**). Config: `LineDriverConfig.enable_llm`, `query_mode` (`multi_query_fuse` \| `single_concat`), caps. **Tests:** mock `llm_complete`. |
| **Authoritative hits** | **Done:** `LineDriverConfig.authoritative_min_score` / backend defaults; hits are **authoritative** for coverage; extraction **must not** contradict them (`pipeline_spec.md` step 3). |
| **Heuristic gap fallback** | **Done:** `extract_placeholder_gaps` (Title case + CamelCase) — keep when LLM disabled, for CI, or as hybrid merge input. |
| **Structured gap extraction (LLM)** | **Done:** `extract_structured_gaps` in `registry_stage/llm/agents.py`; prompt `registry_stage/prompts/registry_gap_extract.md`; model `StructuredGap` + masking in `registry_stage/line_driver.py`. **Tests:** mocked LLM JSON. |
| **Logging / observability** | **Done:** INFO log with `hits`, `gaps`, `expansion` phrases, truncated `queries_used`, baseline snippet. |

**Exit (stub path — implemented):** For a line and a small registry fixture, logs show `hits` + heuristic `gaps`; `registry_stage/line_driver.py`, `registry_stage/tests/test_m3_line_driver.py`.

**M3 exit (LLM path — implemented):** `enable_llm=False` default (heuristic-only, CI-safe); `enable_llm=True` runs expansion then extraction (two Gemini calls when `llm_complete` not injected). Tests: `registry_stage/tests/test_m3_llm_line_driver.py` (mocks) + existing `test_m3_line_driver.py`.

**Gap schema evolution:** If new fields are added to each structured gap (e.g. placeholders for future `rule_id` / bundle trace), **M4** and **M5** must be updated in the same change (or immediately after): consume them in resolve/populate, persist them in the per-line trace, or **explicitly** document ignore rules. Extending the gap JSON without touching downstream consumers will break demos and exports.

**M3 empirical validation — required before M4:** **M4 is not required** to choose retrieval/masking defaults: validation uses **M3-only** outputs (per-line traces with `hits`, expansion metadata, structured `gaps`) on a **fixed small eval set** (bundle fixture(s) + optional seeded `registry.json`). By **end of M3**, run and record **two** comparisons (same eval set, same prompts):

1. **Query mode:** **multi-query + fusion** vs **single concatenated query** (defaults on until results decide). Capture precision/recall *for retrieval* you care about (e.g. “correct registry row in top‑k”), plus latency (# of embed/search calls).
2. **Masking:** **less aggressive** vs **more aggressive** masking (config preset or threshold); capture gap lists and whether obvious unknowns are incorrectly suppressed.

Pick defaults **before starting M4** so resolve and disambiguation (M4) do not churn. Re-run a lighter check after **M5** only if trace/populate changes what “gap” means in exports.

**Gemini integration (recommended shape):** Implement a **thin caller under `registry_stage/`** (e.g. `registry_stage/llm/`) that uses the **same env contract** as **`test_sets/wfm_api_contract_gemini.md`** (`GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_TEMPERATURE`, `GEMINI_MAX_OUTPUT_TOKENS`, `GEMINI_THINKING_LEVEL`, `google-genai` SDK). **Do not** import **`test_sets/scripts/*.py`** as a library (CLI scripts, not a stable API). Keep the caller minimal and **document “parity”** with `run_wfm_folio_gemini.py` / `call_gemini` so ops behavior stays aligned. **End of M3 review:** Revisit whether to extract a **shared** `gemini_client` module used by both `test_sets` and `registry_stage` to remove duplication (only after M3 retrieval/extraction work is done).

**Implementation (M3 LLM path — done):** `registry_stage/llm/` (`gemini_call.py`, `agents.py`), prompts under `registry_stage/prompts/`; `LineDriverConfig.enable_llm`, `query_mode`, `masking_preset`; defaults per caps below. CI/tests use **mocks** (`llm_complete` inject); live Gemini requires `GEMINI_API_KEY` and `pip install google-genai` (see `registry_stage/requirements.txt`).

**Default caps (v1 — adjust after empirical pass):** **Max expanded phrases:** 8 (plus one baseline query in multi-query mode). **Max characters per expansion phrase:** 512. **Max length of single concatenated query string:** 6000 characters (truncate with explicit log). Rationale: limits FAISS/embed cost and query drift; enough room for Gemini paraphrases without dumping whole bundles into one string.

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
| **LLM resolve polishing** (tone, disambiguation hints, paraphrase suggestions for the user). | M4 prompts; does **not** replace M3 retrieval/extraction (those are **required in M3**). |
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
| LLM quality for gaps/resolve | **M3** ships **LLM expansion + structured gaps** (with **heuristic fallback**); use **mocks/fixtures in CI**, live provider for manual demos; **Stretch** adds optional **resolve polishing** in M4. |
| FAISS / model weight size | Document env; offer stub index for CI. |
| Scope creep into formalizer | Gate PRs with “M5 trace only” acceptance. |

---

## What this plan covers (summary)

| Area | Covered |
|------|---------|
| Structured **handoff ingestion** | M1, M6 |
| **Semantic + structural** registry session | M2 |
| **Step 3** pipeline: search (**+ LLM expansion**), **structured** gaps, resolve, populate | M3–M5 (retrieval/extraction **M3**) |
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
