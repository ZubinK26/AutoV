# Development plan — Registry stage v1 (pre–formalizer)

**Purpose:** Execute the **thin vertical slice** agreed in **`registry_persistence_v1.md`** §§8–9: implement **`pipeline_spec.md` step 3** end-to-end in a **runnable** way, from a **structured handoff** through **search → gap extraction → automated LLM resolve + validation → session populate**, **without** requiring the formalizer, Z3, or production rule commit. **Phase 1 resolve is automated only** (programmatic commit or structured failure — normative detail in **[Automated LLM resolution (Phase 1, normative spec)](#automated-llm-resolution-phase-1-normative-spec)**). **Interactive** disambiguation, review UI, and outer user rounds are **deferred** — background notes: **`archive/registry_resolution_interactive_design/`**.

**Canonical references:**

| Doc | Role |
|-----|------|
| **This document — [Automated LLM resolution](#automated-llm-resolution-phase-1-normative-spec)** | **Phase 1** resolve: flow, retries, success predicate, resolver schema, adopted design choices — **authoritative** for **M4**. |
| **`pipeline_spec.md`** | End-to-end pipeline; step 3 semantics (Phase 1 vs full product called out there). |
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

**Placement (why M3, not M4/M5):** **Search expansion** and **gap extraction** decide *what* is retrieved and *what* is still missing **before** resolution. **M4** consumes gaps for **automated LLM resolve + programmatic validation** (no interactive disambiguation in Phase 1). **M5** materializes **post-resolve** rows. Putting LLM retrieval/extraction in M4 or M5 would invert dependencies and make traces misleading (you would be “resolving” before you know structured gaps). Therefore both capabilities are **explicit M3 requirements** below.

| Task | Notes |
|------|--------|
| **Baseline search query** | **Done:** `build_search_query` — `statement_nl` + optional `LineDriverConfig.extra_search_context` (truncated); feeds `RegistrySession.search_nl`. |
| **LLM-backed search term expansion** | **Done:** `registry_stage/llm/agents.py` (`expand_search_phrases`); prompts `registry_stage/prompts/registry_search_expand.md`; **Gemini** via `registry_stage/llm/gemini_call.py` (env contract aligned with **`test_sets/wfm_api_contract_gemini.md`**). Config: `LineDriverConfig.enable_llm`, `query_mode` (`multi_query_fuse` \| `single_concat`), caps. **Tests:** mock `llm_complete`. |
| **Authoritative hits** | **Done:** `LineDriverConfig.authoritative_min_score` / backend defaults; hits are **authoritative** for coverage; extraction **must not** contradict them (`pipeline_spec.md` step 3). |
| **Heuristic gap fallback** | **Done:** `extract_placeholder_gaps` (Title case + CamelCase). **Merged into `gap_spans` only when LLM extraction is off** (`enable_llm=False` or no `llm_complete`). When **`enable_llm=True`** with a real extractor, **`gap_spans`** = structured surfaces only (denoise; **2026-04-09** — see **`registry_stage/REGISTRY_M4_EVAL_DECISIONS.md`**). |
| **Structured gap extraction (LLM)** | **Done:** `extract_structured_gaps` in `registry_stage/llm/agents.py`; prompt `registry_stage/prompts/registry_gap_extract.md`; model `StructuredGap` + masking in `registry_stage/line_driver.py`. **Tests:** mocked LLM JSON. |
| **Logging / observability** | **Done:** INFO log with `hits`, `gaps`, `expansion` phrases, truncated `queries_used`, baseline snippet. |

**Exit (stub path — implemented):** For a line and a small registry fixture, logs show `hits` + heuristic `gaps`; `registry_stage/line_driver.py`, `registry_stage/tests/test_m3_line_driver.py`.

**M3 exit (LLM path — implemented):** `enable_llm=False` default (heuristic-only, CI-safe); `enable_llm=True` runs expansion then extraction (two Gemini calls when `llm_complete` not injected). Tests: `registry_stage/tests/test_m3_llm_line_driver.py` (mocks) + existing `test_m3_line_driver.py`.

**Gap schema evolution:** If new fields are added to each structured gap (e.g. placeholders for future `rule_id` / bundle trace), **M4** and **M5** must be updated in the same change (or immediately after): consume them in resolve/populate, persist them in the per-line trace, or **explicitly** document ignore rules. Extending the gap JSON without touching downstream consumers will break demos and exports.

**M3 empirical validation — done for Phase 1 defaults (2026-04-08):** Retrieval/masking/min-score decisions use **M3-only** JSONL + labels (no M4). Recorded in **`registry_stage/REGISTRY_M3_EVAL_DECISIONS.md`**:

1. **Query mode:** Compared **`multi_query_fuse`** vs **`single_concat`** (conservative masking); **locked `single_concat`**.
2. **Masking:** Compared presets on business + retrieval fixtures; **locked `conservative`** for production-oriented runs.
3. **Authoritative cutoff:** Protocol B on **`m3_retrieval_eval_*`**; **BGE+FAISS default 0.35** in code (**revisit** after more eval).

Re-run a lighter M3 check after **M5** if populate/trace changes what “gap” means in exports.

**M3 Lane A — eval capture (agreed):** Implemented per **`registry_stage/REGISTRY_M3_EVAL_DECISIONS.md`**.

| Agreement | Status | Detail |
|-----------|--------|--------|
| **Raw vs post-mask on results** | **Done** | **`LineSearchGapsResult`**: `raw_structured_gaps`, `raw_expansion_phrases`; post-mask `structured_gaps` / `gap_spans`. |
| **Thin Lane A harness** | **Done** | **`m3_lane_a.py`** (+ optional **`--query-modes`**, **`--masking-presets`**, **`--authoritative-min-score`**); JSONL header + rows; **`m3_protocol_b_minscore`** for min-score sweeps. |
| **Homework fixtures** | **Done** | **`eval_fixtures/m3_business_*.json`**, **`m3_retrieval_eval_*`** (registry, lines, labels); scorer **`m3_eval_score.py`**. |
| **`authoritative_min_score`** | **Done** | Defaults + **stamped** on each Lane A row. |
| **Fixture replay (Lane B)** | **Deferred** | Optional frozen LLM responses under **`recorded_fixtures/`** — **not** part of M3 code exit; add when you want CI without API. |

**Implementation (Lane A — done):** `LineSearchGapsResult` exposes raw vs post-mask layers + **`authoritative_min_score`** / backend label + concat truncate flag; **`registry_stage/m3_lane_a.py`** writes JSONL; committed homework under **`registry_stage/eval_fixtures/m3_business_*.json`**.

**Gemini integration — done:** **`registry_stage/llm/gemini_call.py`** follows the env contract in **`test_sets/wfm_api_contract_gemini.md`** (no imports from **`test_sets/scripts/`** as a library). **Optional later:** extract a **shared** `gemini_client` used by both **`test_sets`** and **`registry_stage`** to deduplicate — **not** an M3 gate.

**Implementation (M3 LLM path — done):** `registry_stage/llm/` (`gemini_call.py`, `agents.py`), prompts under `registry_stage/prompts/`; `LineDriverConfig.enable_llm`, `query_mode`, `masking_preset`; defaults per caps below. CI/tests use **mocks** (`llm_complete` inject); live Gemini requires `GEMINI_API_KEY` and `pip install google-genai` (see `registry_stage/requirements.txt`).

**Default caps (v1 — adjust after empirical pass):** **Max expanded phrases:** 8 (plus one baseline query in multi-query mode). **Max characters per expansion phrase:** 512. **Max length of single concatenated query string:** 6000 characters (truncate with explicit log). Rationale: limits FAISS/embed cost and query drift; enough room for Gemini paraphrases without dumping whole bundles into one string.

---

### M4 — Automated resolve + validation

**Goal:** **`registry_resolution_candidate_nl`** from a **structured LLM** call (M3 hits + gaps), **programmatic validation**, then either set **`registry_resolved_nl`** or **fail the line** with error codes + trace. **No** interactive menu, choice UI, or “user round” in Phase 1 — normative spec: **[Automated LLM resolution (Phase 1, normative spec)](#automated-llm-resolution-phase-1-normative-spec)** (retries, success predicate, `resolve_mode: automated_v1`). **Future** interactive resolve: **`archive/registry_resolution_interactive_design/`**.

| Task | Notes |
|------|-------|
| **LLM resolve** | **Done (v1):** `resolve_v1` JSON via `registry_stage/llm/agents.py` (`resolve_registry_nl_parsed`), prompt **`prompts/registry_resolve_automated.md`**; **`registry_stage/resolve_automated.py`** (`run_automated_resolve`) orchestrates up to **3** calls with validation feedback. |
| **Validate** | **Done (v1 strict):** success predicate + **cited_entry_ids** ⊆ active session and ⊆ **authoritative** hits; parse errors retried. Numeric edit-distance guardrails **deferred** (calibrate after more eval). |
| **Commit** | **Done (in memory):** on pass, **`registry_resolved_nl`** = **`pre_resolved_nl`** = validated candidate in **`ResolveAutomatedOutcome`**. **M5** attaches the same fields to **per-line traces** and **dev export**. |
| **Fail** | **Done:** bad JSON / checks / uncertainty → **no** **`registry_resolved_nl`**; `failure_reasons` + `raw_resolver_json`. |
| **Substitutions / NL shape** | Matches **`pipeline_spec.md`** resolved NL fields; bundle-level serialization remains **M5/M6**. |
| **Serialization** | **M5:** trace dict + **`DevSessionSnapshot`** / export; not blocked on more M4 code. |
| **Tests** | **Done:** `registry_stage/tests/test_m4_resolve_automated.py` (mocked LLM). |

**Why M5 is next (not “waiting on M4”):** The **callable** resolve+validate path is **complete** — **`run_automated_resolve`** is what M5 consumes. What was **partial** is only the **original M4 milestone wording** that bundled **per-line trace + export** and a **two-line integration demo**; those are **M5/M6** deliverables. Starting M5 does **not** require unfinished LLM resolve work.

**Remaining M4-adjacent (optional / later):** numeric candidate NL guardrails (**not** tuned in code as of **2026-04-09** — prompts + heuristic policy only; see **`registry_stage/REGISTRY_M4_EVAL_DECISIONS.md`**); second **E2E** line in the harness (**M6**); further empirical resolve runs + labeled set for calibration.

**Exit (trace / export):** After **M5**, dev export includes **`registry_resolved_nl`** wherever resolve ran (**`pipeline_spec.md`** + **`registry_persistence_v1.md`** §5).

---

### M5 — Populate (session) + traceability bundle

**Goal:** After resolve, **add** new session entries for remaining gaps **and** link context for formalizer **later** (in-memory only).

| Task | Notes |
|------|--------|
| **Populate:** create tentative `sort_` / `ent_` / `fn_` rows; update FAISS. | **Done:** `registry_stage/populate_session.py` (`populate_provisional_from_gaps`) — structured gaps only; constants use per-bundle provisional carrier sort; functions get placeholder domain/codomain sorts. |
| **Orchestration** | **Done:** `registry_stage/bundle_workflow.py` — `run_bundle_through_registry` (M3 → M4 → M5 per line, **`OUT_OF_SCOPE`** → trace skip). |
| **Per-line trace object:** `{ bundle_id, line_index, statement_nl, agent3_verdict, hits, gaps, pre_resolved_nl, registry_resolution_candidate_nl, registry_resolved_nl, resolve_mode, validation_outcome, failure_reasons?, new_entry_ids }` (plus any fields required by **[Automated LLM resolution](#automated-llm-resolution-phase-1-normative-spec)**). | **Done:** trace dicts include hits, authoritative_hits, gap_spans, structured/raw structured gaps, expansion, **`raw_resolver_json`**, **`attempts_used`**, etc. **`user_decisions` / interactive choice ids:** omit or empty in Phase 1. Use **`registry_resolved_nl`** to match **`registry_persistence_v1.md`** §5. |
| **Dev registry snapshot** | **Done:** `registry_session_to_registry_file` (optional **`strip_embeddings`**); **`loaders.save_registry`** for warm-start JSON between runs. |
| **OUT_OF_SCOPE lines:** skip formal pipeline steps; include in trace as **`skipped_reason`**. | **Done** — Match **`pipeline_spec.md`**. |
| **Optional:** write **`.pipeline.json`** with `pipeline_status: pending` for harness realism. | Does not imply production commit. |

**Exit:** End-to-end: handoff fixture → for each in-scope line, session contains new/updated entries + full trace JSON exportable.

**M5 exit (implemented):** `registry_stage/tests/test_m5_bundle_workflow.py`; **`registry_stage/__version__`** **0.0.m5**.

---

### M6 — Runnable harness

**Goal:** One command reproduces the demo for humans.

| Task | Notes |
|------|--------|
| CLI e.g. `python -m registry_stage.run --bundle bundles/fixture_bu_001.json [--registry path/to/registry.json]`. | **Done:** `registry_stage/run.py` — **`--export`**, **`--save-registry`**, **`--index stub|faiss`**, **`--no-llm`** (M3 heuristics only; **M4 resolve still uses Gemini** when not mocked). Optional **`--interactive`** reserved for a **future** interactive resolve mode — **not** part of Phase 1 acceptance. |
| **Output:** print resolved lines + summary; write `exports/{bundle_id}_session.json` (dev). | **Done** via **`--export`** (`export_session`). |
| **Stakeholder demo — warm registry / entity reuse (process guard):** M6 **exit** stays “one README command,” but **after M0–M6 are otherwise complete**, explicitly **exercise** a **two-run** story so this cannot slip: (1) start from **cleared** or empty dev registry; (2) run **bundle A** so **M5**-style populate **seeds** entries and **persist** dev `registry.json` / session export; (3) run **bundle B** with **`--registry`** (or equivalent load) where lines reference **those** entities — **hits + `registry_resolved_nl`** should show **reuse**. Script + fixtures may be minimal; goal is **proof**, not breadth. | **Todo when milestones close** — not a blocker for shipping M5/M6 primitives. |

**Exit:** README section “Registry stage v1 demo” with copy-paste command. **Done:** `registry_stage/README.md` § **Registry stage v1 demo** ( **`run`** + **`m4_warm_eval`** pointers).

---

### Stretch (same phase, optional)

| Task | Notes |
|------|--------|
| **LLM resolve polishing** (tone, hints in structured rationale fields). | M4 prompts; does **not** replace M3 retrieval/extraction (those are **required in M3**). |
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
| LLM quality for gaps/resolve | **M3** ships **LLM expansion + structured gaps**; **heuristic** gaps merge only when **LLM off** (CI). Use **mocks/fixtures in CI**, live provider for manual demos; **`REGISTRY_M4_EVAL_DECISIONS.md`** tracks resolve prompt iterations; **Stretch** adds optional **resolve polishing** in M4. |
| FAISS / model weight size | Document env; offer stub index for CI. |
| Scope creep into formalizer | Gate PRs with “M5 trace only” acceptance. |
| **No human read** before **M5 populate** on auto-passed lines | Phase 1 **commit** is **programmatic** (schema + **cited_entry_ids** + success predicate). A human could still judge the NL wrong (e.g. substitution readability) **without** a workflow pause — **M5** runs on lines that **passed** validation. Mitigation: **full traces + dev export** for audit; stricter model flags; future **interactive** review when product requires it. |

---

## What this plan covers (summary)

| Area | Covered |
|------|---------|
| Structured **handoff ingestion** | M1, M6 |
| **Semantic + structural** registry session | M2 |
| **Step 3** pipeline: search (**+ LLM expansion**), **structured** gaps, **automated** resolve + validation, populate | M3–M5 (retrieval/extraction **M3**; resolve **M4**) |
| **Interactive** agree / disambiguate / disagree | **Deferred** (see **`archive/registry_resolution_interactive_design/`**) |
| **Traceability** per `line_index` / `bundle_id` | M5 |
| Alignment with **`registry_persistence_v1`** keys | M1, M5 exports |
| **Runnable demo** | M6 |

---

## What becomes possible after this plan is done

1. **Experience** the full **registry agent story** from a realistic **post–WFM handoff** without building formalizer or Z3.
2. **Test** extraction, retrieval, and **registry-resolved NL** with real or stubbed embeddings.
3. **Iterate prompts** for search/gaps/resolve with **fast feedback** (fixture in → trace out).
4. **Show stakeholders** automated resolve traces (success + structured failure) and dev exports early; interactive UX comes later if product needs it.
5. **Produce dev artifacts** that **map 1:1** to **`registry_persistence_v1`** so **Phase 2** adds formalizer → production commit without renaming fields.
6. **Optionally warm-start** from a growing `registry.json` once you start persisting dev sessions.

---

## Automated LLM resolution (Phase 1, normative spec)

Former standalone **`REGISTRY_AUTOMATED_RESOLUTION_PLAN.md`** merged into this document **2026-04-04**. **M4** implements this section. **Canonical vocabulary** (`statement_nl`, `pre_resolved_nl`, `registry_resolution_candidate_nl`, `registry_resolved_nl`): see archived interactive design **`archive/registry_resolution_interactive_design/REGISTRY_RESOLUTION_DESIGN_OPEN_ISSUES.md`** **§A.1** (reference only).

**Assumption:** Search + gap extraction usually produce **good** hits and gaps, so resolution is **mostly** substitution / light rephrase into **`registry_resolution_candidate_nl`**, then commit to **`registry_resolved_nl`** when checks pass.

### Flow (happy path)

1. **Input:** `statement_nl`, authoritative hits, structured gaps (from line driver / M3).
2. **LLM resolve:** Single structured call → **`registry_resolution_candidate_nl`** + mapping metadata + optional flags (`confidence_tier`, `primary_review_reason`, etc.—schema aligned with archived design **A.4**).
3. **Validate:** Referential closure (cited `entry_id`s in session), basic guardrails (archived design **A.7** layers—start with **strict** rules: fail if uncertain).
4. **Commit:** If validation passes → set **`registry_resolved_nl`** = accepted candidate; persist trace (archived design **A.12** skeleton).
5. **Fail:** If validation fails or model output unusable → **terminate line** with **error code + reasons** (reuse reason enum where useful); full attempt logged.

### Retry / loop budgets *(locked)*

| Mechanism | Adopted for Phase 1 |
|-----------|---------------------|
| **Validation retry** | **2** re-prompts after bad JSON / id mismatch / guardrail fail (archived design **A.4**; max **3** model calls in that chain). |
| **Automatic outer re-search** | **0** — fail fast with an inventory/closure-style reason; no burning **`R`** in automated-only v1. |
| **User rounds (`K`)** | **0** (deferred). |
| **“Try again” after soft model low confidence** | **No** separate loop — either pass validation and commit, or fail the line. |

### Auto-accept rule

Only one outcome for success: **programmatic commit** (there is no **`USER_ACCEPTED`** yet). **Adopted predicate** (see **Success predicate** below): do **not** commit unless **`needs_human_review == false`**, **`primary_review_reason == NONE`**, **`confidence_tier == high`**, and no other review/doubt signals — any doubt → **fail the line** with logged reasons (stricter than the minimum **A.3** v1 list in the archived doc; appropriate when there is no reviewer).

### Resolve step — explicitly deferred (not contradicted by “Phase 1 out of scope” below)

- Choice UI, diff UX, free-text, **`K`**, outer **`R`** user/policy orchestration (archived **A.5–A.6**, **A.9** outer path for humans).
- **Resolver vs M5 populate (contrast with archived A.11):** The **interactive** archive (`archive/registry_resolution_interactive_design/`, **A.11**) discusses **provisionals** and **draft** registry rows **inside** the resolve loop. **Phase 1 automated** does **not** do that: the **resolver** returns **`registry_resolution_candidate_nl`** + **`cited_entry_ids`** that must be ⊆ **authoritative** hits (**no** resolver-minted `entry_id`s). **Session growth is still required:** **[M5 — Populate](#m5--populate-session--traceability-bundle)** creates new **`sort_` / `ent_` / `fn_`** rows from **remaining gaps** **after** resolve and rebuilds the index. *This bullet rejects the archived “draft rows inside resolve” shape for Phase 1; it does **not** mean the registry stays empty.*
- Per-bundle “**must not auto-resolve**” flags: **not assumed** for this prototype (**Per-bundle “no automation”** below). If you never add such policy, treat every bundle the same for automated resolve.

### Adopted design choices (plain language)

**Status:** Recommendations below are **accepted** as the Phase 1 spec, **except** per-bundle “must not auto-resolve,” which is **out of scope**. **Note:** Guardrail **numeric** cutoffs (**Guardrail numbers**) are **tuned in implementation** using a small eval set after M4 smoke tests — **calibration**, not an open product decision.

#### Guardrail numbers (edit distance, similarity, “how close is close”)

- **Context:** Validation checks how far the candidate is from `statement_nl`, referential closure, “smuggled” logic, etc. Some checks need numeric cutoffs.
- **Adopted:** Start with **conservative placeholders** (tight distance limit, strict referential checks) and **fail the line** when a check is borderline — prefer **more lines erroring** over wrong commits. **Tune** those numbers from a **small fixed eval set** after M4 smoke tests, not speculatively up front.
- **Rationale:** No human in the loop; **bias toward error** until measurements justify relaxing thresholds.

##### Numerical guardrails — inventory (Phase 1; prevents silent drift)

**Rule:** Every **numeric** threshold below is either **locked** (with a pointer to where it was set), **planned** (with the intended eval or trigger), or **explicitly not used yet**. Revisit locked values when prompts, embeddings, fixtures, or models change.

| Knob | Where it applies | Current status | Empirical / next step |
|------|------------------|----------------|------------------------|
| **`authoritative_min_score`** | M3 retrieval — which hits count as **authoritative** | **Locked** default **0.35** (BGE+FAISS) after Protocol B on **`m3_retrieval_eval_*`**; subject to revision | **`registry_stage/REGISTRY_M3_EVAL_DECISIONS.md`** — re-run Protocol B sweep when expansion, index, or eval set changes |
| **`query_mode`**, **`masking_preset`** | M3 expansion + gap masking | **Locked** `single_concat`, `conservative` | Same eval doc (Protocol A); re-benchmark if prompts change materially |
| **Expansion / query caps** (max phrases, max chars, concat length) | M3 cost + drift control | **Defaults** in dev plan § M3; “adjust after empirical pass” | Revisit alongside Lane A when behavior degrades |
| **Success-predicate strictness** | M4 (`needs_human_review`, `primary_review_reason`, `confidence_tier`) | **Locked** policy (no numeric tuning — categorical) | Change only with product/policy decision, not a cutoff sweep |
| **Validation retry budget** | M4 bad JSON / validation feedback | **Locked** 2 retries (3 calls max in chain) | Increase only if logs show recovery worth the cost |
| **Edit distance / similarity** of candidate NL vs `statement_nl` (and related “smuggled text” checks) | M4 validator | **Not implemented** in code yet; named in this spec + M4 **Validate** row as **deferred** | Add checks + **calibrate cutoffs** on a **small resolve eval set** after M4 smoke (same bias: fail when borderline until data says relax) |
| **Top-2 score margin (ε)** in retrieval | M3/M2 search layer | **Not used** in Phase 1 infrastructure | **Ambiguity thresholds** § below — add after **score logs** exist; optional resolver-only ambiguity until then |

**Related:** M3 Lane A / Protocol B artifacts live under **`registry_stage/eval_runs/`** (often gitignored); decisions are summarized in **`REGISTRY_M3_EVAL_DECISIONS.md`**. **M4-side:** first resolve empirical note is **`registry_stage/REGISTRY_M4_EVAL_DECISIONS.md`** (**prompt + heuristic policy**, **2026-04-09**); **numeric** edit-distance row in this table remains **not implemented** until validator + calibration pass.

#### Resolver JSON schema (exact field names, nesting)

- **Context:** The model must return machine-readable structure aligned with archived **A.4** conceptually; exact JSON must be fixed in code.
- **Adopted:** One **versioned** schema (e.g. `resolve_v1`) with **required** keys: `registry_resolution_candidate_nl`, `needs_human_review`, `primary_review_reason`, `confidence_tier`, `llm_rationale_short`, plus `mappings` or `spans` as needed. **Reject** parse failures via the validation-retry path; **no** silent coercion.
- **Rationale:** One schema ties together prompt, validator, and trace export; retries fix **format**, not guessed fields.

#### Validation retries (bad JSON / failed checks)

- **Context:** Re-prompt limit trades cost vs rare recovery.
- **Adopted:** **2** re-prompts after the first failure (**3** calls max in that chain), per archived **A.4**. Do **not** increase beyond **2** until logs show real recoveries worth it.
- **Rationale:** Diminishing returns; automated mode should **fail** rather than loop endlessly.

#### Automatic re-search before giving up

- **Context:** A second search pass might fix stale hits; it also complicates deferred **`R`** / snapshot semantics.
- **Adopted:** **0** automatic outer re-search in v1 automated mode — **fail** with an inventory/closure-style reason and measure frequency in logs. Consider **1** auto re-search **only** if data shows a clear “second search fixes it” pattern without user input.
- **Rationale:** Smallest first path; outer loops stay deferred until justified.

#### Success predicate (auto-commit vs fail)

- **Context:** Model flags can express uncertainty (`needs_human_review`, reasons, confidence tier).
- **Adopted:** **Any** `needs_human_review == true` **or** `primary_review_reason != NONE` **or** `confidence_tier != high` → **do not commit**; **fail the line** with logged reasons (stricter than minimum **A.3** v1).
- **Rationale:** Without a UI, medium confidence must not land in **`registry_resolved_nl`**.

#### Per-bundle “must not auto-resolve” — out of scope (accepted)

- **Why this came up:** Some products mark bundles **no automation** for contracts, regulated domains, pilots, or audit. The archived interactive doc (**A.14**, **`POLICY_REVIEW_REQUIRED`**) leaves room for that.
- **Adopted (out of scope):** No such bundle flag in Phase 1 — **no** extra branching or skip rules for policy bundles.
- **If that ever changes:** Reintroduce as product config + skip line, fail, or merge with interactive workflow — **out of scope** until then.

#### Ambiguity thresholds in retrieval (top-2 scores, “two good matches”)

- **Context:** Two plausible hits with similar scores might warrant an ε margin rule.
- **Adopted:** For automated-only v1, **no** ε in search infrastructure — let the **resolver** surface ambiguity in structured output and **fail** if it does. Add deterministic top-2 margin checks **after** score logs exist.
- **Rationale:** Search/extraction assumed strong; second layer waits on **data**.

#### Trace detail and redaction (logs for testing)

- **Context:** Traces must be useful for debug yet not leak unbounded sensitive text in shared artifacts.
- **Adopted:** Log **full** resolver JSON + validation outcome in **dev / test**; for shared exports, truncate long strings or store **hashes** until a redaction policy exists. Document what lands in **M5** export.
- **Rationale:** Reproducibility first; hygiene tightens when policy exists.

#### Merging back the full interactive workflow later

- **Where the full-branch design lives:** **`archive/registry_resolution_interactive_design/`** (not Phase 1).
- **Context:** That design has **K**, **R**, review UI — off in Phase 1; traces must remain coherent when interactive mode returns.
- **Adopted:** Keep **`registry_resolution_candidate_nl`** vs **`registry_resolved_nl`** from day one; automated success = commit **without** `USER_ACCEPTED`. Tag traces with **`resolve_mode: automated_v1`** (or equivalent).
- **Rationale:** Stable vocabulary and one commit field; comparable regression tests when interactive mode ships.

**Quick index (adopted choices):**

| # | Topic | Heading above |
|---|--------|----------------|
| 1 | Guardrail numbers + inventory | Guardrail numbers → Numerical guardrails — inventory |
| 2 | Resolver JSON schema | Resolver JSON schema |
| 3 | Validation retries | Validation retries |
| 4 | Auto re-search | Automatic re-search before giving up |
| 5 | Success predicate | Success predicate |
| 6 | Per-bundle “no automation” (not in scope) | Per-bundle “must not auto-resolve” |
| 7 | Top-2 / ε | Ambiguity thresholds in retrieval |
| 8 | Trace / redaction | Trace detail and redaction |
| 9 | Full workflow merge | Merging back the full interactive workflow later |

### Merge assessment — do M0, M1, or M2 reopen?

**No.** Consolidating this spec into the dev plan does **not** change M0–M2 exit criteria or undo “**Done**” tasks.

| Milestone | Still closed? | Optional follow-up (does not reopen the milestone) |
|-----------|---------------|------------------------------------------------------|
| **M0** | **Yes** | Packaging and fixture layout unchanged. |
| **M1** | **Yes** | When **M4/M5** land, extend **`export_session` / `DevSessionSnapshot`** with resolver trace fields (`registry_resolution_candidate_nl`, `resolve_mode`, raw resolver JSON) — an **additive** export evolution, not a redo of handoff loading. |
| **M2** | **Yes** | Automated resolve may **read** hit scores for future ε rules; § **Ambiguity thresholds** defers ε until logs exist — **no** required change to `RegistrySession.search` / FAISS wrapper for Phase 1. |

---

## Phase 2 pointer (not scheduled here)

After M0–M6, you can **design and implement** the rest of **`pipeline_spec.md`** **steps 4–8** in a **separate** plan:

| Step | Work (summary) |
|------|----------------|
| **4** | Formalizer LLM on **`registry_resolved_nl`** + registry context → Z3/Python artifact. |
| **5** | Z3 parse/type check. |
| **6** | Identifier extraction + fuzzy match + critic LLM. |
| **7** | Repair loop (errors back to formalizer, iteration budget). |
| **8** | User-approved **production commit**: `rules.json`, **`committed_edges`**, **`registry.json`**, **`bundles/*.pipeline.json`** per *Failure / commit contract*; full **`validate_alignment`**. |

Until that plan exists, **steps 4–8 are not** in the “what you can do after” list for **Phase 1** — by design, Phase 1 stops at the **output that step 3 hands to step 4** (**`registry_resolved_nl`** + session registry context; see **`pipeline_spec.md`** step 4).

---

## Document history (meta)

| Date | Change |
|------|--------|
| 2026-04-04 | Merged former **`REGISTRY_AUTOMATED_RESOLUTION_PLAN.md`** into **Automated LLM resolution (Phase 1, normative spec)**; stub file kept at repo root for bookmarks. |
| 2026-04-05 | **M3 Lane A:** table added — raw result fields, thin JSONL harness (comparable runs), business-domain eval fixtures, `authoritative_min_score` logging/tuning, deferred replay. |
| 2026-04-08 | **M3 Lane A implemented:** `line_driver` raw fields, `m3_lane_a` CLI, **`eval_fixtures/m3_business_*.json`**, tests. |
| 2026-04-08 | **M3 eval protocols:** Retrieval fixtures + labels (`m3_retrieval_eval_*`); **Protocol A** locked **`masking_preset=conservative`**, **`query_mode=single_concat`** (see **`registry_stage/REGISTRY_M3_EVAL_DECISIONS.md`**). **Protocol B** sweep helper: **`m3_protocol_b_minscore`** (single_concat + conservative, one JSONL per `--scores` value). |
| 2026-04-08 | **BGE+FAISS `authoritative_min_score` default** set to **0.35** in `default_authoritative_min_score` (Protocol B rerun); **subject to revision** with broader empirical eval — see **`REGISTRY_M3_EVAL_DECISIONS.md`**. |
| 2026-04-08 | **M4 (partial):** `run_automated_resolve`, `resolve_v1` prompt + parser, strict validation + retries; **`registry_stage/__version__`** → **0.0.m4**. M5 trace/export integration still open. |
| 2026-04-09 | **Clarify A.11 vs M5** (resolver does not mint rows; **M5** grows session). **Numerical guardrails — inventory** table (M3 locked vs M4 deferred vs ε). **M6** stakeholder **two-bundle warm-registry** demo as explicit **post-milestone todo**. **Risks:** no human gate before **M5** populate. |
| 2026-04-09 | **M5 shipped:** `populate_session.py`, `bundle_workflow.py` (`run_bundle_through_registry`), `loaders.save_registry`, tests **`test_m5_bundle_workflow.py`**. **M6 CLI:** `python -m registry_stage.run`. **`__version__`** **0.0.m5**. **Next empirical pass:** resolve-side eval / numeric guardrail calibration once traces from real bundles are exported (`--export`). |
| 2026-04-09 | **M4 warm-registry harness:** `python -m registry_stage.m4_warm_eval --out registry_stage/eval_runs/m4_warm_eval.jsonl` — fixtures **`eval_fixtures/m4_warm_*_bundle.json`**, protocol **`m4_warm_eval_v1`** (JSONL header + per-line rows for seed then reuse). |
| 2026-04-09 | **M4 empirical (prompt + pipeline):** Gap / search-expand / resolve prompt refresh; **`line_driver`** — no heuristic merge into **`gap_spans`** when LLM extraction on. Summarized **`registry_stage/REGISTRY_M4_EVAL_DECISIONS.md`**. **Numeric M4 guardrails:** unchanged (still deferred). **M6 README** demo section completed. |
