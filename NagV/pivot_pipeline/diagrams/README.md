# Pipeline diagrams (Mermaid)

High-level visuals for newcomers. Detailed CLI-level diagram: [`../ARCHITECTURE.md`](../ARCHITECTURE.md).

| File | Topic |
|------|--------|
| [`pipeline_e2e_overview.md`](pipeline_e2e_overview.md) | Full pivot path: NL → formal model → alignment → tests → artifacts |
| [`pipeline_e2e_overview.mmd`](pipeline_e2e_overview.mmd) | Same diagram — **copy-paste only** for [mermaid.live](https://mermaid.live) |
| [`external_world_tester_overview.md`](external_world_tester_overview.md) | External document → provenance fill → blind review → Z3 test |
| [`../../dev_plans/dev_plan_external_world_tester_v2_global_scenario_v1.md`](../../dev_plans/dev_plan_external_world_tester_v2_global_scenario_v1.md) | **Planned v2:** global `scenario` SAT + `not_found` defaults |
| [`external_world_tester_overview.mmd`](external_world_tester_overview.mmd) | Same — copy-paste for mermaid.live |

## Render online

1. Go to **https://mermaid.live**
2. Open the `.mmd` file (or copy the fenced `mermaid` block from the `.md` file).
3. Paste into the left pane.
4. **Actions → Export PNG/SVG/PDF**

GitHub also renders the `.md` files when you view them in the browser.
