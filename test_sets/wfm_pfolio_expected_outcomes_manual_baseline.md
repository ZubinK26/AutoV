# P-FOLIO expected outcomes — benchmark (API regression)

**Reference automated run:** `test_sets/run_results/wfm_pfolio_gemini_20260404_141451Z.md` / `.jsonl` (Gemini 3.1 Pro preview, `temperature=0`, thinking `LOW`, compound limit **8**).

Use this file like **`wfm_folio_expected_outcomes_manual_baseline.md`**: compare **outcome classes** and **per-line Agent 3 verdict patterns**, not necessarily **verbatim** punctuation at every layer. **Formatting quirks** in Agent 3 output (e.g. `PASS: 1.` vs `PASS:` without numbering) are **not** scored here unless you add strict linters; semantic verdicts and decomposition shape matter first.

**Source text:** `test_sets/wfm_folio_pffolio_examples_en.md` (## P-FOLIO section).

---

## Compound operator limit

Same as FOLIO baseline: **`compound_operator_limit: 8`** from `asp/wfm/config/wfm.json` is injected into Agent 2. Manual notebook traces that assumed a **tighter** informal ceiling may show **LIMIT_EXCEEDED** where this harness shows **SUCCESS**; judge **decomposition validity** (no illegitimate splits of unified conditionals / either-or bundles) when limits differ.

---

## Summary table (by PF ID)

| ID | Agent 1 — expected direction | Agent 2 — expected pattern | Agent 3 — expected verdict pattern |
|----|------------------------------|----------------------------|-------------------------------------|
| **PF-1** | Stabilize “some” as “at least one”; optional “instance of” wording. | **SUCCESS** — 3 numbered lines; conclusion line may keep “In conclusion:”. | Line 1–2 **PASS**. Line 3 **PASS** in reference run; acceptable alternative: **REWRITE** to drop “In conclusion:” / “In conclusion,” (wording-only **DIFF**). |
| **PF-2** | “All” → “every”; “some” in conclusion → “at least one” or equivalent; “Therefore,” optional. | **SUCCESS** — 3 lines. | Line 1–2 **PASS**. Line 3 **REWRITE** — remove discourse marker (“Therefore,” / “In conclusion”) → bare existential; **DIFF** wording only. |
| **PF-3** | Universals / existentials; name “Rock” clearly; skittish / still structure preserved. | **SUCCESS** — 7 lines. | Lines 1–6 **PASS**. Line 7 **REWRITE** — strip “In conclusion:”; **DIFF** wording only. |
| **PF-4** | Tense/modality normalized (“will” → present where appropriate); iff and show titles preserved. | **SUCCESS** — 7 lines (quoted titles). | **Intent:** each line **PASS** or cosmetic **REWRITE** on last line to drop “In conclusion:”. Reference run had **inconsistent Agent 3 line prefixes** (human review OK); tighten formatting separately from API scoring. |
| **PF-5** | Aliens / Marvin / Earth / Mars; “cannot be from both” clarified as negated conjunction. | **SUCCESS** — 7 lines. | Lines 1–6 **PASS**. Line 7 **PASS** in reference; acceptable: **REWRITE** to drop “Therefore,”. |
| **PF-6** | WWE / stable facts; fix **strong** capitalization if input typo. | **SUCCESS** — 6 lines (includes / feud split reasonably). | Lines 1–5 **PASS**. Line 6 **PASS** in reference; acceptable: **REWRITE** to drop “In conclusion:”. |
| **PF-7** | Timeliness / mass product tension; incomplete “Either … or …” sentence completed (see **risk note** below). | **SUCCESS** — often **8** lines if conditional consequent “A and B” splits into two implications (classically equivalent). | Lines 1–7 **PASS** typical; line 8 **REWRITE** — strip “In conclusion:” from last atom. |
| **PF-8** | Superhero-movie rules; unpack “vice versa” into symmetric fights; named movie / Sir Digby. | **SUCCESS** — **~10** lines before conclusion in reference (heavy but within limit). | Mixed **REWRITE** / **PASS**: last line **REWRITE** to drop “In conclusion:”; line 1 may be **REWRITE** (watch **“always”** — do not silently weaken modality vs intent). |
| **PF-9** | Managed buildings, deposits, iff on Tom, rent vs threshold, Fluffy / Olive Garden. | **SUCCESS** — **~11** lines (Tom/Fluffy may split). | Lines 1–10 **PASS** typical; line 11 **PASS** in reference; acceptable: **REWRITE** to drop “In conclusion:”. |
| **PF-10** | Taller-than blocking; transitivity; Windy; class / Peter / Michael. | **SUCCESS** — **8** lines. | Lines 1–7 reference **PASS**; line 8 **PASS**; acceptable last-line **REWRITE** if model strips “In conclusion:”. “At least one man in class” vs “a man in class” should remain **existential**, not weakened. |

---

## PF-7 — maintainer risk note

The prompt bundle contains a **fragment**: *“Either Zaha Hadid's design style or Kelly Wearstler's design style.”* Agent 1 typically **completes** it (e.g. “The design style is either …”). Regression tests should ensure that completion is **not** an arbitrary invention: if a model output diverges here, **Agent 3** should **OUT_OF_SCOPE** or force an honest **DIFF** — product policy TBD.

---

## Optional: strict Agent 3 formatting (out of scope for this MD)

For machine validation, normalize **PASS:/REWRITE:/OUT_OF_SCOPE:** lines in post-processing; do not require API **verbatim** prefix parity across models.
