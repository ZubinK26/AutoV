# Test sets

- **`datasets/folio/`** — FOLIO v0.0 JSONL from [Yale-LILY/FOLIO](https://github.com/Yale-LILY/FOLIO) (CC-BY-SA-4.0); small enough to vendor (~960 KB combined).
- **`datasets/p-folio/`** — Place **`P-FOLIO.csv`** here after accepting the Hugging Face license (see folder README).
- **`scripts/select_folio_examples.py`** — Regenerates the curated English example list from the FOLIO JSONL files.
- **`wfm_folio_pffolio_examples_en.md`** — **10 FOLIO + 10 P-FOLIO–source** English blocks for WFM / Agent 1 browser tests (see file header for P-FOLIO caveats).
- **`wfm_pfolio_expected_outcomes_manual_baseline.md`** — regression / benchmark expectations for **PF-*** automated runs (compare to `wfm_folio_expected_outcomes_manual_baseline.md` for F-*).
- **`wfm_stress_examples_en.md`** — **12** medium–hard **reject** (R-*) and **edge** (E-*) blocks for Agents 1→3 stress testing; output files `wfm_stress_*_<UTC>.*`.

## Automated WFM pipeline (Claude API, Agents 1→3)

**Contract defaults** are documented in **`wfm_api_contract_frozen.md`** (model Sonnet 4, `temperature=0`, etc.).

One-shot run from the repo folder that contains `WFM/` and `test_sets/`:

```powershell
cd <repo-root>   # folder that contains WFM/ and test_sets/
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r test_sets/requirements-wfm-test.txt
copy .env.example .env
# Edit .env — set ANTHROPIC_API_KEY only there; never commit .env (gitignored)
python test_sets/scripts/run_wfm_folio_claude.py
```

Optional: set `ANTHROPIC_API_KEY` in the shell environment instead of `.env`.

- Parses the **## FOLIO** section only from `wfm_folio_pffolio_examples_en.md`.
- Loads system prompts verbatim from `WFM/prompts/agent_{1,2,3}_*.md` and injects `compound_operator_limit` from `WFM/config/wfm.json` into Agent 2.
- Writes **`run_results/wfm_folio_run_<UTC>.md`** (human-readable, notebook-style) and **`.jsonl`** (one row per example with usage).
- **Agent 4** is not invoked. If Agent 2 returns `LIMIT_EXCEEDED`, Agent 3 is skipped (matches WFM termination).

Dry-run (no API): `python test_sets/scripts/run_wfm_folio_claude.py --dry-run`

**Stress harness (R-* / E-*):** `python test_sets/scripts/run_wfm_folio_claude.py --stress` → `run_results/wfm_stress_claude_<UTC>.md` / `.jsonl`. Custom path: `--stress --examples path/to/file.md` (must contain `## STRESS`).

## Automated WFM pipeline (Gemini API, Agents 1→3)

Contract: **`test_sets/wfm_api_contract_gemini.md`**. Set **`GEMINI_API_KEY`** in `.env` (see `.env.example`). FOLIO outputs: `wfm_folio_gemini_<UTC>.*`; P-FOLIO: **`--pfolio`** → `wfm_pfolio_gemini_<UTC>.*`; stress: **`--stress`** → `wfm_stress_gemini_<UTC>.*`. **`--pfolio`** and **`--stress`** are mutually exclusive.

```powershell
pip install -r test_sets/requirements-wfm-test.txt
python test_sets/scripts/run_wfm_folio_gemini.py --dry-run
python test_sets/scripts/run_wfm_folio_gemini.py
python test_sets/scripts/run_wfm_folio_gemini.py --pfolio
python test_sets/scripts/run_wfm_folio_gemini.py --stress --dry-run
python test_sets/scripts/run_wfm_folio_gemini.py --stress
```
