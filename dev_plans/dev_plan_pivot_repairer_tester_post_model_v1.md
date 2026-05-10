# Dev plan: Pivot post-model Repairer_Piv + Tester (v1)

## Implementation status (2026-05)

| Area | Status |
|------|--------|
| **Structured critic** (JSON `CriticReport`, `critic_report.json`, terminal block) | **Done** — `pivot_critic.md`, `critic_agent.py` |
| **Critic → handoff** (`critic_drift_handoff.json` on `PROCEED_INCOMPLETE`) | **Done** — `run.py` |
| **Critic → Repairer_Piv semantic** (`REPAIR` at gate, bounded rounds `PIVOT_CRITIC_SEMANTIC_REPAIR_MAX`, default 3) | **Done** — `repairer_piv_agent.py`, `prompts/repairer_piv_semantic.md` |
| **Compile failure → Repairer_Piv structural** (`--repairer-max-rounds`, default 2; `0` disables) | **Done** — `prompts/repairer_piv_structural.md`, `run.py` |
| **Trace logs** | `repairer_piv_structural_trace.jsonl`, `repairer_piv_semantic_trace.jsonl` |
| **Optional Tester** (`--with-tester`, `tester_report.json`, `--fail-on-tester-findings`) | **Done** — `post_model_workflow.py`, `tester_pivot_semantic.md` |
| **Interactive gates** | Critic: `REPAIR` / `PROCEED_INCOMPLETE` / Enter abort. Requires `--interactive-policy` (or extract-interactive) for REPAIR/PROCEED paths. |
| **Registry re-run** | After structural or semantic repair, `registry_pass_from_nl_and_rules` re-applied when `skip_registry` is false. |

### CLI flags (Pivot pipeline)

- `--with-critic` — structured critic (blocks on DRIFT if non-interactive).
- `--with-tester` — second semantic pass after precheck, before critic.
- `--fail-on-tester-findings` — exit `blocked_tester` when tester verdict is `issues`.
- `--repairer-max-rounds N` — structural repair attempts after compile failure (default `2`).

### Env

- `PIVOT_CRITIC_SEMANTIC_REPAIR_MAX` — max semantic repair rounds per critic DRIFT loop (default `3`).

---

## Purpose

Add two LLM-backed agents and a deterministic orchestration path **after** the current Pivot pipeline produces a **processed ruleset** and **policy model** (`MetaScheme` / Z3-ready artifacts), so that:

1. **Repairer_Piv** — Repairs **machine-checkable** failures (compile/validation/linking) and **semantic drift** from critic handoff, with bounded retries and traceable diffs.
2. **Tester** — Optional second review: **NL ↔ formal model semantic alignment** after precheck, **structured findings** for terminal review (`tester_report.json`). *Interactive handoff from Tester → Repairer (like critic) is a future small extension.*

This extends today’s per-line extract repair to **whole-ruleset** repair and adds **human-gated** semantic QA.

---

## Relationship to existing work

- **Extract phase:** per-line schema/JSON repair (`extract_schema_repair.md`), PREEMPTION cross-rule checks when `PIVOT_EXTRACT_WORKERS=1`.
- **Post-model:** operates on **`rules_extracted.json`**, **`meta_scheme.json`**, **effective NL**, **synthetic_en.md**.

---

## Actors and triggers

| Agent | When invoked | Input | Output |
|--------|----------------|-------|--------|
| **Repairer_Piv (structural)** | `load_rules_and_compile` raises (within `--repairer-max-rounds`) | `rules`, `policy_id`, error text | Patched `rules`; `rules_after_structural_repair.json` |
| **Repairer_Piv (semantic)** | Interactive `REPAIR` after critic DRIFT | `critic_drift_handoff`-shaped dict + rules + NL/synth excerpts | Patched `rules`; `rules_after_semantic_repair.json`; recompile + re-critic loop |
| **Critic (structured)** | `--with-critic` after synthetic EN built | Effective NL + `synthetic_en.md` | `critic_report.json`, `critic_result.txt` (raw) |
| **Tester** | `--with-tester` after precheck, before critic | Effective NL + synthetic + Z3 JSON blob | `tester_report.json` |

