# Manual scenario — WFM confirmation / Agent 4 entry point

**Purpose:** Human-driven (or future scripted) exercise that **starts after Agent 3**, at the **confirmation package**, including **structured disagreement**, **`WFM_PATCH`**, **programmatic merge**, **Style A** NL for Agent 1 re-entry, and awareness of **outer** WFM rerun budget.

**Normative spec:** `asp/wfm/Agent_WFM.md` (Confirmation package, Agent 4, Patch merge). **Agent 4 prompt:** `asp/wfm/prompts/agent_4_user_interaction.md`.

**Fixture source (realistic package):** Stress harness **R-1** from `test_sets/run_results/wfm_stress_gemini_20260404_151309Z.md` — mixed **PASS**, **OUT_OF_SCOPE**, and **REWRITE**. Optionally duplicate with **F-2** from `wfm_folio_gemini_20260404_133907Z.md` for an all–in-scope shorter path.

---

## Preconditions

- Orchestration (or a test harness) holds the **authoritative** numbered list **as shown to the user** (1-based indices).
- User has **not** yet accepted the full package.
- Optional: copy Agent 2/3 text from a run artifact into a scratch UI so the exercise does not require re-running Gemini.

---

## Fixture A — R-1 confirmation snapshot (abbreviated labels)

Use these **eight** lines as the **confirmation list** (text = Agent 2 / Agent 3 display basis; align with the Gemini run for verbatim fidelity when testing).

| Idx | Sub-statement (representative) | Agent 3 label |
|-----|--------------------------------|---------------|
| 1 | Northwind assigns every field agent to exactly one regional lead. | PASS |
| 2 | … regional lead to exactly one operations director. | PASS |
| 3 | … operations director to exactly one VP logistics. | PASS |
| 4 | … VP to the chief operating officer. | PASS |
| 5 | Internal policy defines reachability… finite chain… | **OUT_OF_SCOPE** |
| 6 | If an employee can escalate to the COO, then urgent capital requests… auto-approved… | PASS |
| 7 | Avery is a field agent. | PASS |
| 8 | In conclusion: if Avery can escalate… through the reporting chain, then… | **REWRITE** (see run for full REWRITE line) |

*(Full strings: copy from the run file for serious regression work.)*

---

## Scenario 1 — Partial disagree + `WFM_PATCH` replacements only

**Goal:** User accepts some lines, disagrees with **two** lines, supplies **two comments**, Agent 4 returns **replacements** for those indices only; merge + Style A; hand off to Agent 1.

**Steps**

1. **Display** the confirmation package with indices **1–8** and Agent 3 verdicts.
2. User **does not disagree** with lines 1, 2, 3, 4, 7 (implicit accept).
3. User **disagrees** with:
   - **Line 6** — comment: e.g. “Auto-approval should be capped at manager level, not director.”
   - **Line 8** — comment: e.g. “Remove the reporting-chain qualifier entirely; use the REWRITE form.”
4. Optionally user already **confirmed omit** line 5 in the UI *or* will address it in Scenario 2 — for Scenario 1 assume line 5 is **still pending** (orchestration must **block** merge until every **OUT_OF_SCOPE** line is **replace** or **confirmed omit** per `Agent_WFM.md`).  
   - **Adjustment for a minimal first run:** Treat line 5 as **user confirmed omit** in the UI before Agent 4 so merge is valid.
5. Invoke **Agent 4** with structured payload: full list, labels, disagreed `{6, 8}`, comments, **`omit_indices` from UI:** `{5}` if user confirmed omit for the reachability rule.
6. Expect Agent 4 **user-facing** plain-language reply plus **one** markdown fenced block tagged **`wfm_patch`** whose body is JSON with **only** `replacements` for indices **6** and **8** (the model must **not** emit `omit_indices`; omits come from the UI).
7. **Validate** patch: only `{6, 8}` appear; texts non-empty; no other indices.
8. **Merge (orchestration):** apply replacements; drop line 5; **renumber** 1…K; build **Style A** NL:

   ```
   1. <line 1 text>
   2. <line 2 text>
   ...
   ```

