# `registry_stage` (Python package)

**M0 decision — layout**

| Item | Choice |
|------|--------|
| Package directory | **`registry_stage/`** (import `registry_stage`) |
| Handoff JSON on disk | **`bundles/{bundle_id}.json`** at **repo root** (same layout as `registry_persistence_v1.md`) |
| Tests | **`registry_stage/tests/`** — BGE+FAISS integration runs when deps are installed; `REGISTRY_M2_SKIP_HEAVY=1` skips it for fast runs |

**Install (dev):**

```powershell
cd <repo-root>
pip install -r registry_stage/requirements.txt
python -m pytest registry_stage/tests -q
```

See **`development_plan_registry_stage_v1.md`** for milestones M0–M6 and **M4** automated resolve (`run_automated_resolve`, `resolve_v1` + validation; trace/export in **M5**). **M2** adds `RegistrySession` and semantic indexes; **M3** adds `run_search_and_gaps_for_line` (`line_driver.py`) with optional **Gemini** expansion + structured gaps (`registry_stage/llm/`, prompts under `registry_stage/prompts/`). When **`enable_llm=True`**, structured extraction drives **`gap_spans`** (Title-Case **heuristic** merge is **off**); when **`enable_llm=False`**, heuristic gaps are still merged (CI / `--no-llm`). **`LineSearchGapsResult`** includes **`raw_expansion_phrases`**, **`raw_structured_gaps`**, **`authoritative_min_score`**, and **`semantic_backend_label`** for Lane A JSONL. **Lane A (live Gemini):** `python -m registry_stage.m3_lane_a --out registry_stage/eval_runs/my_run.jsonl` — defaults use **`eval_fixtures/m3_business_*.json`**; outputs go under **`eval_runs/`** (gitignored). Optional **`--query-modes`**, **`--masking-presets`**, **`--authoritative-min-score`** narrow the matrix; omitting them keeps the full **2×3** run. **Eval defaults (Protocols A+B):** **`masking_preset=conservative`**, **`query_mode=single_concat`**, BGE+FAISS **`authoritative_min_score`** **0.35** in ``default_authoritative_min_score`` — **re-tune** after more empirical eval; see **`registry_stage/REGISTRY_M3_EVAL_DECISIONS.md`**. **M4 warm eval / prompt tuning** — **`registry_stage/REGISTRY_M4_EVAL_DECISIONS.md`**. **Protocol B** sweep: `python -m registry_stage.m3_protocol_b_minscore --scores 0.18 0.22 0.28 0.32 0.35 0.40 --out-dir registry_stage/eval_runs`. Set **`GEMINI_API_KEY`** in repo-root `.env` (same contract as **`test_sets/wfm_api_contract_gemini.md`**). Default **`enable_llm=False`** keeps tests and CI offline; use mocks via `llm_complete=`.

### Registry stage v1 demo (copy-paste)

From **repo root** (directory containing **`bundles/`** and **`registry_stage/`**), with **`GEMINI_API_KEY`** in **`.env`**:

```powershell
pip install -r registry_stage/requirements.txt
python -m registry_stage.run --bundle bundles/fixture_bu_001.json --export exports/dev_session.json --save-registry exports/registry_after.json
```

Warm start (second run uses saved registry):

```powershell
python -m registry_stage.run --bundle bundles/<another_bundle>.json --registry exports/registry_after.json --export exports/dev_session_2.json
```

**G9 — one-command two-run** (seed bundle → **`--save-registry`** → reuse bundle → **`--registry`**) with defaults from **`eval_fixtures/m4_warm_*`**:

```powershell
python -m registry_stage.warm_registry_two_run --registry-out exports/warm_after_seed_registry.json
```

Optional **`--export-seed`** / **`--export-reuse`** for dev session JSON each phase. See **`development_plan_wfm_registry_e2e_demo.md`** § **8**.

Use **`--index stub`** for fast local smoke without BGE/FAISS; **`--no-llm`** disables M3 Gemini expansion/extraction only (M4 resolve still uses Gemini unless you use tests with mocks).

**M4 warm-registry eval** (seed bundle → save registry → reuse bundle → JSONL). Use a **unique `--out`** path each run so you do not overwrite prior results:

```powershell
python -m registry_stage.m4_warm_eval --out registry_stage/eval_runs/m4_warm_eval.jsonl --label m4_warm
```

Details and what was tuned: **`registry_stage/REGISTRY_M4_EVAL_DECISIONS.md`**, module docstring **`registry_stage/m4_warm_eval.py`**. Prefer **`--index faiss`** for retrieval aligned with Protocol B defaults (**0.35** cutoff).
