# Registry M3 eval — what’s decided vs open (plain language)

This file supports the **3×2 configuration matrix** (two query modes × three masking presets): run **six** full pipelines per example, record **raw expansion**, **raw extraction**, and **post-mask** outputs for prompt tuning—**without** using strict “golden text” checks on live Gemini.

---

## Lane A vs Lane B (agreed)

| Lane | What it’s for | Calls Gemini? |
|------|----------------|-----------------|
| **A — Live eval** | You (or a gated CI job with a key) run **6 × N** examples, save **JSONL** artifacts, compare runs, edit prompts, pick defaults **before M4**. | **Yes** |
| **B — Default CI** | Every normal `pytest` run: **fast, free, stable**. Uses **mocks** and, later, **replaying saved API responses** (fixtures) instead of calling Google. | **No** (by default) |

**Agreed:** default CI **does not** require live Gemini. That does **not** cancel Lane A—you still run Lane A **locally** (or in a separate job) when you care about real prompt behavior.

---

## Decision table (updated)

| # | Topic | Status |
|---|--------|--------|
| 1 | **6 combos** — `multi_query_fuse` / `single_concat` × `standard` / `aggressive` / `conservative` | **Resolved** |
| 2 | **Record three layers** — raw expansion JSON, raw extraction JSON, post-mask `gap_spans` / structured gaps (+ hits context) | **Resolved** |
| 3 | **Small N**, **no caching** between combos for the same line (full fidelity per config) | **Resolved** |
| 4 | **Fair comparison** — same registry + same lines + same prompts/caps; only query mode + masking change | **Resolved** |
| 5 | **Extractor uses search/authoritative** — chain order is fixed | **Resolved** |
| 6 | **No exact-string goldens** on live LLM text | **Resolved** |
| 7 | **Structural checks only** — no fuzzy “should have a gap here” rules until you’re sure | **Resolved** |
| 8 | **Fixture replay** (optional) — after recording, CI can re-run against **frozen** JSON for regression | **Resolved** (pattern agreed; implementation later) |
| 9 | **Which example lines + which fake “registry” rows** | **Resolved** — homework set per §9 |
| 10 | **Code shape: expose “raw LLM before masking”** in results | **Resolved** — extend result type per §10 |
| 11 | **Where files are saved** — folder, gitignore vs commit | **Resolved** — `eval_runs/` + ignore + optional `recorded_fixtures/` per §11 |
| 12 | **What to stamp on each run** — model name, date, git commit, prompt version | **Resolved** — file header + row fields per §12 (include optional fields) |
| 13 | **Live API in CI/schedulers** | **Resolved** — no automated jobs that call APIs; manual / explicit approval only per §13 |
| 14 | **When you read prompts** — before first live dump vs after | **Resolved** — pre-read + iterate from JSONL per §14 |

---

## Agreed items (reference)

### 9. Example lines + seeded registry (“the homework set”)

**What you’re deciding:**  
For each eval run you need a **small list of English lines** (like real `statement_nl` from a handoff) and a **tiny in-memory registry** (a few sorts/constants/functions) so search/hits mean something.

**Why it matters:**  
Garbage in → garbage out. If the registry is empty or irrelevant, you learn nothing about retrieval; if lines are too easy, you won’t stress the prompts.

**Recommendation:**  
Start with **N = 5–10** lines: mix **2–3** from `bundles/fixture_bu_001.json`, plus **2–3** hand-written lines that mention **made-up company/product names** (like BetaCorp) so gaps are obvious. Use **one fixed registry fixture** (same 5–10 entries) for **all** lines first; add a second “richer” registry later only if needed.

**Status:** **Agreed.**

---

### 10. Pre-mask hooks (“show me the LLM before you filtered it”)

**What you’re deciding:**  
Today the pipeline may **merge and mask** gaps inside one function. For eval you need the **exact JSON-shaped gaps Gemini returned** **before** masking drops anything—otherwise you can’t tell if a problem is **prompt** vs **masking**.

**Why it matters:**  
You already agreed to record **raw extraction**; the code must **surface** that object on the result (or a side channel) without guessing from logs.

**Recommendation:**  
Extend the **result object** (e.g. `LineSearchGapsResult`) with fields like `raw_expansion_phrases` (parsed list) and `raw_structured_gaps` (list of dicts/structs **before** `candidate_covered`). Keep current `structured_gaps` as **post-mask**. Same for expansion if anything truncates before search.

**Status:** **Agreed.**

---

### 11. Artifact path + git policy (“where do JSONL files live?”)

