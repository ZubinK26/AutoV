# ASPBench (KR 2025 / arXiv:2507.19749)

**Paper:** [Can LLMs Solve ASP Problems? Insights from a Benchmarking Study](https://arxiv.org/abs/2507.19749) (Ren et al.).

**Repository:** [github.com/HomuraT/ASPBench](https://github.com/HomuraT/ASPBench).

## NL + formalization pairs (what the WFM demo uses)

The published clone includes **SymTex** under `datasets/SymTex/`. For each benchmark instance, the same `id` appears in:

| Role | Files (examples) |
|------|------------------|
| **Natural language (English)** | `*_textual.jsonl` — facts/rules as sentences (from the repo’s textualization pipeline; see upstream `README.md` step 12, `07_05_symtext_textulization.py`). |
| **Reference ASP (DLV2-style)** | `*_symbolic.jsonl` — same facts/rules in logic form. |

We pair:

- `answerset_generation_textual.jsonl` ↔ `answerset_generation_symbolic.jsonl`
- `answerset_selection_textual.jsonl` ↔ `answerset_selection_symbolic.jsonl`
- `fact_state_querying_textual.jsonl` ↔ `fact_state_querying_symbolic.jsonl` (NL in `asp_program_dlv2.noiseless_facts` / `noiseless_rules` on the textual side; ASP in the same fields on the symbolic side)

Loader implementation: `wfm_orchestration/asp_demo_sources.py` (`load_symtex_paired_index`). No synthetic examples — only rows present in both files with matching `id`.

## Getting the data

From the repo root (`AutoV/`):

```powershell
cd test_sets\datasets\aspbench
git clone https://github.com/HomuraT/ASPBench.git repo
```

If `repo/` is already present, `git -C repo pull` to update.

**License:** Follow the license file in the cloned repository (do not assume redistribution rights).

## Relation to this project

- **WFM demo:** `python -m wfm_orchestration.demo_launcher` option (1) draws random SymTex pairs from the clone.
- **Different benchmark:** NL “ASP-Bench” from natural language to programs ([arXiv:2602.01171](https://arxiv.org/abs/2602.01171)) is separate; see **`../asp_nl_bench/README.md`**.