9. Optional **final merged preview** — user confirms.
10. **Re-run** `Agent 1 → 2 → 3` on the Style A string; decrement **outer** rerun budget per `Agent_WFM.md`.

**Pass criteria:** Merged NL reproduces **accepted** lines **verbatim**; replaced lines match validated patch; omitted index absent; Style A formatting identical across harnesses.

---

## Scenario 2 — OUT_OF_SCOPE: explicit omit vs disagree+replace

**Goal:** Exercise **both** allowed OOS outcomes.

**Variant 2a — Confirmed omit**

- Line 5: user checks **“exclude from rule bundle”** and confirms (or equivalent). Orchestration records `omit_indices: [5]` for merge **without** Agent 4 inventing omit.

**Variant 2b — Pursue replacement**

- Line 5: user **disagrees** + comment asking for an in-scope paraphrase (e.g. drop transitive closure, use a single-step relation). Agent 4 proposes **replacement** text for index 5 in `replacements`; **no** omit for 5.

**Pass criteria:** No OOS line left **unresolved** (no silent drop).

---

## Scenario 3 — Blanket disagree

**Goal:** User selects **all** lines; must supply **N comments** (N = 8 in Fixture A). UI may **replicate** draft text into 8 fields but persistence is **eight distinct comments**.

**Pass criteria:** Orchestration refuses to call Agent 4 until **8/8** comments non-empty; Agent 4 patch may replace up to 8 indices (subject to any confirmed omits).

---

## Scenario 4 — Agent 4 retry / invalid patch

**Goal:** Regression for validation.

1. Simulate Agent 4 patch that includes a **non-disagreed** index → orchestration **rejects**; counts as retry per product rules.
2. Simulate malformed JSON in `wfm_patch` → reject + retry.

---

## Scenario 5 — Final merged preview rejected (placeholder)

**Current spec:** User rejects the **post-merge** preview → **abort** / reset to user input (no extra Agent 4 loop defined). Manual test should **document** actual product behavior once implemented.

---

## Artifacts to record

- Snapshot of confirmation package (JSON or Markdown).
- Per-line comments, omit confirmations, Agent 4 transcript.
- Parsed `wfm_patch`, **effective** patch after UI merge, merged list, **Style A** `nl_for_agent1`.
- Result of subsequent WFM pass (or pointer to new run file).

---

## Automated driver (implemented)

**Script:** `test_sets/scripts/run_wfm_agent4_from_run.py`

From repo root, e.g. `C:\Users\Zubin\Documents\Project_Cursor\Project_Cursor` (see **`test_sets/README.md`** for full command lines).

1. Point **`--run-jsonl`** at one `wfm_folio_gemini_*.jsonl`, `wfm_pfolio_gemini_*.jsonl`, or `wfm_stress_gemini_*.jsonl` produced by **`run_wfm_folio_gemini.py`**.
2. **`--list-eligible`** prints **`example_id`** values you can pass as **`--example`** (`F-4`, `R-1`, `PF-2`, `E-3`, …). Rows with **Agent 2 `LIMIT_EXCEEDED`** or **Agent 3 skipped** are excluded.
3. **`--dry-run`** prints the structured payload (Agent 2 + Agent 3 verbatim + your disagree/omit slots) without calling the API.
4. Live run: **`--example`**, **`--disagree`** (comma-separated 1-based indices), **`--comments-file`** (one non-empty line per disagreed index, same order), optional **`--omit-confirmed`**, optional **`--merge-preview`** to parse the response’s fenced block tagged **`wfm_patch`** and print **Style A** merged NL (best-effort validation).

**CLI + manual scenario:** Use the script to pick the fixture by id; use the scenarios below for what to assert and how to exercise OOS omit vs replace.

---

## Automation path (later extensions)

- **Input:** YAML/JSON fixture with expected effective patch / golden Style A string for CI.
- **Optional:** chain **Agents 1→3** re-run on merge preview output inside the same harness.
