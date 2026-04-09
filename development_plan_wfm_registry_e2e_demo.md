# Dev plan — WFM → registry workflow end-to-end demo

**Purpose:** Ship a **single stakeholder-facing story**: choose input (curated or manual) → run **manual WFM** to user acceptance → **automatic** registry stage (**`pipeline_spec.md`** step 3 through populate / dev export, **before** formalizer) → optionally **readable** reports at each stage.

**Authoritative specs:** **`pipeline_spec.md`**, **`registry_persistence_v1.md`**, **`development_plan_registry_stage_v1.md`** (M0–M6), **`WFM/Agent_WFM.md`**, **`test_sets/README.md`**.

---

## Relation to M0–M6 (scope check)

**Yes — for registry behavior from a valid WFM-style handoff through the end of step 3 (pre-formalizer), the M0–M6 implementation is sufficient.** `run_bundle_through_registry` + `python -m registry_stage.run` already exercise **search → gap extraction → automated resolve → populate** with traces and export.

What this demo plan adds is **not** another registry milestone — it is **orchestration and presentation**:

| Area | M0–M6 status | Demo plan |
|------|----------------|-----------|
| Registry pipeline on `HandoffBundle` | **Done** | Call existing APIs / CLI |
| WFM Agents 1–3 (+ optional 4) interactive harness | **Done** (`test_sets/scripts/`) | Reuse; document paths |
| **One** command: menu → WFM → **handoff JSON** → registry | **Not done** | **Build** launcher + handoff builder |
| Readable per-step viewers | **Not done** | **Add** read-only formatters |

The registry dev plan still lists the **two-bundle warm-registry exercise** as a **process guard** (proof, not missing code). This demo should **include** that story as a **variant** (seed bundle → `--save-registry` → reuse bundle with `--registry`) when showcasing entity reuse.

---

## 1. Demo launcher (input choice)

**Intent:** Start from a small **menu**:

