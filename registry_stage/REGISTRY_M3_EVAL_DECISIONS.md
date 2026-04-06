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
| 9 | **Which example lines + which fake “registry” rows** | **Open** — see below |
| 10 | **Code shape: expose “raw LLM before masking”** in results | **Open** — see below |
| 11 | **Where files are saved** — folder, gitignore vs commit | **Open** — see below |
| 12 | **What to stamp on each run** — model name, date, git commit, prompt version | **Open** — see below |
| 13 | **Extra CI beyond default** — optional nightly live job with API key? | **Open** — see below |
| 14 | **When you read prompts** — before first live dump vs after | **Open** — see below |

---

## Open items — simple explanations + recommendations

### 9. Example lines + seeded registry (“the homework set”)

**What you’re deciding:**  
For each eval run you need a **small list of English lines** (like real `statement_nl` from a handoff) and a **tiny in-memory registry** (a few sorts/constants/functions) so search/hits mean something.

**Why it matters:**  
Garbage in → garbage out. If the registry is empty or irrelevant, you learn nothing about retrieval; if lines are too easy, you won’t stress the prompts.

**Recommendation:**  
Start with **N = 5–10** lines: mix **2–3** from `bundles/fixture_bu_001.json`, plus **2–3** hand-written lines that mention **made-up company/product names** (like BetaCorp) so gaps are obvious. Use **one fixed registry fixture** (same 5–10 entries) for **all** lines first; add a second “richer” registry later only if needed.

---

### 10. Pre-mask hooks (“show me the LLM before you filtered it”)

**What you’re deciding:**  
Today the pipeline may **merge and mask** gaps inside one function. For eval you need the **exact JSON-shaped gaps Gemini returned** **before** masking drops anything—otherwise you can’t tell if a problem is **prompt** vs **masking**.

**Why it matters:**  
You already agreed to record **raw extraction**; the code must **surface** that object on the result (or a side channel) without guessing from logs.

**Recommendation:**  
Extend the **result object** (e.g. `LineSearchGapsResult`) with fields like `raw_expansion_phrases` (parsed list) and `raw_structured_gaps` (list of dicts/structs **before** `candidate_covered`). Keep current `structured_gaps` as **post-mask**. Same for expansion if anything truncates before search.

---

### 11. Artifact path + git policy (“where do JSONL files live?”)

**What you’re deciding:**  
Lane A produces **files** (one line per row or per run). Should those live under `registry_stage/eval_runs/`? Should git **ignore** them (private noise) or **commit** selected baselines for replay tests?

**Why it matters:**  
Avoid accidental commit of huge logs or API-ish data; still allow **one** checked-in “golden transcript” set for Lane B replay if you want it.

**Recommendation:**  
- **Default:** write under `registry_stage/eval_runs/` and add that folder to **`.gitignore`**, except an optional subfolder `recorded_fixtures/` you **do** commit (small, hand-curated JSON for replay).  
- **Naming:** include date + short label, e.g. `eval_20260404_promptv1.jsonl`.

---

### 12. Run metadata (“how do I know what produced this file?”)

**What you’re deciding:**  
Each artifact row (or file header) should say **which model**, **which git commit**, **which prompt files**, **which caps**—so two JSONL files are comparable.

**Why it matters:**  
Without stamps, you’ll compare apples to oranges after any prompt tweak.

**Recommendation:**  
At minimum per **file** (header object): `git_commit_short` (optional if not in git), `gemini_model` from env, `timestamp` UTC, **SHA256 or content hash** of both prompt files. Per **row**: `example_id`, `query_mode`, `masking_preset`, `line_index` if any.

---

### 13. Optional CI beyond “default pytest”

**What you’re deciding:**  
Default CI skips live calls (**agreed**). Do you also want a **scheduled** GitHub/GitLab job (weekly/nightly) with **`GEMINI_API_KEY`** secret that runs Lane A automatically?

**Why it matters:**  
Catches regressions when Google changes behavior or when someone edits prompts without running eval locally.

**Recommendation:**  
**Phase 1:** no automated live CI—run Lane A **on demand** before M4 lock-in. **Phase 2:** add **optional** nightly job once prompts stabilize and fixture replay covers most merges. Keeps cost and noise down early.

---

### 14. Prompt review timing

**What you’re deciding:**  
Do you edit `registry_stage/prompts/*.md` **before** the first big JSONL dump, or run once on “v0” prompts and then edit based on artifacts?

**Why it matters:**  
Purely workflow; both work.

**Recommendation:**  
Do a **quick human read** of both prompts **before** the first live eval (catch obvious omissions), then treat the **first JSONL** as the real feedback loop. No need to block on perfection.

---

## Summary

- **Resolved:** 6-way matrix, three recording layers, fair comparisons, no live in default CI, no strict prose goldens, structural checks only, fixture replay as a future pattern.  
- **Open:** concrete example set + registry seed, small code visibility for pre-mask outputs, artifact folder policy, metadata fields, optional nightly CI, prompt review cadence—with **concrete recommendations** above for each.

When these open rows are filled in, you’re ready for a short **test development plan** (who runs Lane A, how to invoke it, exact JSONL schema), then implementation.