**Ordering (implemented):**

1. Extract (+ per-line repair) → registry → **compile** (+ **structural** repair loop).
2. Z3 → **synthetic_en** → precheck.
3. **Tester** (optional).
4. **Critic** loop: PASS / **REPAIR** (semantic repair + refresh artifacts + re-critic) / **PROCEED_INCOMPLETE** (writes `critic_drift_handoff.json`) / abort.

---

## Handoff schemas

### `critic_drift_handoff.json` (v1)

Written when the operator types `PROCEED_INCOMPLETE` after DRIFT. Fields: `handoff_schema_version`, `source: pivot_critic`, `source_note`, `verdict`, `compared_against`, `findings[]`, `audit_trail_bullets`, `notes`. Consumable by **Repairer_Piv semantic** on a later run or out-of-band tooling.

### `tester_handoff.json` (planned extension)

`tester_handoff_from_report()` exists in code for future interactive “accept findings → repair” parity with critic; not yet wired to a TTY gate in `run.py`.

---

## Design decisions (v1)

1. **Critic output:** Single JSON object validated by **Pydantic** (`CriticReport`); legacy `[VERDICT: …]` still parsed as fallback.
2. **Repairer output:** `{ "rules": [ ... ], "change_summary": [ ... ] }` (`RepairerPivOutput`).
3. **Stochastic discipline:** Prompts require **no markdown fences** for JSON stages; truncation markers in repairer payloads.

---

## Prompts (implemented paths)

| File | Role |
|------|------|
| `NagV/pivot_pipeline/prompts/pivot_critic.md` | Structured critic |
| `NagV/pivot_pipeline/prompts/repairer_piv_structural.md` | Compile/validation repair |
| `NagV/pivot_pipeline/prompts/repairer_piv_semantic.md` | Critic-finding repair |
| `NagV/pivot_pipeline/prompts/tester_pivot_semantic.md` | Optional Tester |

---

## Module map

- `pivot_pipeline/critic_agent.py` — `CriticReport`, `parse_critic_response`, `run_pivot_critic_parsed`, `critic_handoff_dict`, `format_critic_report_terminal`
- `pivot_pipeline/repairer_piv_agent.py` — `run_repairer_piv_structural`, `run_repairer_piv_semantic`, `append_repairer_trace`
- `pivot_pipeline/post_model_workflow.py` — `TesterReport`, `run_pivot_tester`, `tester_handoff_from_report`, `critic_repair_max_rounds`
- `pivot_pipeline/run.py` — orchestration
- `pivot_pipeline/policy_gates.py` — `REPAIR_CRITIC_DRIFT_TOKEN` (`REPAIR`)

---

## Remaining / follow-ups

- **Tester → Repairer TTY loop** — mirror critic’s `REPAIR` / `PROCEED` using `tester_handoff.json`.
- **CI policy** — document exit codes for `blocked_compile`, `blocked_tester`, `blocked_critic`.
- **Re-run registry** policy when semantic repair only touches constants (avoid unnecessary rename churn).
- **`Extract-Pivot.md`** — operator-facing section for new flags and critic/Tester artifacts.

---

## Done criteria (v1) — revised

- [x] Structured critic JSON + `critic_report.json` + terminal summary.
- [x] DRIFT gate: `REPAIR` (semantic Repairer + re-critic) or `PROCEED_INCOMPLETE` (handoff file).
- [x] Structural repair loop on compile failure (`--repairer-max-rounds`).
- [x] Optional Tester (`--with-tester`) + `tester_report.json`.
- [x] Unit tests for critic JSON parse; pipeline tests still green.
