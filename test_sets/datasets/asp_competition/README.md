# ASP planning / competition encodings (solver benchmarks)

**Not used for WFM NL demos.** These repositories ship **logic programs** (e.g. planning encodings) without a canonical natural-language specification paired one-to-one with each file, so they are **not** offered in `wfm_orchestration.demo_launcher`.

Use them for **Clingo / ClinCon solver checks**, regression on grounding, or mining encoding idioms — not as NL→ASP gold pairs for WFM.

| Resource | URL | Notes |
|----------|-----|--------|
| Potassco org | [github.com/potassco](https://github.com/potassco) | Many encodings and domain benchmarks |
| ASP planning benchmarks | [potassco/asp-planning-benchmarks](https://github.com/potassco/asp-planning-benchmarks) | `encoding.asp`, instances |
| Asprilo | [potassco/asprilo](https://github.com/potassco/asprilo) | Logistics generators + instances |
| ASPLIB (legacy listing) | [ASPLIB benchmarks index](http://dit.unitn.it/~wasp/Benchmarks/index.html) | Verify license per archive |

## Optional local clone

```powershell
cd test_sets\datasets\asp_competition
git clone https://github.com/potassco/asp-planning-benchmarks.git planning
```

**Clingo** is the usual solver; **ClinCon** adds constraints — check whether an encoding fits your ClinCon-safe fragment before using it as a formalizer target.

## Pairs for WFM + scoring

Use **[HomuraT/ASPBench](https://github.com/HomuraT/ASPBench) SymTex** (`../aspbench/README.md`) or vendored **[NL ASP-Bench](https://arxiv.org/abs/2602.01171)** via `../asp_nl_bench/installed.json`.