1. **P-FOLIO** — random choice from a **pre-curated** list of example ids / texts (same source family as **`test_sets/wfm_folio_pffolio_examples_en.md`** / PF-* blocks).
2. **FOLIO** — random from curated **F-*** examples (same file, **## FOLIO** section).
3. **Stress** — random from curated **R-\*** / **E-\*** examples (**`test_sets/wfm_stress_examples_en.md`** or existing stress harness lists).
4. **Manual** — operator types/pastes NL subject to a **word cap**.

**Curated lists:** Checked-in JSON or Markdown index files (ids + pointers into existing example files) so the demo does not depend on scraping at runtime. **Random:** use `random.choice`; optional **`--demo-seed`** for reproducible stakeholder runs.

**Manual input word cap:** Compute **once** (script or documented constant):

- Measure **word count** (whitespace-split, English) for **each** curated FOLIO + P-FOLIO + stress block you allow in the demo lists.
- Set **`MANUAL_INPUT_WORD_LIMIT` = max(all those counts) + N`**, with **`N`** in **10–20** per product preference (pick one default, e.g. **15**, and document it next to the constant).

Enforce the cap **before** WFM starts; reject or ask with a clear message if over.

**Deliverable:** `test_sets/scripts/demo_wfm_registry_launcher.py` (name TBD) — **thin**; delegates to existing WFM entry points where possible.

---

## 2. WFM phase (same manual experience you already use)

**Intent:** After input selection, **the same interactive WFM demo** you already ran: full **user-visible** control flow reachable via **manual** choices (confirmation, disagreement / omit paths as applicable, **Agent 4** when using the interactive harness, etc.).

**Concrete mapping today (Gemini-oriented):**

- **Agents 1→3 batch** on folio/pfolio/stress: **`python test_sets/scripts/run_wfm_folio_gemini.py`** (flags **`--pfolio`**, **`--stress`** as today).
- **Agent 4 + confirmation disagree / merge preview:** **`python test_sets/scripts/run_wfm_agent4_interactive.py`** and/or **`run_wfm_agent4_from_run.py`** as in **`test_sets/README.md`**.

**Important caveat (document in demo README):** **`test_sets/README.md`** states that **automatic** “merged Style A → full **Agent 1** re-entry” in **one** process is **orchestration not implemented yet** — the operator may need to **paste** merged text back into **`run_wfm_folio_gemini.py`** (or a future single orchestrator). The demo plan should either:

- **(A)** Treat that as **current truth** for v1 and document the manual hop in the **runbook**, or  
- **(B)** Add a follow-up milestone **“close the Style-A loop inside one launcher”** (optional, larger).

**Deliverable:** Demo **runbook** section listing exact commands + when to use Agent 4; launcher ties steps together **as far as existing code allows**, with explicit stops where the repo still requires manual handoff.

---

## 3. Handoff JSON → registry (automatic after acceptance)

**Intent:** Once the user has **accepted** the confirmation package (per **`WFM/Agent_WFM.md`**), produce a **`HandoffBundle`** JSON file compatible with **`registry_stage.loaders.load_handoff_bundle`** — same shape as **`bundles/fixture_bu_001.json`** (**`registry_persistence_v1`** schema / `schema_version: registry_persistence_v1`).

**Gap:** Today, WFM harnesses emit **Markdown / JSONL** artifacts, **not** the canonical handoff JSON. This is **the main new technical piece** for true e2e.

**Deliverable:**

- **`wfm_acceptance_to_handoff_bundle(...)`** (module location TBD, e.g. under `test_sets/` or a small `orchestration/` package): inputs = structured acceptance state you already have at “go to registry” time (per-line **`statement_nl`**, **`agent3_verdict`**, optional scope/diff, bundle-level audit fields); output = `Path` to written **`bundles/{bundle_id}.json`** or in-memory dict passed to **`run_bundle_through_registry`**.

- **Validation:** `load_handoff_bundle(path)` must succeed; optional **`handoff_bundle_to_dict`** round-trip test.

- **Launcher:** After builder succeeds, invoke **`python -m registry_stage.run --bundle <path> ...`** (or in-process `run_bundle_through_registry`) with **`--export`** / **`--save-registry`** as needed for the warm-registry story.

**Registry stage:** Remains **fully automatic** for Phase 1 (no manual resolve UI) — aligns with M4–M5.

---

## 4. Readable per-step reports (read-only)

**Intent:** Stakeholders can **inspect** what each major stage did **without** diffing raw JSON.

**Registry stages (map to traces already produced by `bundle_workflow`):**

| Narrative step | Primary source in export / trace |
|----------------|----------------------------------|
| **Search** | `hits`, `authoritative_hits`, scores; expansion / backend labels as logged |
| **Extract (gaps)** | `gap_spans`, `structured_gaps` / raw structured gaps |
| **Resolve** | `registry_resolution_candidate_nl`, validation, `raw_resolver_json`, `failure_reasons` |
| **Populate** | `new_entry_ids` (and/or session diff vs pre-run registry) |

**WFM:** Markdown reports under **`test_sets/run_results/`** are already fairly readable; optional **HTML or rich terminal** summary can **wrap** the same files (no mutation).

**Requirements:**

- Scripts **only read** existing outputs (JSON export, JSONL rows, Markdown) and write **new** human-oriented files (e.g. **`demo_out/<run_id>/registry_step_search.md`**) or print to stdout.
- **Do not** alter source artifacts in place.

**Complexity:** **Low to moderate** — mostly templating and field selection; **worth doing** for demos. Edge cases (very long `statement_nl`, huge hit lists): truncate with “show first K + count” in v1.

**Deliverable:** e.g. `test_sets/scripts/render_registry_trace_readable.py --export path/to/session.json --out demo_out/...` and optional `render_wfm_run_readable.py` for JSONL → compact timeline.

**Timing:** Can land **in parallel** with launcher once a stable **`--export`** path exists; polishing can continue after first successful e2e.

---

## 5. Suggested implementation order

| Phase | Work | Exit criterion |
|-------|------|----------------|
| **P0** | Handoff builder + validate with `load_handoff_bundle` | One real acceptance → JSON → `registry_stage.run` succeeds |
| **P1** | Launcher menu + curated lists + manual word cap + runbook | Stakeholder can run F/P/stress/manual without editing paths |
| **P2** | Readable registry + WFM renderers | Side-by-side folder with one page per stage |
| **P3** | Warm-registry two-run story | Documented in same runbook; optional scripted subcommand |

---

## 6. Clarifications / issues to resolve early

1. **Which WFM backend for the “canonical” demo** — Gemini (`run_wfm_folio_gemini.py`) vs Claude (`run_wfm_folio_claude.py`): pick default for runbook; second path optional.
2. **Bundle id / timestamps** — who generates **`bundle_id`** and **`wfm_pipeline_timestamps.confirmation_accepted_utc`** at acceptance time (launcher vs builder).
3. **Style-A loop** — confirm acceptance of **(A)** manual re-feed vs **(B)** building automated loop (schedule).
4. **Random stress examples** — some stress cases may **terminate early** (by design); runbook should say “reroll or pick another” if the demo must always reach registry.

---

## 7. After this demo

- **Edit distance / similarity** guardrails remain **post–demo** per **`development_plan_registry_stage_v1.md`** (Guardrail numbers).
- **Phase 2** formalizer / Z3 — out of scope for this plan.
