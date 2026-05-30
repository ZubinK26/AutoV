# Policy case pipeline (v4)

Unstructured source → **partial world** (stated + unknown) → **provenance** on stated fields only → **Z3 strict** (CWA on unknowns) + **Z3 lenient** (existential completion, stated pinned only) → **explanation** (witness or unsat core) + **query addendum**.

No `golden.sat`, no completeness critic, no pass/fail = “LLM agreed with Z3.”

## Run

```powershell
python -m pivot_pipeline.external_tester.run `
  --work-dir NagV\exports\pivot_runs\<run> `
  --external-source path\to\source.txt
```

| Flag | Default |
|------|---------|
| `--case-unknown-policy` | `cwa` (`block` skips Z3 when unknown grounded) |
| `--case-derive-mode` | `z3_witness` (`llm_glossary` optional) |

## Artifacts

| File | Content |
|------|---------|
| `policy_case_world.json` | Stated, unknown, derived |
| `policy_case_query.json` | Strict Z3 compatibility |
| `policy_case_query_addendum.json` | Strict + lenient + example witness for unknowns |
| `policy_case_explanation.json` | Witness or unsat core rules |
| `policy_case_report.json` | Final summary (`external_tester_run_report.json` alias) |

## Diagram

See [external_world_tester_overview.mmd](./external_world_tester_overview.mmd).
