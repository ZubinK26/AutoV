# NagV (Z3)

This folder hosts **two** policy/Z3 stories:

1. **Pivot pipeline** (recommended for NL → WFM → IR → Z3): see [`pivot_pipeline/README.md`](pivot_pipeline/README.md), [`Extract-Pivot.md`](Extract-Pivot.md), and demo-oriented notes in [`demo-presentation-file.md`](demo-presentation-file.md). Install from **AutoV repo root**: `pip install -e .` (entry points `pivot-pipeline`, `scope-rewriter`, `pivot-template-suite`).
2. **Legacy NagV formalizer** (below): LLM writes **Python + Z3** directly; separate progress schema and driver.

## Legacy NagV formalizer (Python-as-model)

Pipeline: **WFM (SMT profile)** → aggregated NL → **LLM formalizer** emits **Z3 Python** → **feasibility gate** (`run_z3_check` returns `sat|unsat|unknown`) → **critic** → **final Z3 verify** (expect **`sat`** for default policy consistency).

## Setup

```powershell
cd NagV
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Requires repo-root **`GEMINI_API_KEY`** (or Anthropic if `NAGV_LLM=anthropic`) in `AutoV/.env`.

## Formalizer contract

The generated file must define **`run_z3_check()`** (or `check()`) returning a **dict** with **`status`**: `"sat"` | `"unsat"` | `"unknown"`.

The subprocess driver is `python -m nagv.z3_driver <file> feasibility|verify`.

## Success

- **`Outcome: success`** — final phase got **`sat`** (policy encoding satisfiable under the default harness).
- This is **not** a Nagini-style proof; soundness of NL→Z3 is still LLM + critic gated.

## Artifacts

Under `--work-dir`: `candidate_verified.py`, `final.py`, `verification_log.txt`, `run_summary.json`, `nagv_progress.json` (`schema_version` **nagv_progress_v3_z3**).

## CLI

- `--z3-timeout` (alias `--nagini-timeout`) — driver subprocess seconds (default 120).