**What you’re deciding:**  
Lane A produces **files** (one line per row or per run). Should those live under `registry_stage/eval_runs/`? Should git **ignore** them (private noise) or **commit** selected baselines for replay tests?

**Why it matters:**  
Avoid accidental commit of huge logs or API-ish data; still allow **one** checked-in “golden transcript” set for Lane B replay if you want it.

**Recommendation:**  
- **Default:** write under `registry_stage/eval_runs/` and add that folder to **`.gitignore`**, except an optional subfolder `recorded_fixtures/` you **do** commit (small, hand-curated JSON for replay).  
- **Naming:** include date + short label, e.g. `eval_20260404_promptv1.jsonl`.

**Status:** **Agreed.**

---

### 12. Run metadata (“how do I know what produced this file?”)

**What you’re deciding:**  
Each artifact row (or file header) should say **which model**, **which git commit**, **which prompt files**, **which caps**—so two JSONL files are comparable.

**Why it matters:**  
Without stamps, you’ll compare apples to oranges after any prompt tweak.

**Recommendation — required per file (header object):**  
`timestamp` (UTC), `gemini_model` (from env at run time), **hash of each prompt file** (e.g. SHA-256 of `registry_search_expand.md` and `registry_gap_extract.md`), and **`query_mode` / `masking_preset` scope** if one file holds one full matrix run (or repeat per row — see below).

**Recommendation — include when available (optional but stamp when you have them):**  
`git_commit_short` / `git_commit_full`, repo **dirty flag**, **`wfm_compound_operator_limit`** (or other caps echoed from config), **`eval_protocol_version`** (string you bump when JSONL schema changes), **`operator` / `machine`** (who ran it).

**Recommendation — per row (minimum):**  
`example_id`, `query_mode`, `masking_preset`, `line_index` / `bundle_id` if applicable, and pointer to `statement_nl` or stable id.

**Status:** **Agreed** — use required + optional fields above so runs stay comparable and auditable.

---

### 13. Live API usage — no silent automation

**What you’re deciding:**  
Default CI skips live Gemini (**Lane B**, agreed). Whether **any** scheduled or automatic pipeline should call Google with a repo secret **without a human in the loop**.

**Policy (agreed):**  
- **Do not** add **cron**, **nightly**, or **on-push** CI jobs that call **Gemini** (or any paid API) using stored credentials. **Your consent must be explicit each time** paid/remote inference runs.  
- **Reminders only:** use calendar tasks, release checklists, or a doc note (“before merging prompt changes, run Lane A locally”) — not autonomous API jobs.  
- **CI that never surprises you:** keep **`pytest`** on **mocks + fixture replay** only. Replay files are **deterministic** and need **no** API key.

**If you later use GitHub Actions for Lane A anyway:**  
Use **`workflow_dispatch` only** (manual “Run workflow” button), document that the run **will charge** / call Google, and **do not** store secrets in workflows that trigger on `schedule` for this purpose. That preserves “approval each time” as **the act of clicking run** plus conscious use of a secret environment. If even that is too implicit, **only run Lane A on your machine** after exporting `GEMINI_API_KEY` in the shell — zero server-side automation.

**Status:** **Agreed** — no phase-based optional nightly jobs; reminders + manual/explicit runs only.

---

### 14. Prompt review timing

**What you’re deciding:**  
Do you edit `registry_stage/prompts/*.md` **before** the first big JSONL dump, or run once on “v0” prompts and then edit based on artifacts?

**Why it matters:**  
Purely workflow; both work.

**Recommendation:**  
Do a **quick human read** of both prompts **before** the first live eval (catch obvious omissions), then treat the **first JSONL** as the real feedback loop. No need to block on perfection.

**Status:** **Agreed** — prompts already read pre–first dump; iterate from JSONL after results.

---

## Summary

- **Resolved:** Full decision table (#1–#14): 6-way matrix, three recording layers, fair comparisons, no live calls in default CI, no strict prose goldens, structural checks only, fixture replay pattern, homework set (#9), pre-mask hooks (#10), artifact paths (#11), run metadata with **required + optional** header/row fields (#12), **no cron/nightly/API CI — reminders + manual or `workflow_dispatch` only (#13)**, prompt cadence (#14).
- **Next:** optional **Lane A runbook** (invoke command, JSONL schema) when you implement eval capture; keep **`pytest`** on mocks/replay only per §13.

When the runbook + schema exist, run the first **Lane A** matrix and lock M3 defaults before M4.