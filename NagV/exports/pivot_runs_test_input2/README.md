# Pivot export: `Test_input2` full run

Versioned snapshot for **another machine** via Git: policy IR, WFM/NL artifacts, linearization, critic/cross outputs, Z3, and executable template suite results.

| Artifact | Role |
|----------|------|
| `source_policy_Test_input2.md` | Original NL rules file (copy for portability; `run_summary.json` may still list an absolute path from the machine that produced the run). |
| `phase0_normalized_nl.txt` | Processed / normalized NL after WFM. |
| `rules_source.txt` | NL stream used for registry / artifacts in this run. |
| `rules_extracted.json` | Extracted JSON IR (`policy_id` + `rules`). |
| `meta_scheme.json` | Compiled meta (pathways, sorts, etc.). |
| `synthetic_en.md` | Markdown render of the model. |
| `linearized_nl_and_model.txt` | Linearized NL + model excerpt. |
| `linearized_model_for_cross_critic.txt` | Rules linearized for CrossCritic. |
| `z3_result.json` | Solver outcome / model excerpt. |
| `precheck.json` | Heuristic NL vs meta checks. |
| `critic_*`, `cross_critic_*` | Semantic + cross-coherence traces. |
| `template_suite_generated.json` | LLM-generated executable test suite. |
| `template_run_report.json` | Per-instance Z3 vs golden verdicts. |
| `run_summary.json` | Pipeline summary for this work dir. |

See repo root **`test-gen-results.md`** for a plain-language read of `template_run_report.json`.
