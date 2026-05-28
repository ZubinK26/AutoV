# Dev plan: CrossCritic finding triage (selective CrossRepairer) v1

## Status

| Area | Status |
|------|--------|
| **Problem / UX spec** | This document |
| **`cross_critic_interactive_loop.py` (triage + gate)** | Implemented |
| **`cross_repair_handoff.json` + filtered handoff** | Implemented |
| **`run.py` cross slice wiring** | Implemented |
| **`cross_repairer.md` + trace fields** | Implemented |
| **Tests + docs** | Implemented |

---

## Problem

**CrossCritic** can emit multiple findings (`X001`, `X002`, …) with mixed severity and quality. **CrossRepairer v1** receives the **entire** `handoff.findings` list when the operator types **`REPAIR`** at the policy gate — there is **no** per-finding approval step (unlike **Pivot Tester → Test-Repairer**, which supports `a` / `i` triage and `approved_finding_ids`).

Operators need to **accept only the suggestions they agree with** (e.g. approve **X001** outcome_split, ignore **X003** template-style noise) without manually editing JSON or gambling on prompt-only “prefer no edit” discipline.

**Observed case (recruitment_16_temp_wfm):** X001 = real wiring gap (R0037 vs R0030–R0033); X002 = optional aggregate hygiene; X003 = false-positive template mismatch — ideal for selective repair.

---

## Goals

1. After CrossCritic prints findings, run a **short triage** before the existing **REPAIR / PROCEED_INCOMPLETE / abort** gate.
2. **Accept-all shortcut:** ask whether the user accepts **all** suggestions; **`y` / `yes`** → all findings approved for repair; skip disagree prompt.
3. **Selective path:** if **not** accept-all, show **numbered** findings (`1`, `2`, `3`, …) and ask which the user **disagrees** with (comma-separated indices, e.g. `2,3`).
4. **Approved set** = all findings **minus** disagreed indices; **ignored** = disagreed only.
5. **CrossRepairer** receives a handoff whose `findings` array contains **approved findings only** (same mechanical pattern as `tester_repair_handoff_dict`).
6. Persist **`cross_repair_handoff.json`** on disk for audit and future resume (v1.1 optional).
7. **REPAIR with zero approved:** print hint; do not call CrossRepairer LLM; return to triage or main gate.

## Non-goals (v1)

- Per-finding **`a` / `i`** walk (Tester style) — batch “accept all?” + “disagree numbers” only.
- Triage on **semantic critic** or **pivot tester** (already implemented elsewhere).
- Auto-repair without interactive flags.
- Re-running CrossCritic with “ignored” findings suppressed from the report (ignored findings stay in `cross_critic_report.json`; only repair scope changes).

---

## Names

| Artifact / module | Name |
|-------------------|------|
| Triage helper | `run_cross_finding_triage()` in `cross_critic_interactive_loop.py` |
| Filtered handoff builder | `cross_repair_handoff_dict()` in `cross_repairer_agent.py` (or `cross_critic_agent.py`) |
| On disk | `cross_repair_handoff.json` |
| Trace field | `approved_finding_ids`, `ignored_finding_ids` in `cross_repairer_trace.jsonl` |

Reuse gate tokens: **`REPAIR`**, **`PROCEED_INCOMPLETE`**, Enter = abort (unchanged).

---

## UX specification

### A. Finding display (numbered)

Extend **`format_cross_critic_report_terminal`** (or a sibling formatter used only in interactive mode) so each finding line is prefixed with a **1-based index**:

```text
Findings:
  1. [X001] WARN / outcome_split: … (rules: R0030, …)
      → Within the escalation semantic family, align …
  2. [X002] INFO / inconsistency: …
  3. [X003] INFO / inconsistency: …
```

**Stable ordering:** sort findings by `id` (same as Tester triage) before assigning indices. Indices are **display ordinals**, not `finding.id`.

### B. Triage prompts

After printing the CrossCritic block:

```text
=== CrossCritic triage ===
Accept all suggestions for repair? (y/n):
```

