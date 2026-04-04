# FOLIO expected outcomes — manual simulation baseline

Reference simulation: **`Agent1-3_chat_sim_results.ipynb`** (chat export), run **manually in browser with Gemini 3.1 Pro** on the English FOLIO blocks aligned with `wfm_folio_pffolio_examples_en.md`.

This file is the **closest in-repo stand-in for intended behavior** when evaluating automated runs (any API / model). It records **outcome classes** and **role-level** Agent 3 verdicts, not a requirement for **verbatim** string match at every layer.

---

## Compound operator limit — read this first

The manual run predates **raising** the WFM compound-operator budget (notebook text cites **more than four** operators on the failing disjuncts; the frozen test harness today injects **`compound_operator_limit: 8`** from `WFM/config/wfm.json`).

**Implications for regression checks**

- **Per-line operator totals** under the counting rules will often be **higher** than what still fit under the old informal ceiling; sub-statements that previously forced **LIMIT_EXCEEDED** may now fall **within** the configured limit.
- **Downstream:** Agent 2 may emit a **full SUCCESS** list where the manual trace shows **LIMIT_EXCEEDED**; Agent 3 may then run on **additional** lines (or different splits) that the manual sim never reached. For those cases, judge **decomposition correctness** (especially **do not** illegitimately split unified conditionals or either/or bundles) rather than insisting on LIMIT_EXCEEDED parity.
- The **LIMIT_EXCEEDED** narratives in the table remain the **documented honest failure** for the **Bonnie** and **James** disjuncts **when** the budget is tight enough that the piece cannot be decomposed without meaning loss; they are **not** a guarantee that every future run must stop there once the limit is higher.

LIMIT_EXCEEDED presentation in product: manual notes require **verbatim offender**, **operator total**, and **trace** (categories + counted phrases) so the user can audit the stop condition.

---

## FOLIO examples not present in the notebook

| ID        | Status |
|-----------|--------|
| **F-2**   | Not captured in manual baseline |
| **F-6**   | Not captured in manual baseline |
| **F-7**   | Not captured in manual baseline |
| **F-10**  | Not captured in manual baseline |

Use this table for **F-1, F-3, F-4, F-5, F-8, F-9** only; for others, rely on corpus text plus general WFM prompts until a manual pass is added.

---

## Expected outcomes (by FOLIO ID)

Columns are **outcome classes**. Where the manual trace shows concrete wording, it illustrates **intent** (e.g. normalization to “every / at least one”, removal of “In conclusion” at Agent 3).

### Summary table

| ID   | Agent 1 — expected direction | Agent 2 — manual outcome | Agent 3 — expected verdict pattern |
|------|------------------------------|---------------------------|-------------------------------------|
| **F-1**  | Normalize quantification and shape wording (“every”, “exactly four sides”, “thing with exactly four sides”); clean conclusion punctuation. | **SUCCESS** — 3 atomic lines (premise, premise, conclusion). | Line 1 **PASS**. Line 2 **REWRITE** → conditional form (“if a thing has exactly four sides, then it is a shape” style); **DIFF** = no substantive loss. Line 3 **REWRITE** → drop narrative “in conclusion” wrapper; **DIFF** = wording only. |
| **F-3**  | Normalize to universal + existentials (“every fir tree”, “at least one object of worship…”, “at least one evergreen is not…”). | **SUCCESS** — 3 lines (evergreen link, worship fir link, conclusion). | Line 1 **PASS**. Line 2 **PASS**. Line 3 **REWRITE** → strip “in conclusion” / narrative shell; **DIFF** = wording only. |
| **F-4**  | Heavy normalization: singular “person” with explicit verbs, “chaperones”, split children vs teenagers where needed, align “school events” phrasing, preserve Bonnie’s either/or as one unit in meaning. | **LIMIT_EXCEEDED** (under tight budget) — **offender** is the **Bonnie disjunct** (“Bonnie either both attends… or … neither … nor …”); **cannot** split into independent claims without losing either/or meaning. *(With limit 8, may become SUCCESS; see § above.)* | *(Manual sim stops at Agent 2 for this case.)* If Agent 3 runs after a SUCCESS decomposition, evaluate each line per scope rules; no frozen manual row. |
| **F-5**  | Fix “Symptons”; sharpen virus/hosts (“at least one animal, including at least one human”); universal mammals/animals; symptoms list may still contain **“and so on”** in manual trace; flu → explicit **if-then**; conclusion → **at least one animal**. | **SUCCESS** — 7 lines (disease, virus hosts, human→mammal, mammal→animal, **single** symptoms line including “and so on”, flu rule, conclusion). | 1 **PASS**. 2 **REWRITE** → split “including” into explicit conjunction; **DIFF** = wording only. 3–4 **PASS**. 5 **OUT_OF_SCOPE** — **“and so on”** open-ended; REPORT vagueness. 6 **PASS**. 7 **REWRITE** → bare existential “there is at least one animal”; **DIFF** = strip narrative. **Note:** Manual follow-up wanted **Agent 1** to eliminate **“so on”** when possible so the symptom line can become in-scope; baseline **OUT_OF_SCOPE** documents the strict response when it remains. |
| **F-8**  | Normalize employees/persons, **at least one** meeting where appropriate, James disjunct (“James either both is a manager…” style), countries wording, managers singular/plural consistency. | **LIMIT_EXCEEDED** (under tight budget) — **offender** is the **James disjunct**; same structural issue as F-4. *(With limit 8, may become SUCCESS; see § above.)* | *(Manual sim stops at Agent 2.)* If Agent 3 runs, evaluate per line; no frozen manual row. |
| **F-9**  | Strengthen to “every person” where appropriate; tax haven phrasing (“at least one tax haven”) where manual shows it; keep Djokovic conditional explicit. | **SUCCESS** — 9 lines (disjunction over kind, chain of universals, conditionals, Djokovic bridge, conclusion with “In conclusion,” inside last atom in manual trace). | Lines 1–8 **PASS**. Line 9 **REWRITE** → **Djokovic is a Grand Slam champion** without “In conclusion”; **DIFF** = wording only. |

### Agent 2 formatting note

The notebook used **quoted lines** without the `1.` / `2.` prefixes. The **product** Agent 2 prompt specifies a **numbered** list for SUCCESS; treat numbering as a **format** requirement, not a semantic difference.

---

## Optional disagreement / suggestions (for maintainers)

- **Verbatim vs semantic:** For API swaps, prefer comparing **PASS / REWRITE / OUT_OF_SCOPE** and **LIMIT_EXCEEDED yes/no** (and decomposition validity) over exact punctuation or synonym choices at Agent 1.
- **Check in notebook:** If you want deterministic diffs, consider copying the baseline into this repo under e.g. `test_sets/fixtures/Agent1-3_chat_sim_results.ipynb` so the reference does not drift on `Downloads/`.
- **F-4 split risk:** When LIMIT_EXCEEDED no longer fires, the main regression to watch is **invalid splitting** of the first conditional’s **conjunctive consequent** (“attend **and** very engaged”); that is a **meaning** failure even if operator counts look fine.
