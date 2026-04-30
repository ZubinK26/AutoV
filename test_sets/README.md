# Test sets

- **`datasets/folio/`** — FOLIO v0.0 JSONL from [Yale-LILY/FOLIO](https://github.com/Yale-LILY/FOLIO) (CC-BY-SA-4.0); small enough to vendor (~960 KB combined).
- **`datasets/p-folio/`** — Place **`P-FOLIO.csv`** here after accepting the Hugging Face license (see folder README).
- **`scripts/select_folio_examples.py`** — Regenerates the curated English example list from the FOLIO JSONL files.
- **`wfm_folio_pffolio_examples_en.md`** — **10 FOLIO + 10 P-FOLIO–source** English blocks for WFM / Agent 1 browser tests (see file header for P-FOLIO caveats).
- **`wfm_pfolio_expected_outcomes_manual_baseline.md`** — regression / benchmark expectations for **PF-*** automated runs (compare to `wfm_folio_expected_outcomes_manual_baseline.md` for F-*).
- **`wfm_stress_examples_en.md`** — **12** medium–hard **reject** (R-*) and **edge** (E-*) blocks for Agents 1→3 stress testing; output files `wfm_stress_*_<UTC>.*`. (Labels predate **ClinCon** scope; see file header.)
- **`wfm_clincon_fragment_examples_en.md`** — **6** smoke blocks (C-*) for **ClinCon-safe ASP** Agent 3 scope; run with `--clincon` → `wfm_clincon_*_<UTC>.*`.
- **`datasets/aspbench/`** — README + optional git clone of [HomuraT/ASPBench](https://github.com/HomuraT/ASPBench) ([arXiv:2507.19749](https://arxiv.org/abs/2507.19749)).
- **`datasets/asp_nl_bench/`** — where to fetch **NL → ASP** “ASP-Bench” ([arXiv:2602.01171](https://arxiv.org/abs/2602.01171)).
- **`datasets/asp_competition/`** — Potassco / competition encodings (**solver-only**, not NL-paired; see folder README).
- **`wfm_agent4_confirmation_manual_scenario.md`** — manual (or future automated) tests starting **after Agent 3**: confirmation package, disagreement, `WFM_PATCH`, Style A merge, loop-back; uses stress/FOLIO run artifacts as fixtures.
- **`scripts/run_wfm_loopback_agent4_merge.py`** — run Agents **1→3** on **Style A** text extracted from Agent 4 interactive Markdown reports (`wfm_agent4_merge_loopback_gemini_*` in `run_results/`).

## Automated WFM pipeline (Claude API, Agents 1→3)

**Contract defaults** are documented in **`wfm_api_contract_frozen.md`** (model Sonnet 4, `temperature=0`, etc.).

One-shot run from the repo folder that contains `asp/wfm/` and `test_sets/`:

```powershell
cd <repo-root>   # folder that contains asp/wfm/ and test_sets/
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r test_sets/requirements-wfm-test.txt
copy .env.example .env
# Edit .env — set ANTHROPIC_API_KEY only there; never commit .env (gitignored)
python test_sets/scripts/run_wfm_folio_claude.py
```

Optional: set `ANTHROPIC_API_KEY` in the shell environment instead of `.env`.

- Parses the **## FOLIO** section only from `wfm_folio_pffolio_examples_en.md`.
- Loads system prompts verbatim from `asp/wfm/prompts/agent_{1,2,3}_*.md` and injects `compound_operator_limit` from `asp/wfm/config/wfm.json` into Agent 2.
- Writes **`run_results/wfm_folio_run_<UTC>.md`** (human-readable, notebook-style) and **`.jsonl`** (one row per example with usage).
- **Agent 4** is not invoked. If Agent 2 returns `LIMIT_EXCEEDED`, Agent 3 is skipped (matches WFM termination).

Dry-run (no API): `python test_sets/scripts/run_wfm_folio_claude.py --dry-run`

**Stress harness (R-* / E-*):** `python test_sets/scripts/run_wfm_folio_claude.py --stress` → `run_results/wfm_stress_claude_<UTC>.md` / `.jsonl`. Custom path: `--stress --examples path/to/file.md` (must contain `## STRESS`).

**ClinCon fragment (C-*):** `python test_sets/scripts/run_wfm_folio_claude.py --clincon` (or `run_wfm_folio_gemini.py --clincon`) → `wfm_clincon_*_<UTC>.*`. Custom markdown must contain `## CLINCON`.

## Agent 4 from a saved run (Gemini)

**Repo root (this clone):** `C:\Users\Zubin\Documents\Project_Cursor\Project_Cursor`

Open PowerShell and start every scenario with:

```powershell
cd C:\Users\Zubin\Documents\Project_Cursor\Project_Cursor
```

---

### Interactive flow (console UI, no JSONL paths)

```powershell
python test_sets/scripts/run_wfm_agent4_interactive.py
```

- Loads the **latest** `wfm_folio_gemini_*.jsonl`, `wfm_pfolio_gemini_*.jsonl`, and `wfm_stress_gemini_*.jsonl` under **`test_sets/run_results/`** (by file modification time). No `--run-jsonl` or comments file.
- The **menu** lists only rows where **Agent 3** output contains **`OUT_OF_SCOPE`**, each line shows **example id**, **dataset** (F-Gemini / P-FOLIO-Gemini / STRESS-Gemini), and **source JSONL filename**, plus difficulty.
- After you pick an example, the **main** view shows **Agent 3 output only**. Disagree and omit still use **Agent 2 sub-statement indices** (the numbers on `OUT_OF_SCOPE: N.` / `PASS: N.` lines), which match **`--disagree`** in the CLI script and the merge preview.
- **Blocking:** every **OUT_OF_SCOPE** line that could be mapped to an Agent 2 index must be either **disagreed** (with a comment) or **omit-confirmed** before review.
- **Modes:** disagree one index at a time with an immediate comment prompt; **blanket disagree** walks every Agent 2 statement top-to-bottom (shows the matching **Agent 3** line when available, else Agent 2 wording); **omit**; **abort** with confirmation.
- **Review** then **Send to Agent 4** (same `GEMINI_API_KEY` as other Gemini harnesses). Optional merge preview and Markdown report path.

If a run has `OUT_OF_SCOPE` text that cannot be matched to Agent 2 numbered lines, that example is skipped or blocked with a short message—use the CLI harness for edge cases.

**Merge preview (Style A):** the preview applies `wfm_patch` on a **merge base built from Agent 3** (PASS / REWRITE / OUT_OF_SCOPE quoted text per Agent 2 index), falling back where needed—so REWRITE lines from Agent 3 appear in the preview instead of stale Agent 2 wording. If the overlay cannot parse a line, notes may be appended under the preview.

---

### What this script does vs. the full WFM loop

| Piece | In `run_wfm_agent4_from_run.py` today? |
|--------|----------------------------------------|
| Load a **saved** Agents 1–3 row from a **JSONL** | Yes |
| Build the **structured payload** (Agent 2 + Agent 3 + your disagree / omit slots) | Yes |
| Call **Agent 4** (Gemini) and print the reply | Yes |
| Parse **`wfm_patch`** and print a **Style A merge preview** (`--merge-preview`) | Yes (best-effort) |
| **Automatically** run **Agent 1 → 2 → 3** again on the merged text | **No** — not implemented in this script |

The **product** flow in **`asp/wfm/Agent_WFM.md`** is: confirm merged NL → **full WFM re-entry at Agent 1** → … → confirmation again (subject to outer budget). This repository’s Agent 4 script is a **slice** of that: it exercises **Agent 4 + merge preview** only. After you inspect the merge preview (or copy the merged text), you **manually** feed that text into **`run_wfm_folio_gemini.py`** (or a future single orchestrator that chains the steps). Wiring the full loop into **one** command is **orchestration work**, not done here yet.

---

### API key

The script uses the **same** **`GEMINI_API_KEY`** as `run_wfm_folio_gemini.py` (loaded from **`.env`** at the repo root, next to `asp/wfm/` and `test_sets/`).

- If the key is **already** set and Gemini 1–3 runs work, you do **not** do anything extra for Agent 4.
- You only need to edit `.env` if the script prints **`ERROR: Set GEMINI_API_KEY`** (missing or empty).

---

### One JSONL file per workflow

Each full Gemini run produces **one** new pair of files, e.g. `wfm_stress_gemini_<UTC>.jsonl` (stress: **R-***, **E-***) or `wfm_folio_gemini_<UTC>.jsonl` (**F-***). Pick **the one file** that contains your **`--example`**. You do **not** need two JSONL files unless you are testing two different runs.

---

### Scenario A — Agent 4 only (use an existing JSONL on disk)

Replace `STRESS_JSONL` with your real filename under `test_sets\run_results\` (tab-complete in PowerShell is fine).

**A0 — Optional: see what’s in the file (no API, no key):**

```powershell
cd C:\Users\Zubin\Documents\Project_Cursor\Project_Cursor
python test_sets/scripts/run_wfm_agent4_from_run.py --run-jsonl test_sets/run_results/wfm_stress_gemini_20260404_151309Z.jsonl --list-eligible
```

**A1 — Preview the confirmation payload for one id (no API, no key):**

```powershell
python test_sets/scripts/run_wfm_agent4_from_run.py --run-jsonl test_sets/run_results/wfm_stress_gemini_20260404_151309Z.jsonl --example R-1 --dry-run
```

**A2 — Real Agent 4 call:** create a comments file with **one non-empty line per** `--disagree` index, **same order** (here lines 6 then 8):

```powershell
@"
User disagrees with line 6: want different approval rule.
User disagrees with line 8: use conclusion without 'through the reporting chain'.
"@ | Set-Content -Encoding utf8 .\comments_r1.txt
```

```powershell
python test_sets/scripts/run_wfm_agent4_from_run.py --run-jsonl test_sets/run_results/wfm_stress_gemini_20260404_151309Z.jsonl --example R-1 --disagree 6,8 --comments-file .\comments_r1.txt --omit-confirmed 5 --merge-preview
```

- **`--omit-confirmed 5`**: line 5 is treated as **user-confirmed omit** in the merge preview (matches the manual scenario where OOS reachability is dropped). Omit if you are not omitting any line.

**A3 — Full loop (manual second leg, today):** copy the **Style A** block from the script output (or from `--merge-preview`), save as `merged_rule.txt`, then run Agents 1–3 on that text. The Gemini runner expects an **examples markdown** file, not a raw fragment—so until orchestration exists, practical options are: paste into a one-off `###` block in a scratch `.md`, or add a small future `--raw-input` to the Gemini runner. **Until then, “loop back” is: you paste merged NL into whatever input path you use for Agent 1.**

---

### Scenario B — New stress run, then Agent 4 on a row from the new JSONL

**B1 — Produce a fresh JSONL (uses `GEMINI_API_KEY` from `.env`):**

```powershell
cd C:\Users\Zubin\Documents\Project_Cursor\Project_Cursor
python test_sets/scripts/run_wfm_folio_gemini.py --stress
```

Note the printed paths, e.g. `test_sets\run_results\wfm_stress_gemini_YYYYMMDD_HHMMSSZ.jsonl`.

**B2 — List eligible ids in that new file:**

```powershell
python test_sets/scripts/run_wfm_agent4_from_run.py --run-jsonl test_sets/run_results/wfm_stress_gemini_YYYYMMDD_HHMMSSZ.jsonl --list-eligible
```

**B3 — Dry-run / live Agent 4** as in A1 / A2 but with the **new** `--run-jsonl` path.

---

**Eligible row:** Agent 3 has output (not skipped) and Agent 2 is not `LIMIT_EXCEEDED`.

See **`wfm_agent4_confirmation_manual_scenario.md`** and **`asp/wfm/prompts/agent_4_user_interaction.md`** (`WFM_PATCH`).

## Automated WFM pipeline (Gemini API, Agents 1→3)

Contract: **`test_sets/wfm_api_contract_gemini.md`**. Set **`GEMINI_API_KEY`** in `.env` (see `.env.example`). FOLIO outputs: `wfm_folio_gemini_<UTC>.*`; P-FOLIO: **`--pfolio`** → `wfm_pfolio_gemini_<UTC>.*`; stress: **`--stress`** → `wfm_stress_gemini_<UTC>.*`; ClinCon smoke: **`--clincon`** → `wfm_clincon_gemini_<UTC>.*`. **`--pfolio`**, **`--stress`**, and **`--clincon`** are mutually exclusive.

```powershell
pip install -r test_sets/requirements-wfm-test.txt
python test_sets/scripts/run_wfm_folio_gemini.py --dry-run
python test_sets/scripts/run_wfm_folio_gemini.py
python test_sets/scripts/run_wfm_folio_gemini.py --pfolio
python test_sets/scripts/run_wfm_folio_gemini.py --stress --dry-run
python test_sets/scripts/run_wfm_folio_gemini.py --stress
python test_sets/scripts/run_wfm_folio_gemini.py --clincon --dry-run
python test_sets/scripts/run_wfm_folio_gemini.py --clincon
```

### Loopback — Agent 4 merge preview → Agents 1→3 (Gemini)

Use saved **`wfm_agent4_interactive_*.md`** reports (must include a **Style A merge preview** block). Each report becomes one row: **merge preview text** is passed to **Agent 1** as user input (same call chain as `run_wfm_folio_gemini.py`), then Agent 2 → Agent 3. Writes **`run_results/wfm_agent4_merge_loopback_gemini_<UTC>.md`** and **`.jsonl`** (`example_set: agent4_merge_loopback`, plus `loopback_source_report` per row).

```powershell
cd C:\Users\Zubin\Documents\Project_Cursor\Project_Cursor
python test_sets/scripts/run_wfm_loopback_agent4_merge.py --dry-run --glob "test_sets/run_results/wfm_agent4_interactive_*.md"
python test_sets/scripts/run_wfm_loopback_agent4_merge.py --glob "test_sets/run_results/wfm_agent4_interactive_*.md"
```

**Caveat:** Input is the **numbered merge** prose, not the original unstructured natural-language rule; Agent 1 is instructed to preserve numbering. Re-run interactive Agent 4 if you want an updated preview (e.g. after the Agent 3–based merge fix).