| Input | Behavior |
|-------|----------|
| `y`, `yes` (case-insensitive) | `approved` = all finding ids; `ignored` = ∅ |
| `n`, `no` | Ask disagree prompt (below) |
| invalid | Re-prompt accept-all |
| empty on accept-all | Re-prompt (do not default) |

If **no**:

```text
Enter the number(s) you DISAGREE with (comma-separated), or press Enter if you agree with all:
  e.g. 2,3  — ignores findings 2 and 3; repairs the rest
```

| Input | Behavior |
|-------|----------|
| empty | **Approve all** (equivalent to “yes” on accept-all — user disagrees with none) |
| `2, 3` | Parse integers; map to finding ids at those indices; those → **ignored**; others → **approved** |
| out of range / non-numeric | Re-prompt with error; do not proceed |
| duplicates | Dedupe silently |

**Summary** (always print before main gate):

```text
CrossCritic triage summary:
  Approved for repair: X001
  Ignored: X002, X003
```

### C. Main gate (unchanged tokens, new context line)

```text
[policy gate] CrossCritic reported ISSUES (3 total; 1 approved for repair).
  Type 'REPAIR' to run CrossRepairer on approved findings only, then re-check semantic critic.
  Type 'PROCEED_INCOMPLETE' to continue anyway.
  Type 'retriage' to re-run CrossCritic triage (optional v1 — see Implementation).
  Press Enter to abort.
```

### D. REPAIR branch

- Build `cross_repair_handoff_dict(xc_report, approved_ids=..., ignored_ids=..., full_report_path=work_dir / "cross_critic_report.json")`.
- `handoff["findings"]` = only approved finding objects.
- `handoff["approved_finding_ids"]`, `handoff["ignored_finding_ids"]` for audit.
- Pass filtered handoff to `run_cross_repairer`.
- Append trace: `approved_finding_ids`, `ignored_finding_ids`, `round`.

Post-repair: existing loop (compile, Z3, semantic critic refresh, re-run CrossCritic). **Re-triage:** on a new ISSUES report, run triage again (do not reuse prior approvals unless **`retriage`** not chosen and product adds sticky handoff — **v1: always re-triage** after each CrossCritic ISSUES pass).

---

## Handoff schema

Extend **`cross_critic_handoff_dict`** → split into:

- **`cross_critic_handoff_dict`** — full report export (optional, unchanged for non-repair).
- **`cross_repair_handoff_dict`** — repair payload:

```json
{
  "handoff_schema_version": "1.0",
  "source": "cross_critic",
  "source_note": "user approved repair subset",
  "verdict": "ISSUES",
  "compared_against": "processed_nl_and_linearized_model",
  "approved_finding_ids": ["X001"],
  "ignored_finding_ids": ["X002", "X003"],
  "findings": [ /* only X001 object */ ],
  "full_report_path": ".../cross_critic_report.json",
  "audit_trail_bullets": [],
  "notes": ""
}
```

**CrossRepairer prompt** (`prompts/cross_repairer.md`): clarify that `handoff.findings` is **already filtered**; repair **only** those ids; do not re-introduce ignored findings from `full_report_path`.

---

## Implementation steps

### 1. `cross_critic_interactive_loop.py` (new)

- `parse_disagree_indices(raw: str, *, max_index: int) -> set[int] | None` — split on `,`, strip, int parse, validate `1 <= i <= max_index`.
- `run_cross_finding_triage(report, *, input_fn, print_fn) -> tuple[set[str], set[str]]` — returns approved / ignored **finding id** sets.
- `format_cross_critic_report_numbered(report) -> str` — numbered findings block.
- `write_cross_repair_handoff(work_dir, report, approved, ignored) -> Path`.

Inject **`input_fn` / `print_fn`** for tests (mirror `tester_interactive_loop.py`).

### 2. `cross_repairer_agent.py`

- Add **`cross_repair_handoff_dict(...)`** mirroring `tester_repair_handoff_dict`.
- Deprecate passing unfiltered `cross_critic_handoff_dict` into `run_cross_repairer` from orchestration (keep full dict helper for non-repair exports if needed).

### 3. `run.py` cross slice (~L691–760)

Replace direct:

```python
h = cross_critic_handoff_dict(xc_report, ...)
```

with:

