# AutoV

## For reviewers

Start here:
1. Read `example_run_artifact_bundle.md` for one complete run.
2. View `Pipeline_Diagram_Simplified.png` for the control flow.
3. Run `pivot-pipeline ...` from the quick start if you want to reproduce.
4. See `NagV/pivot_pipeline/ARCHITECTURE.md` for implementation details.




Monorepo workspace for **natural-language policy formalization**: chunked **writing workflows (WFM)**, **LLM-assisted extraction** into a structured rule IR, compilation to **Z3**, and optional **semantic / cross alignment** and **executable template-suite** checks against the solver.

The main packaged surface for reviewers is the **pivot policy pipeline** (`pivot-pipeline`). The installable project name is **`autov-workspace`** (see [`pyproject.toml`](pyproject.toml)); this repository directory is **AutoV**.

## Pipeline diagrams (Mermaids)

1. **[`Pipeline_Diagram.png`](Pipeline_Diagram.png)** — full pipeline (detailed stages and branches).
2. **[`Pipeline_Diagram_Simplified.png`](Pipeline_Diagram_Simplified.png)** — simplified overview.

For the Architecture file - **editable Mermaid source**, narrative, and flag semantics, see **[`NagV/pivot_pipeline/ARCHITECTURE.md`](NagV/pivot_pipeline/ARCHITECTURE.md)**.

## Example artifact from a prior run

For one **combined read-through** of inputs and model-shaped outputs from **an archived pivot export** (original NL, a plain-language WFM summary, the English used before structured IR, linearized rules, and pretty-printed `meta_scheme.json`), open **[`example_run_artifact_bundle.md`](example_run_artifact_bundle.md)**. It is stitched from [`NagV/exports/pivot_runs_test_input2/`](NagV/exports/pivot_runs_test_input2/README.md); use that folder for per-file artifacts and `run_summary.json` metadata.

## Requirements

- **Python 3.11+**
- **Google Gemini API** key for LLM steps used by the pivot stack (set `GEMINI_API_KEY` in `.env`)

## Quick start

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
copy .env.example .env
# Edit .env: set GEMINI_API_KEY
```

Run the pipeline (sample input shipped in-repo; use a fresh `--work-dir` so you do not overwrite a versioned export):

```powershell
pivot-pipeline --input NagV\exports\pivot_runs_test_input2\source_policy_Test_input2.md --work-dir NagV\exports\pivot_runs\my_run
```

**Optional — pre-WFM Scope Rewriter** (`scope-rewriter` after a successful `pip install -e .`, or run `python NagV\pivot_pipeline\scope_rewriter_cli.py …` from the repo root): turn a reference Markdown/policy note into pivot-oriented **plain rules** plus a JSON sidecar, with an interactive review loop, then point `pivot-pipeline --input` at `work-dir\scope_rewriter\latest.nl`.

If you already have extracted rules JSON and want to skip Phase 1 LLM extraction:

```powershell
pivot-pipeline --input path\to\rules.nl --work-dir path\to\work --rules-json path\to\rules_extracted.json
```

See **`pivot-pipeline --help`** for flags (`--skip-phase0`, `--with-critic`, `--with-cross-critic`, `--with-template-generator`, `--template-suite`, and others).

## Where to look next

| Topic | Location |
|--------|-----------|
| **Single-file read-through of one archived export** | [`example_run_artifact_bundle.md`](example_run_artifact_bundle.md) |
| **Pipeline diagram (PNG, from Mermaid)** | [`Pipeline_Diagram.png`](Pipeline_Diagram.png) |
| **Pipeline diagram simplified (PNG, from Mermaid)** | [`Pipeline_Diagram_Simplified.png`](Pipeline_Diagram_Simplified.png) |
| **End-to-end architecture (Mermaid source + narrative)** | [`NagV/pivot_pipeline/ARCHITECTURE.md`](NagV/pivot_pipeline/ARCHITECTURE.md) |
| **Rule IR contract** | [`NagV/Extract-Pivot.md`](NagV/Extract-Pivot.md) |
| **Pipeline-focused README** | [`NagV/pivot_pipeline/README.md`](NagV/pivot_pipeline/README.md) |
| **Versioned example run + artifact glossary** | [`NagV/exports/pivot_runs_test_input2/README.md`](NagV/exports/pivot_runs_test_input2/README.md) |
| **Plain read of template-suite results** | [`test-gen-results.md`](test-gen-results.md) |
| **Older NagV Z3 formalizer path** | [`NagV/README.md`](NagV/README.md) |

The pipeline **diagram PNGs** above already give a visual overview on the default GitHub view; you can still add a **short demo recording** if you want motion capture of a full run.

## Tests

From the repo root (after `pip install -e .`):

```powershell
pytest
```

`testpaths` are configured in [`pyproject.toml`](pyproject.toml) (`registry_stage`, `wfm_orchestration`, `NagV/pivot_pipeline`, `NagV/pivot_wfm`).

## Repository layout (high level)

- **`NagV/pivot_pipeline/`** — Pivot NL → WFM → JSON IR → Z3 → checks (primary CLI).
- **`NagV/pivot_wfm/`** — Pivot WFM profile assets used in Phase 0.
- **`registry_stage/`**, **`wfm_orchestration/`** — Shared extraction / WFM plumbing used by the pivot stack.
- **`NagV/`** (other) — NagV Z3 formalizer pipeline; see `NagV/README.md`.
- **`CPMpy/`**, **`WFM/`** — Additional experiments and specs (not required for `pivot-pipeline` alone).

## License

See [`LICENSE`](LICENSE).
