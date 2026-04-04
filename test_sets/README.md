# Test sets

- **`datasets/folio/`** — FOLIO v0.0 JSONL from [Yale-LILY/FOLIO](https://github.com/Yale-LILY/FOLIO) (CC-BY-SA-4.0); small enough to vendor (~960 KB combined).
- **`datasets/p-folio/`** — Place **`P-FOLIO.csv`** here after accepting the Hugging Face license (see folder README).
- **`scripts/select_folio_examples.py`** — Regenerates the curated English example list from the FOLIO JSONL files.
- **`wfm_folio_pffolio_examples_en.md`** — **10 FOLIO + 10 P-FOLIO–source** English blocks for WFM / Agent 1 browser tests (see file header for P-FOLIO caveats).

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
