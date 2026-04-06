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

See **`development_plan_registry_stage_v1.md`** for milestones M0–M6. **M2** adds `RegistrySession` and semantic indexes; **M3** adds `run_search_and_gaps_for_line` (`line_driver.py`) with optional **Gemini** expansion + structured gaps (`registry_stage/llm/`, prompts under `registry_stage/prompts/`). Set `LineDriverConfig(enable_llm=True)` and **`GEMINI_API_KEY`** in repo-root `.env` (same contract as **`test_sets/wfm_api_contract_gemini.md`**). Default **`enable_llm=False`** keeps tests and CI offline; use mocks via `llm_complete=`.
