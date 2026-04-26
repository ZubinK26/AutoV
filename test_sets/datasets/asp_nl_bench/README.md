# ASP-Bench (natural language → ASP) — **option 2** in the WFM demo

This is **not** the same artifact as **[HomuraT/ASPBench](https://github.com/HomuraT/ASPBench)** (Ren et al., [arXiv:2507.19749](https://arxiv.org/abs/2507.19749)). That GitHub repo is **SymTex** and is what **demo option 1** uses. If the link you have is `github.com/HomuraT/ASPBench`, you already have the right source for **option 1**, not for this folder.

**This folder** is for **Szeider et al.**, [*ASP-Bench: From Natural Language to Logic Programs*](https://arxiv.org/abs/2602.01171) (arXiv:2602.01171): **128** NL problems, validators, example solutions.

## Official data location (from the paper)

The paper states that the full benchmark (problem descriptions, ground-truth validators, example solutions) is published on **Zenodo**:

- **DOI:** [https://doi.org/10.5281/zenodo.18062939](https://doi.org/10.5281/zenodo.18062939)

The release is an **encrypted** archive; the paper/HTML version explains why and how to obtain the password. Download and unpack per Zenodo + paper instructions.

We do **not** auto-download or commit that archive here (encryption, license, and layout may change with Zenodo versions).

## Wiring the WFM demo (option 2)

The demo expects a single **JSONL** you produce from the official files (or a small export script), one JSON object per line, **verbatim** fields, for example:

```json
{"id": "<problem id>", "nl": "<natural language from the benchmark>", "reference_asp": "<reference program text if you export it>"}
```

Field names accepted by the loader: `nl` or `natural_language`; `reference_asp` or `reference_lp` or `program`.

Then:

1. Copy `installed.example.json` → **`installed.json`** in this directory.
2. Set `"problems_jsonl"` to the path of that JSONL (relative to `asp_nl_bench/` is fine).
3. Run `python -m wfm_orchestration.demo_launcher` and choose **2**.

If you only need **paired NL + ASP** without maintaining a custom JSONL, use **demo option 1** (SymTex from HomuraT/ASPBench); our loader already pairs textual + symbolic JSONL there.

## Use with formalization pipeline

After WFM, formalize **PASS** lines to `.lp` and compare to `reference_asp` from the same JSONL row (or to validator semantics from the Zenodo package).
