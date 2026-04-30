# Gemini WFM runs — summary and verdict

Reference machine work; all runs use **`gemini-3.1-pro-preview`**, **`temperature = 0`**, **`max_output_tokens = 16384`**, **`GEMINI_THINKING_LEVEL=low`** (default), and **`compound_operator_limit: 8`** from `asp/wfm/config/wfm.json`. Agent 4 was not invoked.

Artifacts live under **`test_sets/run_results/`** (Markdown + JSONL per run).

---

## Runs recorded

| Run | Output basename (UTC) | Example set | Examples |
|-----|------------------------|-------------|----------|
| FOLIO | `wfm_folio_gemini_20260404_133907Z` | `folio` (F-*) | 10 |
| P-FOLIO | `wfm_pfolio_gemini_20260404_141451Z` | `pfolio` (PF-*) | 10 |
| Stress | `wfm_stress_gemini_20260404_151309Z` | `stress` (R-*, E-*) | 12 |

Commands used (from repo root):

- `python test_sets/scripts/run_wfm_folio_gemini.py`
- `python test_sets/scripts/run_wfm_folio_gemini.py --pfolio`
- `python test_sets/scripts/run_wfm_folio_gemini.py --stress`

---

## Overall verdict

**Fit for purpose:** Gemini **3.1 Pro** under this contract is a **solid** driver for the **Agents 1 → 2 → 3** WFM smoke path: stable multi-step calls, usable outputs for human/scorecard review, and **reasonable** alignment with `asp/wfm/prompts/agent_{1,2,3}_*.md` and `Agent_WFM.md` control flow (including **`LIMIT_EXCEEDED`** gating when Agent 2 trips the compound-operator budget).

**Strengths**

- **FOLIO & P-FOLIO:** Reliable normalization (quantifiers, structure), numbered Agent 2 lists, and mostly sensible **PASS / REWRITE** patterns for registry-ward text.
- **Stress — rejects:** Strong **OUT_OF_SCOPE** detection on **unbounded domains**, heavy **temporal / history** wording, **vague “most”**, and **higher-order / hypothetical** quantification in several cases; **R-6** hit **`LIMIT_EXCEEDED`** at Agent 2 as intended.
- **Stress — edges:** **E-1** (guarding conjunctive antecedents) and **E-4** (iff + numeric chain) behaved like **clean in-scope** benchmarks.

**Weaknesses / watch list**

- **Open-ended lists:** Same class of gap as FOLIO **F-5** — vague symptom / “similar complaints” style text (**E-2**) can get **all PASS** instead of **OUT_OF_SCOPE** or tightening.
- **Stress logic quality:** Not every “reject” ends cleanly — e.g. **R-3** produced a **non-equivalent REWRITE** on one line; **R-5** mixed **OUT_OF_SCOPE** premises with **PASS** conclusions; **R-1** conclusion **REWRITE** risked **weakening** path-dependent meaning.
- **Scope aggressiveness:** “**until**” / time phrases sometimes flagged **OUT_OF_SCOPE** even when a product might treat them as static snapshots (**E-3**, branch line in **E-6**).
- **Agent 3 formatting:** Verdict lines are **semantically** clear but **not** uniform (`PASS: 1.` vs unnumbered **PASS**), which matters only if you add strict parsers.

**Bottom line:** Keep using this stack for **cross-API regression** and **human baseline** comparison; treat **OUT_OF_SCOPE** density and **enumeration / temporal** corners as the main areas to tighten in prompts or post-validation—not raw model swapping.

---

## Continuing on another device (no secrets in repo)

1. Clone **`https://github.com/ZubinK26/AutoV`**
2. `copy .env.example .env` (or equivalent) and set **`GEMINI_API_KEY`** / **`ANTHROPIC_API_KEY`** locally — **`.env` is gitignored; never commit it.**
3. `pip install -r test_sets/requirements-wfm-test.txt`
4. Re-run smoke tests as needed (`--dry-run` first optional).

Regression baselines: **`wfm_folio_expected_outcomes_manual_baseline.md`**, **`wfm_pfolio_expected_outcomes_manual_baseline.md`**.