1. `format_cross_critic_report_terminal` + numbered section (or combined printer).
2. `approved, ignored = run_cross_finding_triage(...)` when `interactive_cross_any`.
3. Write `cross_repair_handoff.json` before gate (even on PROCEED — audit).
4. On `REPAIR`, use `cross_repair_handoff_dict`; if `len(approved)==0`, continue loop without LLM.
5. Summary fields: `cross_repair_approved_count`, `cross_repair_ignored_ids`, `cross_repair_handoff` path.

**Non-interactive:** unchanged — blocked with message to enable interactive flags (no triage).

### 4. Prompt + trace

- **`cross_repairer.md`:** rule 2 — “`handoff.findings` is the approved subset only.”
- **`cross_repairer_trace.jsonl`:** include `approved_finding_ids`, `ignored_finding_ids`.

### 5. Tests — `test_cross_critic_interactive_loop.py`

| Case | Assert |
|------|--------|
| accept all `y` | all ids approved |
| `n` + `2,3` | X002,X003 ignored; rest approved |
| `n` + empty | all approved |
| invalid index `9` | re-prompt, no crash |
| handoff filter | `findings` length == len(approved) |
| REPAIR M=0 | mock: no `run_cross_repairer` call |

### 6. Docs

- **`dev_plan_pivot_cross_critic_cross_repairer.md`:** add “Superseded by triage” pointer to this plan § Orchestration.
- **`NagV/pivot_pipeline/README.md` or ARCHITECTURE.md:** one paragraph on cross triage UX.
- **Conversation / demo:** recruitment example (approve 1, ignore 2–3).

### 7. Optional v1.1 (document only)

- **`retriage`** at main gate without re-running CrossCritic.
- **Sticky handoff** on cross-repair compile failure (reuse approved set like tester resume).
- **By finding id** input (`X003`) in addition to numbers for power users.

---

## CLI / flags

No new flags required — triage runs when:

- `--with-cross-critic` + `--with-cross-repair` + (`--interactive-policy` or `--interactive-cross-coherence`).

Document in `--help` for `--interactive-cross-coherence` that selective triage runs before REPAIR.

---

## Risks

| Risk | Mitigation |
|------|------------|
| User confuses **disagree numbers** with **approve numbers** | Label prompt “DISAGREE with”; show worked example `2,3` |
| LLM fixes ignored finding via “dependency” | Prompt: no edits for ignored ids; validate `change_summary[].finding_id ⊆ approved` (warn if violation) |
| Index/order drift vs report file | Sort by `id` before numbering; store `triage_index_map` in handoff optional field `{ "1": "X001", ... }` |
| Re-run CrossCritic after partial repair still flags ignored items | Expected; user may PROCEED_INCOMPLETE or ignore again |

---

## Acceptance criteria

- [x] Interactive cross run: user can reject finding **3** by typing `3` on disagree prompt; only findings **1–2** go to CrossRepairer.
- [x] `cross_repair_handoff.json` lists `approved_finding_ids` / `ignored_finding_ids` and filtered `findings`.
- [x] `cross_repairer_trace.jsonl` records approved/ignored per round.
- [x] `REPAIR` with all ignored (e.g. `1,2,3` when 3 findings) does not call LLM.
- [x] Non-interactive behavior unchanged (blocked, no triage).
- [x] Unit tests cover parse + handoff filter without live LLM.

---

## Example session (target)

```text
=== CrossCritic (IR coherence) ===
Verdict: ISSUES
Findings:
  1. [X001] WARN / outcome_split: …
  2. [X002] INFO / inconsistency: …
  3. [X003] INFO / inconsistency: …

=== CrossCritic triage ===
Accept all suggestions for repair? (y/n): n
Enter the number(s) you DISAGREE with (comma-separated): 2,3

CrossCritic triage summary:
  Approved for repair: X001
  Ignored: X002, X003

[policy gate] CrossCritic reported ISSUES (3 total; 1 approved for repair).
> REPAIR
```

---

## Related plans

- `dev_plan_pivot_cross_critic_cross_repairer.md` — base CrossCritic / CrossRepairer (implemented).
- `dev_plan_test_repairer_interactive_v1.md` — reference triage + handoff pattern (implemented).
