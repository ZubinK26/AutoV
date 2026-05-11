# CPMpy agentsim_e2e — handoff for review (Claude / external)

Generated snapshot of the last successful **`cpmpy-policy-pipeline run`** bundle plus domain inputs and NL-alignment tests.

## Layout

| Path | Contents |
|------|-----------|
| **`orchestrator_output/`** | **`policy.py`** (embedded `rule_module` JSON + `exec`), **`signature.py`** (vocabulary), **`manifest.json`** (NL per rule, symbols), **`consistency_report.json`**, **`verification_log.jsonl`**. |
| **`domain_inputs/`** | **`rules.txt`**, **`tools.json`**, Phase 0 **`signature.py`**, **`glossary.md`** from `agentsim_simplified_wfm` (sources the formalizer used; export `signature.py` should match or be copied from here at emit time). |
| **`tests/`** | **`test_agentsim_e2e_nl_alignment.py`** — scenario tests vs NL (existence, POSTED/pending, KYC, sanctions, merchant/goodwill caps, vulnerable cap). |
| **`TEST_RESULTS.txt`** | Pytest stdout for the NL-alignment file (**10 passed** at time of export). |

## Re-run tests (from repo root `AutoV`)

Requires editable install / `PYTHONPATH` so `cpmpy_wfm_policy` imports:

```powershell
cd <AutoV>
pip install -e ".[cpmpy-pipeline]"
python -m pytest exports/cpmpy_agentsim_e2e_claude_handoff/tests/test_agentsim_e2e_nl_alignment.py -v
```

Tests resolve the policy bundle at **`exports/cpmpy_agentsim_e2e`** relative to repo root (same as this handoff’s sibling folder).

## Reading `policy.py`

Formalized rules are **not** in separate `.py` files: they are JSON-encoded strings in **`_RULE_MODULES`**, each snippet `exec`’d after loading **`signature.py`**. See `manifest.json` for the **`nl_source`** of each **`rule_k`**.

## Full pipeline test suite

The workspace also has **`pytest CPMpy/policy_pipeline/tests`** (~74 tests, mostly mocked LLM); that output is **not** included here unless you run it separately.
